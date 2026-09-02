"""Generate and score the fresh development null for KGW gamma selection."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import platform
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from . import canonical
from .compact_scoring import CompactKGWScorer
from .confirmatory_null import atomic_json
from .kgw_joint_protocol import (
    CONFIG_PATH,
    candidate_grid,
    validate_authorization,
    validate_manifests,
    validate_protocol,
)
from .native import TransformersNativeRunner, require_ml_dependencies
from .positive_sensitivity import audit_score
from .smoke import git_commit, git_dirty, load_json, sha256_text
from .variance_pilot import file_sha256


DEFAULT_OUTPUT = Path("results/phase2-v2-kgw-joint-feasibility/development-null")


def source_sha256() -> str:
    digest = hashlib.sha256()
    for path in (
        Path("uv.lock"),
        Path("src/ai_watermarks_phase2/canonical.py"),
        Path("src/ai_watermarks_phase2/compact_scoring.py"),
        Path("src/ai_watermarks_phase2/native.py"),
        Path("src/ai_watermarks_phase2/kgw_joint_protocol.py"),
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
        if not isinstance(batch.get("records"), list):
            raise ValueError(f"Malformed batch: {path}")
        yield from batch["records"]


def run_digest(output_dir: Path) -> str:
    metadata = load_json(output_dir / "run.json")
    stable = {
        key: metadata[key]
        for key in (
            "schema_version",
            "status",
            "protocol_id",
            "split_role",
            "records",
            "input_sha256",
        )
    }
    digest = hashlib.sha256(json.dumps(stable, sort_keys=True).encode())
    for path in batch_paths(output_dir):
        digest.update(path.name.encode())
        digest.update(bytes.fromhex(file_sha256(path)))
    return digest.hexdigest()


def build_conditions(
    config: dict[str, Any], runner: TransformersNativeRunner
) -> list[dict[str, Any]]:
    watermark = load_json(Path(config["watermark_config"]))
    if watermark["variants"]["kgw"] != canonical.KGW_AUTHOR_VARIANT:
        raise ValueError("Development null requires author-canonical KGW")
    schedule_source = load_json(Path(config["key_schedule"]["source_config"]))
    keys = [int(value) for value in schedule_source["key_schedule"]["kgw"]]
    gammas = sorted({gamma for gamma, _ in candidate_grid(config)})
    conditions: list[dict[str, Any]] = []
    shared_table = None
    for gamma in gammas:
        for key_index, key in enumerate(keys):
            settings = dict(
                watermark["kgw"],
                hashing_key=key,
                greenlist_ratio=gamma,
            )
            generation_config = canonical.build_kgw_config(
                settings, canonical.KGW_AUTHOR_VARIANT
            )
            processor = generation_config.construct_processor(
                runner.model.config.vocab_size, runner.device
            )
            if shared_table is None:
                shared_table = processor.fixed_table
            else:
                processor.fixed_table = shared_table
            conditions.append(
                {
                    "scheme": "kgw",
                    "gamma": gamma,
                    "key_id": f"kgw-{key_index:02d}",
                    "key_index": key_index,
                    "variant": canonical.KGW_AUTHOR_VARIANT,
                    "generation_config": generation_config,
                    "scorer": CompactKGWScorer(
                        processor=processor,
                        variant=canonical.KGW_AUTHOR_VARIANT,
                        key_id=f"kgw-{key_index:02d}",
                        hashing_key=key,
                        greenlist_ratio=gamma,
                    ),
                }
            )
    return conditions


def validate_existing(
    output_dir: Path,
    prompts: list[dict[str, Any]],
    batch_size: int,
    input_sha256: dict[str, str],
) -> tuple[int, list[dict[str, Any]]]:
    paths = batch_paths(output_dir)
    if [path.name for path in paths] != [
        f"batch-{index:06d}.json" for index in range(len(paths))
    ]:
        raise ValueError("Existing development-null batches are not contiguous")
    observed_ids: list[str] = []
    audits: list[dict[str, Any]] = []
    for index, path in enumerate(paths):
        batch = load_json(path)
        if batch.get("batch_index") != index or batch.get("input_sha256") != input_sha256:
            raise ValueError(f"Batch identity mismatch: {path}")
        records = batch.get("records")
        if not isinstance(records, list) or len(records) != batch_size:
            raise ValueError(f"Incomplete batch: {path}")
        observed_ids.extend(str(row["prompt_id"]) for row in records)
        if batch.get("native_score_audits"):
            if audits:
                raise ValueError("Native audits appear in more than one batch")
            audits = batch["native_score_audits"]
    if observed_ids != [row["id"] for row in prompts[: len(observed_ids)]]:
        raise ValueError("Existing development-null prompt order differs")
    return len(observed_ids), audits


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    parser.add_argument("--authorization", type=Path)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    config = load_json(args.config)
    plan = validate_protocol(config)
    manifest_hashes = validate_manifests(config)
    manifest_path = Path(config["prompt_manifests"]["development_null"])
    manifest = load_json(manifest_path)
    prompts = manifest["records"]
    generation = config["generation"]["development_null"]
    target = int(generation["outputs"])
    batch_size = int(config["generation"]["batch_size"])
    limit = target if args.limit is None else int(args.limit)
    if not 1 <= limit <= target or limit % batch_size:
        parser.error(f"--limit must be a multiple of {batch_size} in [{batch_size}, {target}]")

    dry_run_result = {
        "status": "configuration_valid_generation_unauthorized",
        "protocol_id": config["protocol_id"],
        "split_role": "development_null",
        "prompts": target,
        "selected": limit,
        "batches": limit // batch_size,
        "gamma_key_length_cells": plan["development_null_primary_cells"],
        "maximum_strict_exceedances": plan[
            "development_null_maximum_strict_exceedances"
        ],
        "prompt_manifest_sha256": manifest_hashes["development_null"],
        "generation_authorized": False,
    }
    if args.dry_run:
        print(json.dumps(dry_run_result, indent=2))
        return 0
    if args.authorization is None:
        parser.error("generation requires --authorization")
    validate_authorization(args.config, args.authorization)

    input_sha256 = {
        "protocol_config": file_sha256(args.config),
        "authorization": file_sha256(args.authorization),
        "prompt_manifest": file_sha256(manifest_path),
        "watermark_config": file_sha256(Path(config["watermark_config"])),
        "key_schedule_source": file_sha256(Path(config["key_schedule"]["source_config"])),
        "runner_source": source_sha256(),
    }
    completed, audits = validate_existing(
        args.output_dir, prompts, batch_size, input_sha256
    )
    if completed >= limit:
        print(json.dumps({"status": "already_complete", "records": completed}, indent=2))
        return 0

    runner = TransformersNativeRunner(
        model_id=config["model"]["id"],
        revision=config["model"]["revision"],
        device=config["model"]["device"],
    )
    conditions = build_conditions(config, runner)
    lengths = [int(value) for value in generation["paired_prefix_lengths"]]
    torch, transformers = require_ml_dependencies()
    for batch_start in range(completed, limit, batch_size):
        batch_index = batch_start // batch_size
        prompt_batch = prompts[batch_start : batch_start + batch_size]
        batch_seed = int(generation["base_seed"]) + batch_index
        generated_rows = runner.generate_batch(
            [row["prompt"] for row in prompt_batch],
            seed=batch_seed,
            min_new_tokens=int(generation["generated_tokens"]),
            max_new_tokens=int(generation["generated_tokens"]),
            temperature=float(config["generation"]["temperature"]),
            top_k=int(config["generation"]["top_k"]),
            watermark_config=None,
        )
        batch_records: list[dict[str, Any]] = []
        batch_audits: list[dict[str, Any]] = []
        for stream_index, (prompt, generated) in enumerate(
            zip(prompt_batch, generated_rows, strict=True)
        ):
            _, continuation, text_value = generated
            if len(continuation) != int(generation["generated_tokens"]):
                raise RuntimeError(f"Unexpected generated length: {prompt['id']}")
            scored = [
                condition["scorer"].score_prefixes(continuation, lengths)
                for condition in conditions
            ]
            prefix_results = []
            for length in lengths:
                scores = [row[length] for row in scored]
                if any(
                    not math.isfinite(float(score["value"]))
                    or int(score["eligible_positions"]) <= 0
                    for score in scores
                ):
                    raise RuntimeError(f"Invalid compact score: {prompt['id']}")
                prefix_results.append({"length": length, "scores": scores})
            if completed == 0 and stream_index == 0:
                for condition, by_length in zip(conditions, scored, strict=True):
                    for length in lengths:
                        audit = audit_score(
                            runner, condition, continuation, length, by_length[length]
                        )
                        audit["gamma"] = condition["gamma"]
                        batch_audits.append(audit)
            batch_records.append(
                {
                    "prompt_id": prompt["id"],
                    "source_shard": prompt["source_shard"],
                    "source_row": prompt["source_row"],
                    "source_prompt_id": prompt["source_prompt_id"],
                    "prompt_sha256": prompt["prompt_sha256"],
                    "condition": "unwatermarked",
                    "batch_seed": batch_seed,
                    "batch_stream_index": stream_index,
                    "generated_tokens": len(continuation),
                    "token_ids": continuation,
                    "output_sha256": sha256_text(text_value),
                    "text": text_value,
                    "prefix_results": prefix_results,
                }
            )
        atomic_json(
            args.output_dir / "batches" / f"batch-{batch_index:06d}.json",
            {
                "schema_version": 1,
                "protocol_id": config["protocol_id"],
                "split_role": "development_null",
                "batch_index": batch_index,
                "batch_seed": batch_seed,
                "input_sha256": input_sha256,
                "native_score_audits": batch_audits,
                "records": batch_records,
            },
        )
        if batch_audits:
            audits = batch_audits
        completed += batch_size
        metadata = {
            "schema_version": 1,
            "status": (
                "kgw_joint_development_null_complete"
                if completed == target
                else "kgw_joint_development_null_partial"
            ),
            "protocol_id": config["protocol_id"],
            "split_role": "development_null",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "records": completed,
            "target_records": target,
            "batch_size": batch_size,
            "input_sha256": input_sha256,
            "native_score_audits": audits,
            "confirmation_scores_used": False,
            "environment": {
                "python": platform.python_version(),
                "platform": platform.platform(),
                "torch": torch.__version__,
                "transformers": transformers.__version__,
                "package_version": importlib.metadata.version("ai-watermarks-research"),
                "git_commit": git_commit(),
                "git_dirty": git_dirty(),
            },
        }
        atomic_json(args.output_dir / "run.json", metadata)
        print(f"checkpoint {completed}/{target}", flush=True)
    print(
        json.dumps(
            {
                "status": metadata["status"],
                "records": completed,
                "output_dir": str(args.output_dir),
                "run_digest": run_digest(args.output_dir),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
