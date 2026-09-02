"""Run the resumable targeted canonical-KGW generation-bias experiment."""

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
from .compact_scoring import CompactKGWScorer
from .key_schedule import SCHEDULE_SEED, derive_schedule
from .native import TransformersNativeRunner, require_ml_dependencies
from .positive_sensitivity import atomic_json, audit_score
from .smoke import git_commit, git_dirty, load_json, sha256_text
from .variance_pilot import file_sha256


def source_sha256() -> str:
    digest = hashlib.sha256()
    for path in (
        Path("uv.lock"),
        Path("src/ai_watermarks_phase2/canonical.py"),
        Path("src/ai_watermarks_phase2/compact_scoring.py"),
        Path("src/ai_watermarks_phase2/native.py"),
        Path(__file__),
    ):
        digest.update(path.as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def batch_paths(output_dir: Path) -> list[Path]:
    return sorted((output_dir / "batches").glob("batch-*.json"))


def iter_records(output_dir: Path) -> Iterator[dict[str, Any]]:
    for path in batch_paths(output_dir):
        batch = load_json(path)
        if not isinstance(batch, dict) or not isinstance(batch.get("records"), list):
            raise ValueError(f"Malformed batch: {path}")
        yield from batch["records"]


def batch_plan(
    key_indices: list[int], biases: list[float], prompts: int, batch_size: int
) -> list[dict[str, Any]]:
    if prompts < 1 or batch_size < 1 or prompts % batch_size:
        raise ValueError("prompts must be a positive multiple of batch_size")
    return [
        {
            "key_index": key_index,
            "key_id": f"kgw-{key_index:02d}",
            "bias": bias,
            "prompt_start": prompt_start,
        }
        for key_index in key_indices
        for bias in biases
        for prompt_start in range(0, prompts, batch_size)
    ]


def paired_batch_seed(
    base_seed: int, key_indices: list[int], key_index: int, prompt_start: int, batch_size: int,
    prompts: int,
) -> int:
    key_position = key_indices.index(key_index)
    return base_seed + key_position * (prompts // batch_size) + prompt_start // batch_size


def validate_inputs(config_path: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[int]]:
    config = load_json(config_path)
    if config.get("status") != "development_only_predeclared":
        raise ValueError("Experiment is not predeclared development-only")
    manifest = load_json(Path(config["prompt_manifest"]))
    if manifest.get("status") != "kgw_bias_development_prompt_manifest_frozen":
        raise ValueError("Prompt manifest is not frozen")
    if manifest.get("experiment_id") != config.get("experiment_id"):
        raise ValueError("Config and manifest experiment IDs differ")
    thresholds = load_json(Path(config["provisional_thresholds"]["artifact"]))
    if thresholds.get("status") != "development_thresholds_frozen":
        raise ValueError("Development thresholds are not frozen")
    if thresholds.get("separation", {}).get("confirmation_scores_loaded") is not False:
        raise ValueError("Threshold artifact does not prove confirmation separation")
    if config["provisional_thresholds"]["confirmation_scores_used"] is not False:
        raise ValueError("Confirmation separation is not predeclared")
    generation = config["generation"]
    prompts = int(generation["prompts_per_condition"])
    if len(manifest["records"]) != prompts:
        raise ValueError("Prompt count differs from the experiment config")
    if len({row["prompt_sha256"] for row in manifest["records"]}) != prompts:
        raise ValueError("Prompt hashes are not unique")
    schedule_source = load_json(Path(config["key_schedule"]["source_config"]))
    if config["key_schedule"]["seed"] != SCHEDULE_SEED:
        raise ValueError("Key schedule seed differs")
    schedule = schedule_source["key_schedule"]
    if schedule.get("seed") != SCHEDULE_SEED or {
        "kgw": schedule["kgw"], "synthid": schedule["synthid"]
    } != derive_schedule(10):
        raise ValueError("Key schedule differs from the frozen derivation")
    key_indices = [int(value) for value in generation["target_key_indices"]]
    if len(key_indices) != len(set(key_indices)) or not all(0 <= value < 10 for value in key_indices):
        raise ValueError("Invalid target key indices")
    return config, manifest, thresholds, [int(value) for value in schedule["kgw"]]


def build_conditions(
    config: dict[str, Any], kgw_keys: list[int], runner: TransformersNativeRunner
) -> dict[tuple[int, float], dict[str, Any]]:
    watermark = load_json(Path(config["watermark_config"]))
    if config["model"] != watermark["model"]:
        raise ValueError("Experiment and watermark model configs differ")
    if watermark["variants"]["kgw"] != canonical.KGW_AUTHOR_VARIANT:
        raise ValueError("Experiment requires the author-canonical KGW variant")
    conditions: dict[tuple[int, float], dict[str, Any]] = {}
    shared_table = None
    for key_index in config["generation"]["target_key_indices"]:
        for bias in config["generation"]["bias_candidates_in_selection_order"]:
            settings = dict(
                watermark["kgw"], hashing_key=kgw_keys[int(key_index)], bias=float(bias)
            )
            generation_config = canonical.build_kgw_config(
                settings, watermark["variants"]["kgw"]
            )
            processor = generation_config.construct_processor(
                runner.model.config.vocab_size, runner.device
            )
            if shared_table is None:
                shared_table = processor.fixed_table
            else:
                processor.fixed_table = shared_table
            scorer = CompactKGWScorer(
                processor=processor,
                variant=watermark["variants"]["kgw"],
                key_id=f"kgw-{int(key_index):02d}",
                hashing_key=kgw_keys[int(key_index)],
                greenlist_ratio=float(settings["greenlist_ratio"]),
            )
            conditions[(int(key_index), float(bias))] = {
                "scheme": "kgw", "key_id": f"kgw-{int(key_index):02d}",
                "variant": watermark["variants"]["kgw"],
                "generation_config": generation_config, "scorer": scorer,
            }
    return conditions


def validate_existing(
    output_dir: Path, plan: list[dict[str, Any]], prompts: list[dict[str, Any]],
    batch_size: int, input_sha256: dict[str, str], generation: dict[str, Any],
) -> tuple[int, list[dict[str, Any]], Counter[str]]:
    paths = batch_paths(output_dir)
    if [path.name for path in paths] != [f"batch-{i:06d}.json" for i in range(len(paths))]:
        raise ValueError("Existing batches are not contiguous and zero-based")
    audits: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    keys = [int(v) for v in generation["target_key_indices"]]
    for index, path in enumerate(paths):
        batch, expected = load_json(path), plan[index]
        if batch.get("batch_index") != index or batch.get("input_sha256") != input_sha256:
            raise ValueError(f"Batch identity mismatch: {path}")
        for field in ("key_id", "bias", "prompt_start"):
            if batch.get(field) != expected[field]:
                raise ValueError(f"Batch plan mismatch: {path}")
        expected_seed = paired_batch_seed(
            int(generation["base_seed"]), keys, int(expected["key_index"]),
            int(expected["prompt_start"]), batch_size, int(generation["prompts_per_condition"]),
        )
        if batch.get("batch_seed") != expected_seed:
            raise ValueError(f"Paired seed mismatch: {path}")
        records = batch.get("records")
        if not isinstance(records, list) or len(records) != batch_size:
            raise ValueError(f"Incomplete batch: {path}")
        expected_ids = [row["id"] for row in prompts[expected["prompt_start"]:expected["prompt_start"] + batch_size]]
        if [row["prompt_id"] for row in records] != expected_ids:
            raise ValueError(f"Prompt order mismatch: {path}")
        audits.extend(batch.get("native_score_audits", []))
        counts.update([f"{expected['key_id']}/bias-{expected['bias']}"] * len(records))
    return len(paths), audits, counts


def run_digest(output_dir: Path) -> str:
    digest = hashlib.sha256()
    metadata = load_json(output_dir / "run.json")
    stable = {key: metadata[key] for key in (
        "schema_version", "status", "experiment_id", "completed_batches",
        "completed_outputs", "input_sha256",
    )}
    digest.update(json.dumps(stable, sort_keys=True).encode())
    for path in batch_paths(output_dir):
        digest.update(path.name.encode())
        digest.update(bytes.fromhex(file_sha256(path)))
    return digest.hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/phase2-v2-kgw-bias-development.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("results/phase2-v2-kgw-bias-development/run"))
    parser.add_argument("--limit-batches", type=int)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    config, manifest, _thresholds, kgw_keys = validate_inputs(args.config)
    prompts, generation = manifest["records"], config["generation"]
    batch_size = int(generation["batch_size"])
    keys = [int(v) for v in generation["target_key_indices"]]
    biases = [float(v) for v in generation["bias_candidates_in_selection_order"]]
    plan = batch_plan(keys, biases, int(generation["prompts_per_condition"]), batch_size)
    target_batches = len(plan)
    limit = target_batches if args.limit_batches is None else args.limit_batches
    if not 1 <= limit <= target_batches:
        parser.error(f"--limit-batches must be between 1 and {target_batches}")
    input_sha256 = {
        "config": file_sha256(args.config),
        "prompt_manifest": file_sha256(Path(config["prompt_manifest"])),
        "watermark_config": file_sha256(Path(config["watermark_config"])),
        "key_schedule_source": file_sha256(Path(config["key_schedule"]["source_config"])),
        "provisional_thresholds": file_sha256(Path(config["provisional_thresholds"]["artifact"])),
        "runner_source": source_sha256(),
    }
    if args.dry_run:
        print(json.dumps({
            "status": "configuration_valid", "experiment_id": config["experiment_id"],
            "prompts": len(prompts), "target_keys": keys, "biases": biases,
            "target_cells": len(keys) * len(generation["paired_prefix_lengths"]),
            "target_batches": target_batches, "selected_batches": limit,
            "target_outputs": target_batches * batch_size,
            "confirmation_scores_used": False, "input_sha256": input_sha256,
        }, indent=2))
        return 0

    completed, audits, counts = validate_existing(
        args.output_dir, plan, prompts, batch_size, input_sha256, generation
    )
    if completed >= limit:
        print(json.dumps({"status": "already_complete", "batches": completed}, indent=2))
        return 0
    runner = TransformersNativeRunner(**{
        "model_id": config["model"]["id"], "revision": config["model"]["revision"],
        "device": config["model"]["device"],
    })
    conditions = build_conditions(config, kgw_keys, runner)
    lengths = [int(v) for v in generation["paired_prefix_lengths"]]
    torch, transformers = require_ml_dependencies()
    for batch_index in range(completed, limit):
        spec = plan[batch_index]
        condition = conditions[(int(spec["key_index"]), float(spec["bias"]))]
        start = int(spec["prompt_start"])
        prompt_batch = prompts[start:start + batch_size]
        batch_seed = paired_batch_seed(
            int(generation["base_seed"]), keys, int(spec["key_index"]), start,
            batch_size, int(generation["prompts_per_condition"]),
        )
        generated_rows = runner.generate_batch(
            [row["prompt"] for row in prompt_batch], seed=batch_seed,
            min_new_tokens=int(generation["generated_tokens"]),
            max_new_tokens=int(generation["generated_tokens"]),
            temperature=float(generation["temperature"]), top_k=int(generation["top_k"]),
            watermark_config=condition["generation_config"],
        )
        batch_records, batch_audits = [], []
        for stream_index, (prompt, generated) in enumerate(zip(prompt_batch, generated_rows, strict=True)):
            _, continuation, text_value = generated
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
            batch_records.append({
                "prompt_id": prompt["id"], "source_shard": prompt["source_shard"],
                "source_row": prompt["source_row"], "source_prompt_id": prompt["source_prompt_id"],
                "prompt_sha256": prompt["prompt_sha256"], "condition": "watermarked",
                "scheme": "kgw", "key_id": condition["key_id"], "bias": float(spec["bias"]),
                "variant": condition["variant"], "batch_seed": batch_seed,
                "batch_stream_index": stream_index, "generated_tokens": len(continuation),
                "token_ids": continuation, "output_sha256": sha256_text(text_value),
                "text": text_value, "prefix_results": prefix_results,
            })
        atomic_json(args.output_dir / "batches" / f"batch-{batch_index:06d}.json", {
            "schema_version": 1, "experiment_id": config["experiment_id"],
            "batch_index": batch_index, "key_id": condition["key_id"],
            "bias": float(spec["bias"]), "prompt_start": start, "batch_seed": batch_seed,
            "input_sha256": input_sha256, "native_score_audits": batch_audits,
            "records": batch_records,
        })
        audits.extend(batch_audits)
        counts.update([f"{condition['key_id']}/bias-{spec['bias']}"] * batch_size)
        completed = batch_index + 1
        complete = completed == target_batches
        metadata = {
            "schema_version": 1,
            "status": "kgw_bias_development_complete" if complete else "kgw_bias_development_partial",
            "experiment_id": config["experiment_id"], "generated_at": datetime.now(timezone.utc).isoformat(),
            "scope": config["scope"], "completed_batches": completed, "target_batches": target_batches,
            "completed_outputs": completed * batch_size, "target_outputs": target_batches * batch_size,
            "input_sha256": input_sha256,
            "environment": {
                "python": platform.python_version(), "platform": platform.platform(),
                "torch": torch.__version__, "transformers": transformers.__version__,
                "package_version": importlib.metadata.version("ai-watermarks-research"),
                "git_commit": git_commit(), "git_dirty": git_dirty(),
            },
            "condition_output_counts": dict(sorted(counts.items())),
            "native_score_audits": audits, "confirmation_scores_used": False,
        }
        atomic_json(args.output_dir / "run.json", metadata)
        print(f"checkpoint batch {completed}/{target_batches} outputs {completed * batch_size}/{target_batches * batch_size}", flush=True)
    print(json.dumps({
        "status": metadata["status"], "batches": completed,
        "outputs": completed * batch_size, "output_dir": str(args.output_dir),
        "run_digest": run_digest(args.output_dir),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
