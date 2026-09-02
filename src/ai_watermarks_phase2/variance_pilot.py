"""Run the paired multi-key by length Phase 2 variance pilot."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import platform
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import canonical
from .compact_scoring import CompactKGWScorer, CompactSynthIDScorer
from .key_schedule import SCHEDULE_SEED, derive_schedule
from .native import TransformersNativeRunner, require_ml_dependencies
from .smoke import git_commit, git_dirty, load_json, sha256_text


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def runner_source_sha256() -> str:
    paths = [
        Path("uv.lock"),
        Path("src/ai_watermarks_phase2/canonical.py"),
        Path("src/ai_watermarks_phase2/compact_scoring.py"),
        Path("src/ai_watermarks_phase2/native.py"),
        Path("src/ai_watermarks_phase2/variance_pilot.py"),
    ]
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def write_result(path: Path, result: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def build_scorers(
    config: dict[str, Any], watermark_config: dict[str, Any], runner: TransformersNativeRunner
) -> tuple[list[CompactKGWScorer], list[CompactSynthIDScorer], Any, Any]:
    kgw_variant = config["variants"]["kgw"]
    synthid_variant = config["variants"]["synthid"]
    if kgw_variant != canonical.KGW_AUTHOR_VARIANT:
        raise ValueError("The variance pilot requires the author-canonical KGW variant")
    if synthid_variant != canonical.SYNTHID_DEEPMIND_VARIANT:
        raise ValueError("The variance pilot requires the DeepMind-canonical SynthID variant")

    kgw_scorers: list[CompactKGWScorer] = []
    primary_kgw_config = None
    shared_table = None
    for index, key in enumerate(config["key_schedule"]["kgw"]):
        settings = dict(watermark_config["kgw"], hashing_key=int(key))
        keyed_config = canonical.build_kgw_config(settings, kgw_variant)
        processor = keyed_config.construct_processor(
            runner.model.config.vocab_size, runner.device
        )
        if shared_table is None:
            shared_table = processor.fixed_table
        else:
            processor.fixed_table = shared_table
        if index == 0:
            primary_kgw_config = keyed_config
        kgw_scorers.append(
            CompactKGWScorer(
                processor=processor,
                variant=kgw_variant,
                key_id=f"kgw-{index:02d}",
                hashing_key=int(key),
                greenlist_ratio=float(settings["greenlist_ratio"]),
            )
        )

    synthid_scorers: list[CompactSynthIDScorer] = []
    primary_synthid_config = None
    for index, keys in enumerate(config["key_schedule"]["synthid"]):
        settings = dict(watermark_config["synthid"], keys=[int(key) for key in keys])
        keyed_config = canonical.build_synthid_config(settings, synthid_variant)
        processor = keyed_config.construct_processor(
            runner.model.config.vocab_size, runner.device
        )
        if index == 0:
            primary_synthid_config = keyed_config
        synthid_scorers.append(
            CompactSynthIDScorer(
                processor=processor,
                variant=synthid_variant,
                key_id=f"synthid-{index:02d}",
                keys=tuple(int(key) for key in keys),
                eos_token_id=int(runner.tokenizer.eos_token_id),
            )
        )
    return (
        kgw_scorers,
        synthid_scorers,
        primary_kgw_config,
        primary_synthid_config,
    )


def audit_primary_scores(
    runner: TransformersNativeRunner,
    tokens: list[int],
    length: int,
    compact_kgw: dict[str, Any],
    compact_synthid: dict[str, Any],
    kgw_config: Any,
    synthid_config: Any,
    variants: dict[str, str],
) -> dict[str, Any]:
    prefix = tokens[:length]
    native_kgw = runner.score_kgw(
        prefix,
        first_generated_position=0,
        config=kgw_config,
        variant=variants["kgw"],
        ignore_repeated_ngrams=True,
    )
    native_synthid = runner.score_synthid(
        prefix,
        first_generated_position=0,
        config=synthid_config,
        variant=variants["synthid"],
    )
    kgw_exact = (
        compact_kgw["eligible_positions"] == native_kgw.eligible_positions
        and compact_kgw["green_tokens"] == native_kgw.auxiliary["green_tokens"]
        and compact_kgw["value"] == native_kgw.value
    )
    native_g_sum = sum(
        sum(row.values["g_values"])
        for row in native_synthid.position_traces
        if row.eligible
    )
    synthid_exact = (
        compact_synthid["eligible_positions"] == native_synthid.eligible_positions
        and compact_synthid["g_value_sum"] == native_g_sum
        and compact_synthid["value"] == native_synthid.value
    )
    if not kgw_exact or not synthid_exact:
        raise RuntimeError(f"Compact/native score parity failed at length {length}")
    return {
        "length": length,
        "kgw_exact": kgw_exact,
        "synthid_exact": synthid_exact,
        "native_scores": [native_kgw.to_dict(), native_synthid.to_dict()],
    }


def validate_design(config: dict[str, Any], prompts: list[dict[str, Any]]) -> None:
    lengths = config["generation"]["paired_prefix_lengths"]
    generated = int(config["generation"]["generated_tokens"])
    if lengths != sorted(set(lengths)) or lengths[-1] != generated:
        raise ValueError("paired_prefix_lengths must be unique, sorted, and end at generated_tokens")
    if len(config["key_schedule"]["kgw"]) != 10:
        raise ValueError("The frozen pilot requires exactly ten KGW keys")
    synthid_keys = config["key_schedule"]["synthid"]
    if len(synthid_keys) != 10 or len({tuple(keys) for keys in synthid_keys}) != 10:
        raise ValueError("The frozen pilot requires ten unique SynthID key vectors")
    if any(len(keys) != 9 for keys in synthid_keys):
        raise ValueError("Every SynthID key vector must preserve depth nine")
    if config["key_schedule"]["seed"] != SCHEDULE_SEED:
        raise ValueError("Key-schedule seed differs from the frozen derivation")
    expected_schedule = derive_schedule(10)
    if config["key_schedule"]["kgw"] != expected_schedule["kgw"]:
        raise ValueError("KGW key schedule does not match its frozen derivation")
    if synthid_keys != expected_schedule["synthid"]:
        raise ValueError("SynthID key schedule does not match its frozen derivation")
    target = int(config["selection"]["prompts"])
    if len(prompts) < target:
        raise ValueError(f"Prompt manifest has {len(prompts)} records, needs {target}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path, default=Path("configs/phase2-variance-pilot.json")
    )
    parser.add_argument(
        "--output", type=Path, default=Path("results/phase2-variance-pilot/run.json")
    )
    parser.add_argument("--limit", type=int)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    config = load_json(args.config)
    prompt_path = Path(config["prompt_manifest"])
    watermark_path = Path(config["watermark_config"])
    prompt_manifest = load_json(prompt_path)
    prompts = prompt_manifest["records"]
    validate_design(config, prompts)
    target = int(config["selection"]["prompts"])
    limit = target if args.limit is None else args.limit
    if not 1 <= limit <= target:
        parser.error(f"--limit must be between 1 and {target}")
    batch_size = int(config["generation"]["batch_size"])
    if limit != target and limit % batch_size:
        parser.error(f"partial --limit must be divisible by batch_size={batch_size}")

    input_sha256 = {
        "config": file_sha256(args.config),
        "prompt_manifest": file_sha256(prompt_path),
        "watermark_config": file_sha256(watermark_path),
        "runner_source": runner_source_sha256(),
    }
    if args.dry_run:
        print(
            json.dumps(
                {
                    "status": "configuration_valid",
                    "prompts": target,
                    "selected": limit,
                    "lengths": config["generation"]["paired_prefix_lengths"],
                    "kgw_keys": len(config["key_schedule"]["kgw"]),
                    "synthid_keys": len(config["key_schedule"]["synthid"]),
                    "input_sha256": input_sha256,
                },
                indent=2,
            )
        )
        return 0

    records: list[dict[str, Any]] = []
    audits: list[dict[str, Any]] = []
    if args.resume and args.output.exists():
        previous = load_json(args.output)
        if previous.get("input_sha256") != input_sha256:
            raise ValueError("Cannot resume: pilot inputs or runner source changed")
        records = previous.get("records", [])
        audits = previous.get("native_trace_audits", [])
        expected = [item["id"] for item in prompts[: len(records)]]
        observed = [item["prompt_id"] for item in records]
        if expected != observed or len(records) % batch_size:
            raise ValueError("Cannot resume: records are not complete frozen batches")
    if len(records) >= limit:
        print(json.dumps({"status": "already_complete", "records": len(records)}, indent=2))
        return 0

    watermark_config = load_json(watermark_path)
    if config["model"] != watermark_config["model"]:
        raise ValueError("Variance-pilot and watermark model configurations differ")
    if config["variants"] != watermark_config["variants"]:
        raise ValueError("Variance-pilot and watermark variants differ")
    runner = TransformersNativeRunner(
        model_id=config["model"]["id"],
        revision=config["model"]["revision"],
        device=config["model"]["device"],
    )
    (
        kgw_scorers,
        synthid_scorers,
        primary_kgw_config,
        primary_synthid_config,
    ) = build_scorers(config, watermark_config, runner)
    generation = config["generation"]
    lengths = [int(length) for length in generation["paired_prefix_lengths"]]
    selected = prompts[:limit]
    torch, transformers = require_ml_dependencies()

    for batch_start in range(len(records), len(selected), batch_size):
        batch = selected[batch_start : batch_start + batch_size]
        batch_index = batch_start // batch_size
        batch_seed = int(generation["base_seed"]) + batch_index
        generated_rows = runner.generate_batch(
            [item["prompt"] for item in batch],
            seed=batch_seed,
            min_new_tokens=int(generation["generated_tokens"]),
            max_new_tokens=int(generation["generated_tokens"]),
            temperature=float(generation["temperature"]),
            top_k=int(generation["top_k"]),
            watermark_config=None,
        )
        for stream_index, (prompt, generated_row) in enumerate(
            zip(batch, generated_rows, strict=True)
        ):
            _, continuation, text = generated_row
            if len(continuation) != int(generation["generated_tokens"]):
                raise RuntimeError(f"Unexpected generated length for {prompt['id']}")
            kgw_by_key = [
                scorer.score_prefixes(continuation, lengths) for scorer in kgw_scorers
            ]
            synthid_by_key = [
                scorer.score_prefixes(continuation, lengths)
                for scorer in synthid_scorers
            ]
            prefix_results = []
            for length in lengths:
                scores = [items[length] for items in kgw_by_key] + [
                    items[length] for items in synthid_by_key
                ]
                if any(
                    not math.isfinite(float(score["value"]))
                    or int(score["eligible_positions"]) <= 0
                    for score in scores
                ):
                    raise RuntimeError(f"Invalid compact score for {prompt['id']}")
                prefix_results.append({"length": length, "scores": scores})
            if not audits:
                for prefix_result in prefix_results:
                    audits.append(
                        audit_primary_scores(
                            runner,
                            continuation,
                            prefix_result["length"],
                            prefix_result["scores"][0],
                            prefix_result["scores"][len(kgw_scorers)],
                            primary_kgw_config,
                            primary_synthid_config,
                            config["variants"],
                        )
                    )
            records.append(
                {
                    "prompt_id": prompt["id"],
                    "source_row": prompt["source_row"],
                    "category": prompt["category"],
                    "prompt_sha256": prompt["prompt_sha256"],
                    "condition": "unwatermarked",
                    "batch_seed": batch_seed,
                    "batch_stream_index": stream_index,
                    "generated_tokens": len(continuation),
                    "token_ids": continuation,
                    "output_sha256": sha256_text(text),
                    "text": text,
                    "prefix_results": prefix_results,
                }
            )

        result = {
            "schema_version": 1,
            "status": "variance_pilot_complete" if len(records) == target else "variance_pilot_partial",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "scope": config["scope"],
            "config": config,
            "input_sha256": input_sha256,
            "environment": {
                "python": platform.python_version(),
                "platform": platform.platform(),
                "torch": torch.__version__,
                "transformers": transformers.__version__,
                "package_version": importlib.metadata.version("ai-watermarks-research"),
                "git_commit": git_commit(),
                "git_dirty": git_dirty(),
            },
            "category_counts": dict(
                sorted(Counter(record["category"] for record in records).items())
            ),
            "native_trace_audits": audits,
            "records": records,
        }
        write_result(args.output, result)
        print(f"checkpoint {len(records)}/{target}", flush=True)

    print(
        json.dumps(
            {"status": result["status"], "records": len(records), "output": str(args.output)},
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
