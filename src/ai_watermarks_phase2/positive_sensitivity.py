"""Run the resumable v2 development-only watermarked-positive screen."""

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
from typing import Any, Iterator

from . import canonical
from .compact_scoring import CompactKGWScorer, CompactSynthIDScorer
from .key_schedule import SCHEDULE_SEED, derive_schedule
from .native import TransformersNativeRunner, require_ml_dependencies
from .smoke import git_commit, git_dirty, load_json, sha256_text
from .variance_pilot import file_sha256


def source_sha256() -> str:
    digest = hashlib.sha256()
    for path in (
        Path("uv.lock"),
        Path("src/ai_watermarks_phase2/canonical.py"),
        Path("src/ai_watermarks_phase2/compact_scoring.py"),
        Path("src/ai_watermarks_phase2/native.py"),
        Path("src/ai_watermarks_phase2/positive_sensitivity.py"),
    ):
        digest.update(path.as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def batch_paths(output_dir: Path) -> list[Path]:
    return sorted((output_dir / "batches").glob("batch-*.json"))


def iter_records(output_dir: Path) -> Iterator[dict[str, Any]]:
    for path in batch_paths(output_dir):
        batch = load_json(path)
        if not isinstance(batch, dict) or not isinstance(batch.get("records"), list):
            raise ValueError(f"Malformed batch: {path}")
        yield from batch["records"]


def condition_ids() -> list[tuple[str, str, int]]:
    return [
        (scheme, f"{scheme}-{index:02d}", index)
        for scheme in ("kgw", "synthid")
        for index in range(10)
    ]


def batch_plan(prompts: int, batch_size: int) -> list[dict[str, Any]]:
    if prompts < 1 or batch_size < 1 or prompts % batch_size:
        raise ValueError("prompts must be a positive multiple of batch_size")
    plan: list[dict[str, Any]] = []
    for scheme, key_id, key_index in condition_ids():
        for prompt_start in range(0, prompts, batch_size):
            plan.append(
                {
                    "scheme": scheme,
                    "key_id": key_id,
                    "key_index": key_index,
                    "prompt_start": prompt_start,
                }
            )
    return plan


def validate_inputs(
    config_path: Path, manifest_path: Path, thresholds_path: Path
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    config = load_json(config_path)
    manifest = load_json(manifest_path)
    thresholds = load_json(thresholds_path)
    if config.get("status") != "development_only_predeclared":
        raise ValueError("Pilot config is not predeclared development-only")
    if manifest.get("status") != "positive_sensitivity_prompt_manifest_frozen":
        raise ValueError("Prompt manifest is not frozen")
    if thresholds.get("status") != "development_thresholds_frozen":
        raise ValueError("Development thresholds are not frozen")
    pilot_id = config["pilot_id"]
    if manifest.get("pilot_id") != pilot_id or thresholds.get("pilot_id") != pilot_id:
        raise ValueError("Pilot IDs do not agree")
    if thresholds["input_sha256"]["development_config"] != file_sha256(config_path):
        raise ValueError("Pilot config changed after thresholds were frozen")
    separation = thresholds.get("separation", {})
    if separation.get("confirmation_scores_loaded") is not False:
        raise ValueError("Threshold artifact does not prove confirmation separation")
    prompts = int(config["generation"]["prompts_per_scheme_key"])
    if len(manifest["records"]) != prompts:
        raise ValueError("Prompt count differs from the predeclared pilot")
    if len({row["prompt_sha256"] for row in manifest["records"]}) != prompts:
        raise ValueError("Prompt hashes are not unique")
    schedule_source = load_json(Path(config["key_schedule"]["source_config"]))
    source_schedule = schedule_source["key_schedule"]
    schedule = {
        "kgw": source_schedule["kgw"],
        "synthid": source_schedule["synthid"],
    }
    if (
        config["key_schedule"]["seed"] != SCHEDULE_SEED
        or source_schedule.get("seed") != SCHEDULE_SEED
        or schedule != derive_schedule(10)
    ):
        raise ValueError("Key schedule differs from the frozen derivation")
    return config, manifest, thresholds, schedule


def build_conditions(
    config: dict[str, Any], schedule: dict[str, Any], runner: TransformersNativeRunner
) -> list[dict[str, Any]]:
    watermark = load_json(Path(config["watermark_config"]))
    if config["model"] != watermark["model"]:
        raise ValueError("Pilot and watermark model configs differ")
    variants = watermark["variants"]
    if variants["kgw"] != canonical.KGW_AUTHOR_VARIANT:
        raise ValueError("Pilot requires the author-canonical KGW variant")
    if variants["synthid"] != canonical.SYNTHID_DEEPMIND_VARIANT:
        raise ValueError("Pilot requires the DeepMind-canonical SynthID variant")
    conditions: list[dict[str, Any]] = []
    shared_kgw_table = None
    for scheme, key_id, key_index in condition_ids():
        if scheme == "kgw":
            settings = dict(watermark["kgw"], hashing_key=int(schedule["kgw"][key_index]))
            generation_config = canonical.build_kgw_config(settings, variants["kgw"])
            processor = generation_config.construct_processor(
                runner.model.config.vocab_size, runner.device
            )
            if shared_kgw_table is None:
                shared_kgw_table = processor.fixed_table
            else:
                processor.fixed_table = shared_kgw_table
            scorer: Any = CompactKGWScorer(
                processor=processor,
                variant=variants["kgw"],
                key_id=key_id,
                hashing_key=int(schedule["kgw"][key_index]),
                greenlist_ratio=float(settings["greenlist_ratio"]),
            )
        else:
            keys = [int(value) for value in schedule["synthid"][key_index]]
            settings = dict(watermark["synthid"], keys=keys)
            generation_config = canonical.build_synthid_config(settings, variants["synthid"])
            processor = generation_config.construct_processor(
                runner.model.config.vocab_size, runner.device
            )
            scorer = CompactSynthIDScorer(
                processor=processor,
                variant=variants["synthid"],
                key_id=key_id,
                keys=tuple(keys),
                eos_token_id=int(runner.tokenizer.eos_token_id),
            )
        conditions.append(
            {
                "scheme": scheme,
                "key_id": key_id,
                "key_index": key_index,
                "generation_config": generation_config,
                "scorer": scorer,
                "variant": variants[scheme],
            }
        )
    return conditions


def audit_score(
    runner: TransformersNativeRunner,
    condition: dict[str, Any],
    tokens: list[int],
    length: int,
    compact: dict[str, Any],
) -> dict[str, Any]:
    prefix = tokens[:length]
    if condition["scheme"] == "kgw":
        native = runner.score_kgw(
            prefix,
            first_generated_position=0,
            config=condition["generation_config"],
            variant=condition["variant"],
            ignore_repeated_ngrams=True,
        )
        exact = (
            compact["eligible_positions"] == native.eligible_positions
            and compact["green_tokens"] == native.auxiliary["green_tokens"]
            and compact["value"] == native.value
        )
    else:
        native = runner.score_synthid(
            prefix,
            first_generated_position=0,
            config=condition["generation_config"],
            variant=condition["variant"],
        )
        g_sum = sum(
            sum(row.values["g_values"])
            for row in native.position_traces
            if row.eligible
        )
        exact = (
            compact["eligible_positions"] == native.eligible_positions
            and compact["g_value_sum"] == g_sum
            and compact["value"] == native.value
        )
    if not exact:
        raise RuntimeError(
            f"Compact/native parity failed: {condition['key_id']} length {length}"
        )
    return {
        "scheme": condition["scheme"],
        "key_id": condition["key_id"],
        "length": length,
        "exact": exact,
        "eligible_positions": native.eligible_positions,
        "value": native.value,
    }


def validate_existing(
    output_dir: Path,
    plan: list[dict[str, Any]],
    prompts: list[dict[str, Any]],
    batch_size: int,
    input_sha256: dict[str, str],
) -> tuple[int, list[dict[str, Any]], Counter[str]]:
    paths = batch_paths(output_dir)
    expected_names = [f"batch-{index:06d}.json" for index in range(len(paths))]
    if [path.name for path in paths] != expected_names:
        raise ValueError("Existing batches are not contiguous and zero-based")
    audits: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    for index, path in enumerate(paths):
        batch = load_json(path)
        expected = plan[index]
        if batch.get("batch_index") != index or batch.get("input_sha256") != input_sha256:
            raise ValueError(f"Batch identity mismatch: {path}")
        if any(batch.get(key) != expected[key] for key in ("scheme", "key_id", "prompt_start")):
            raise ValueError(f"Batch plan mismatch: {path}")
        records = batch.get("records")
        if not isinstance(records, list) or len(records) != batch_size:
            raise ValueError(f"Incomplete batch: {path}")
        expected_ids = [
            row["id"]
            for row in prompts[expected["prompt_start"] : expected["prompt_start"] + batch_size]
        ]
        if [row["prompt_id"] for row in records] != expected_ids:
            raise ValueError(f"Prompt order mismatch: {path}")
        audits.extend(batch.get("native_score_audits", []))
        counts.update([expected["scheme"]] * len(records))
    return len(paths), audits, counts


def run_digest(output_dir: Path) -> str:
    digest = hashlib.sha256()
    metadata = load_json(output_dir / "run.json")
    stable = {
        key: metadata[key]
        for key in (
            "schema_version",
            "status",
            "pilot_id",
            "completed_batches",
            "completed_outputs",
            "input_sha256",
        )
    }
    digest.update(json.dumps(stable, sort_keys=True).encode("utf-8"))
    for path in batch_paths(output_dir):
        digest.update(path.name.encode("utf-8"))
        digest.update(bytes.fromhex(file_sha256(path)))
    return digest.hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path, default=Path("configs/phase2-v2-positive-sensitivity.json")
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("results/phase2-v2-positive-sensitivity/run")
    )
    parser.add_argument("--limit-batches", type=int)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    config_preview = load_json(args.config)
    manifest_path = Path(config_preview["prompt_manifest"])
    threshold_path = Path(config_preview["provisional_thresholds"]["artifact"])
    config, manifest, _thresholds, schedule = validate_inputs(
        args.config, manifest_path, threshold_path
    )
    prompts = manifest["records"]
    generation = config["generation"]
    batch_size = int(generation["batch_size"])
    plan = batch_plan(int(generation["prompts_per_scheme_key"]), batch_size)
    target_batches = len(plan)
    limit_batches = target_batches if args.limit_batches is None else args.limit_batches
    if not 1 <= limit_batches <= target_batches:
        parser.error(f"--limit-batches must be between 1 and {target_batches}")
    input_sha256 = {
        "config": file_sha256(args.config),
        "prompt_manifest": file_sha256(manifest_path),
        "watermark_config": file_sha256(Path(config["watermark_config"])),
        "key_schedule_source": file_sha256(Path(config["key_schedule"]["source_config"])),
        "provisional_thresholds": file_sha256(threshold_path),
        "runner_source": source_sha256(),
    }
    if args.dry_run:
        print(
            json.dumps(
                {
                    "status": "configuration_valid",
                    "pilot_id": config["pilot_id"],
                    "prompts": len(prompts),
                    "conditions": len(condition_ids()),
                    "primary_cells": 60,
                    "target_batches": target_batches,
                    "selected_batches": limit_batches,
                    "target_outputs": target_batches * batch_size,
                    "input_sha256": input_sha256,
                    "confirmation_scores_used": False,
                },
                indent=2,
            )
        )
        return 0

    completed, audits, counts = validate_existing(
        args.output_dir, plan, prompts, batch_size, input_sha256
    )
    if completed >= limit_batches:
        print(json.dumps({"status": "already_complete", "batches": completed}, indent=2))
        return 0
    runner = TransformersNativeRunner(
        model_id=config["model"]["id"],
        revision=config["model"]["revision"],
        device=config["model"]["device"],
    )
    conditions = build_conditions(config, schedule, runner)
    condition_lookup = {(item["scheme"], item["key_id"]): item for item in conditions}
    lengths = [int(value) for value in generation["paired_prefix_lengths"]]
    torch, transformers = require_ml_dependencies()

    for batch_index in range(completed, limit_batches):
        spec = plan[batch_index]
        condition = condition_lookup[(spec["scheme"], spec["key_id"])]
        start = int(spec["prompt_start"])
        prompt_batch = prompts[start : start + batch_size]
        batch_seed = int(generation["base_seed"]) + batch_index
        generated_rows = runner.generate_batch(
            [row["prompt"] for row in prompt_batch],
            seed=batch_seed,
            min_new_tokens=int(generation["generated_tokens"]),
            max_new_tokens=int(generation["generated_tokens"]),
            temperature=float(generation["temperature"]),
            top_k=int(generation["top_k"]),
            watermark_config=condition["generation_config"],
        )
        batch_records: list[dict[str, Any]] = []
        batch_audits: list[dict[str, Any]] = []
        for stream_index, (prompt, generated) in enumerate(
            zip(prompt_batch, generated_rows, strict=True)
        ):
            _, continuation, text = generated
            if len(continuation) != int(generation["generated_tokens"]):
                raise RuntimeError(f"Unexpected generated length: {prompt['id']}")
            scores = condition["scorer"].score_prefixes(continuation, lengths)
            prefix_results = []
            for length in lengths:
                score = scores[length]
                if not math.isfinite(float(score["value"])) or int(score["eligible_positions"]) <= 0:
                    raise RuntimeError(f"Invalid score: {prompt['id']}/{condition['key_id']}")
                prefix_results.append({"length": length, "score": score})
            if start == 0 and stream_index == 0:
                batch_audits.extend(
                    audit_score(runner, condition, continuation, row["length"], row["score"])
                    for row in prefix_results
                )
            batch_records.append(
                {
                    "prompt_id": prompt["id"],
                    "source_shard": prompt["source_shard"],
                    "source_row": prompt["source_row"],
                    "source_prompt_id": prompt["source_prompt_id"],
                    "prompt_sha256": prompt["prompt_sha256"],
                    "condition": "watermarked",
                    "scheme": condition["scheme"],
                    "key_id": condition["key_id"],
                    "variant": condition["variant"],
                    "batch_seed": batch_seed,
                    "batch_stream_index": stream_index,
                    "generated_tokens": len(continuation),
                    "token_ids": continuation,
                    "output_sha256": sha256_text(text),
                    "text": text,
                    "prefix_results": prefix_results,
                }
            )
        batch_value = {
            "schema_version": 1,
            "pilot_id": config["pilot_id"],
            "batch_index": batch_index,
            "scheme": condition["scheme"],
            "key_id": condition["key_id"],
            "prompt_start": start,
            "batch_seed": batch_seed,
            "input_sha256": input_sha256,
            "native_score_audits": batch_audits,
            "records": batch_records,
        }
        atomic_json(args.output_dir / "batches" / f"batch-{batch_index:06d}.json", batch_value)
        audits.extend(batch_audits)
        counts.update([condition["scheme"]] * len(batch_records))
        completed = batch_index + 1
        complete = completed == target_batches
        metadata = {
            "schema_version": 1,
            "status": "positive_sensitivity_complete" if complete else "positive_sensitivity_partial",
            "pilot_id": config["pilot_id"],
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "scope": config["scope"],
            "completed_batches": completed,
            "target_batches": target_batches,
            "completed_outputs": completed * batch_size,
            "target_outputs": target_batches * batch_size,
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
            "scheme_output_counts": dict(sorted(counts.items())),
            "native_score_audits": audits,
            "confirmation_scores_used": False,
        }
        atomic_json(args.output_dir / "run.json", metadata)
        print(
            f"checkpoint batch {completed}/{target_batches} "
            f"outputs {completed * batch_size}/{target_batches * batch_size}",
            flush=True,
        )

    print(
        json.dumps(
            {
                "status": metadata["status"],
                "batches": completed,
                "outputs": completed * batch_size,
                "output_dir": str(args.output_dir),
                "run_digest": run_digest(args.output_dir),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
