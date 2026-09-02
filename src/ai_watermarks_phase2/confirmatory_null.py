"""Run leakage-separated, sharded Phase 2 confirmatory null generation."""

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

from .native import TransformersNativeRunner, require_ml_dependencies
from .smoke import git_commit, git_dirty, load_json, sha256_text
from .variance_pilot import (
    audit_primary_scores,
    build_scorers,
    file_sha256,
    runner_source_sha256,
    validate_design,
    write_result,
)


SPLIT_MANIFESTS = {
    "calibration": Path("data/phase2-confirmatory-calibration-prompts.json"),
    "confirmation": Path("data/phase2-confirmatory-confirmation-prompts.json"),
}


def confirmatory_source_sha256() -> str:
    digest = hashlib.sha256()
    for path in (
        Path("src/ai_watermarks_phase2/confirmatory_null.py"),
        Path("validation/prepare_phase2_confirmatory_prompts.py"),
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


def iter_sharded_records(output_dir: Path) -> Iterator[dict[str, Any]]:
    for path in batch_paths(output_dir):
        batch = load_json(path)
        if not isinstance(batch, dict) or not isinstance(batch.get("records"), list):
            raise ValueError(f"Malformed batch file: {path}")
        yield from batch["records"]


def sharded_run_digest(output_dir: Path) -> str:
    digest = hashlib.sha256()
    metadata_path = output_dir / "run.json"
    metadata = load_json(metadata_path)
    stable_metadata = {
        key: metadata[key]
        for key in (
            "schema_version",
            "status",
            "protocol_id",
            "split_role",
            "records",
            "input_sha256",
            "category_counts",
        )
    }
    digest.update(json.dumps(stable_metadata, sort_keys=True).encode("utf-8"))
    for path in batch_paths(output_dir):
        digest.update(path.name.encode("utf-8"))
        digest.update(bytes.fromhex(file_sha256(path)))
    return digest.hexdigest()


def effective_config(protocol: dict[str, Any], split: str) -> dict[str, Any]:
    watermark = load_json(Path(protocol["watermark_config"]))
    schedule_source = load_json(Path(protocol["key_schedule"]["source_config"]))
    generation = protocol["generation"]
    return {
        "schema_version": 1,
        "scope": protocol["scope"],
        "protocol_id": protocol["protocol_id"],
        "split_role": split,
        "prompt_manifest": str(SPLIT_MANIFESTS[split]),
        "watermark_config": protocol["watermark_config"],
        "model": protocol["model"],
        "generation": {
            "base_seed": int(generation[f"{split}_base_seed"]),
            "batch_size": int(generation["batch_size"]),
            "generated_tokens": int(generation["generated_tokens"]),
            "paired_prefix_lengths": generation["paired_prefix_lengths"],
            "temperature": float(generation["temperature"]),
            "top_k": int(generation["top_k"]),
            "decoder_policy": generation["decoder_policy"],
        },
        "selection": {
            "prompts": int(protocol["selection"]["samples_per_split"]),
            "paired_design": True,
        },
        "key_schedule": schedule_source["key_schedule"],
        "variants": watermark["variants"],
        "storage": {
            "format": "atomic_json_batches",
            "generated_token_ids": True,
            "generated_text": True,
            "compact_score_trace_hashes": True,
            "full_native_trace_audit_samples_per_length": 1,
        },
    }


def validate_existing_batches(
    output_dir: Path,
    prompts: list[dict[str, Any]],
    batch_size: int,
    input_sha256: dict[str, str],
) -> tuple[int, list[dict[str, Any]], Counter[str]]:
    paths = batch_paths(output_dir)
    expected_names = [f"batch-{index:06d}.json" for index in range(len(paths))]
    if [path.name for path in paths] != expected_names:
        raise ValueError("Existing batch files are not a contiguous zero-based sequence")
    observed_ids: list[str] = []
    audits: list[dict[str, Any]] = []
    categories: Counter[str] = Counter()
    for index, path in enumerate(paths):
        batch = load_json(path)
        if batch.get("batch_index") != index or batch.get("input_sha256") != input_sha256:
            raise ValueError(f"Batch identity or input fingerprint mismatch: {path}")
        records = batch.get("records")
        if not isinstance(records, list) or len(records) != batch_size:
            raise ValueError(f"Incomplete frozen batch: {path}")
        observed_ids.extend(record["prompt_id"] for record in records)
        categories.update(record["category"] for record in records)
        if batch.get("native_trace_audits"):
            if audits:
                raise ValueError("Native audits appear in more than one batch")
            audits = batch["native_trace_audits"]
    expected_ids = [prompt["id"] for prompt in prompts[: len(observed_ids)]]
    if observed_ids != expected_ids:
        raise ValueError("Existing batch prompt order differs from the frozen manifest")
    return len(observed_ids), audits, categories


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--protocol", type=Path, default=Path("configs/phase2-confirmatory-null.json")
    )
    parser.add_argument("--split", choices=("calibration", "confirmation"), required=True)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--thresholds", type=Path)
    parser.add_argument("--authorize-confirmation", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    protocol = load_json(args.protocol)
    split = args.split
    output_dir = args.output_dir or Path(f"results/phase2-confirmatory-null/{split}")
    prompt_path = SPLIT_MANIFESTS[split]
    prompt_manifest = load_json(prompt_path)
    prompts = prompt_manifest["records"]
    config = effective_config(protocol, split)
    validate_design(config, prompts)
    if prompt_manifest.get("protocol_id") != protocol["protocol_id"]:
        raise ValueError("Prompt manifest and protocol IDs differ")
    if prompt_manifest.get("split_role") != split:
        raise ValueError("Prompt manifest has the wrong split role")

    if split == "confirmation":
        if not args.authorize_confirmation or args.thresholds is None:
            parser.error(
                "confirmation requires --authorize-confirmation and a frozen --thresholds artifact"
            )
        thresholds = load_json(args.thresholds)
        if thresholds.get("status") != "thresholds_frozen":
            raise ValueError("Confirmation requires a frozen threshold artifact")
        if thresholds.get("protocol_id") != protocol["protocol_id"]:
            raise ValueError("Threshold artifact and protocol IDs differ")

    target = int(config["selection"]["prompts"])
    limit = target if args.limit is None else args.limit
    batch_size = int(config["generation"]["batch_size"])
    if not 1 <= limit <= target or limit % batch_size:
        parser.error(f"--limit must be a multiple of {batch_size} between {batch_size} and {target}")

    input_sha256 = {
        "protocol": file_sha256(args.protocol),
        "prompt_manifest": file_sha256(prompt_path),
        "watermark_config": file_sha256(Path(protocol["watermark_config"])),
        "key_schedule_source": file_sha256(Path(protocol["key_schedule"]["source_config"])),
        "variance_runner_source": runner_source_sha256(),
        "confirmatory_runner_source": confirmatory_source_sha256(),
    }
    if split == "confirmation":
        input_sha256["thresholds"] = file_sha256(args.thresholds)

    if args.dry_run:
        print(
            json.dumps(
                {
                    "status": "configuration_valid",
                    "protocol_id": protocol["protocol_id"],
                    "split": split,
                    "prompts": target,
                    "selected": limit,
                    "batch_size": batch_size,
                    "batches": limit // batch_size,
                    "lengths": config["generation"]["paired_prefix_lengths"],
                    "keys_per_scheme": len(config["key_schedule"]["kgw"]),
                    "input_sha256": input_sha256,
                    "output_dir": str(output_dir),
                },
                indent=2,
            )
        )
        return 0

    completed, audits, categories = validate_existing_batches(
        output_dir, prompts, batch_size, input_sha256
    )
    if completed >= limit:
        print(json.dumps({"status": "already_complete", "records": completed}, indent=2))
        return 0

    watermark_config = load_json(Path(protocol["watermark_config"]))
    runner = TransformersNativeRunner(
        model_id=config["model"]["id"],
        revision=config["model"]["revision"],
        device=config["model"]["device"],
    )
    kgw_scorers, synthid_scorers, primary_kgw, primary_synthid = build_scorers(
        config, watermark_config, runner
    )
    generation = config["generation"]
    lengths = [int(value) for value in generation["paired_prefix_lengths"]]
    torch, transformers = require_ml_dependencies()

    for batch_start in range(completed, limit, batch_size):
        batch_index = batch_start // batch_size
        prompt_batch = prompts[batch_start : batch_start + batch_size]
        batch_seed = int(generation["base_seed"]) + batch_index
        generated_rows = runner.generate_batch(
            [item["prompt"] for item in prompt_batch],
            seed=batch_seed,
            min_new_tokens=int(generation["generated_tokens"]),
            max_new_tokens=int(generation["generated_tokens"]),
            temperature=float(generation["temperature"]),
            top_k=int(generation["top_k"]),
            watermark_config=None,
        )
        batch_records = []
        batch_audits = []
        for stream_index, (prompt, generated_row) in enumerate(
            zip(prompt_batch, generated_rows, strict=True)
        ):
            _, continuation, text = generated_row
            if len(continuation) != int(generation["generated_tokens"]):
                raise RuntimeError(f"Unexpected generated length for {prompt['id']}")
            kgw_by_key = [scorer.score_prefixes(continuation, lengths) for scorer in kgw_scorers]
            synthid_by_key = [
                scorer.score_prefixes(continuation, lengths) for scorer in synthid_scorers
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
            if completed == 0 and not audits and not batch_audits:
                for prefix_result in prefix_results:
                    batch_audits.append(
                        audit_primary_scores(
                            runner,
                            continuation,
                            prefix_result["length"],
                            prefix_result["scores"][0],
                            prefix_result["scores"][len(kgw_scorers)],
                            primary_kgw,
                            primary_synthid,
                            config["variants"],
                        )
                    )
            batch_records.append(
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

        batch_value = {
            "schema_version": 1,
            "protocol_id": protocol["protocol_id"],
            "split_role": split,
            "batch_index": batch_index,
            "batch_seed": batch_seed,
            "input_sha256": input_sha256,
            "native_trace_audits": batch_audits,
            "records": batch_records,
        }
        atomic_json(output_dir / "batches" / f"batch-{batch_index:06d}.json", batch_value)
        if batch_audits:
            audits = batch_audits
        categories.update(record["category"] for record in batch_records)
        completed += len(batch_records)
        metadata = {
            "schema_version": 1,
            "status": "confirmatory_split_complete" if completed == target else "confirmatory_split_partial",
            "protocol_id": protocol["protocol_id"],
            "split_role": split,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "scope": protocol["scope"],
            "records": completed,
            "target_records": target,
            "batch_size": batch_size,
            "batch_files": completed // batch_size,
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
            "category_counts": dict(sorted(categories.items())),
            "native_trace_audits": audits,
        }
        atomic_json(output_dir / "run.json", metadata)
        print(f"checkpoint {completed}/{target}", flush=True)

    print(
        json.dumps(
            {
                "status": metadata["status"],
                "records": completed,
                "output_dir": str(output_dir),
                "run_digest": sharded_run_digest(output_dir),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
