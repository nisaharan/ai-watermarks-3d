#!/usr/bin/env python3
"""Audit the pinned UltraChat source for a possible Phase 2 replacement study."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from ai_watermarks_phase2.native import require_ml_dependencies
from ai_watermarks_phase2.smoke import load_json


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalized(value: str) -> str:
    return " ".join(value.split()).casefold()


def manifest_records(path: Path) -> list[dict[str, Any]]:
    value = load_json(path)
    if isinstance(value, list):
        return value
    if isinstance(value, dict) and isinstance(value.get("records"), list):
        return value["records"]
    raise ValueError(f"Unsupported exclusion-manifest shape: {path}")


def percentile(values: list[int], fraction: float) -> int:
    if not values:
        raise ValueError("Cannot calculate a percentile of an empty list")
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round(fraction * (len(ordered) - 1))))
    return ordered[index]


def exclusion_keys(paths: list[Path]) -> tuple[set[str], set[str]]:
    hashes: set[str] = set()
    prompts: set[str] = set()
    for path in paths:
        for record in manifest_records(path):
            prompt = record.get("prompt")
            if isinstance(prompt, str) and prompt.strip():
                prompts.add(normalized(prompt))
                hashes.add(hashlib.sha256(prompt.encode("utf-8")).hexdigest())
            prompt_hash = record.get("prompt_sha256")
            if isinstance(prompt_hash, str):
                hashes.add(prompt_hash)
    return hashes, prompts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/phase2-confirmatory-null-v2-draft.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/phase2-ultrachat-source-audit.json"),
    )
    parser.add_argument("--batch-size", type=int, default=512)
    args = parser.parse_args(argv)

    config = load_json(args.config)
    if config.get("status") != "draft_not_authorized_for_generation":
        raise ValueError("Source audit expects a non-executable draft config")

    card = config["source"]["dataset_card"]
    card_path = Path(card["path"])
    card_sha256 = file_sha256(card_path)
    if card_sha256 != card["sha256"]:
        raise ValueError(f"Dataset-card hash mismatch: {card_path}")

    source_rows_expected = 0
    source_files: list[dict[str, Any]] = []
    for item in config["source"]["files"]:
        source_path = Path(item["path"])
        extract_path = Path(item["prompt_extract"])
        observed_source_sha = file_sha256(source_path)
        observed_extract_sha = file_sha256(extract_path)
        if observed_source_sha != item["sha256"]:
            raise ValueError(f"Source hash mismatch: {source_path}")
        if observed_extract_sha != item["prompt_extract_sha256"]:
            raise ValueError(f"Prompt-extract hash mismatch: {extract_path}")
        source_rows_expected += int(item["rows"])
        source_files.append(
            {
                "path": str(source_path),
                "sha256": observed_source_sha,
                "rows": int(item["rows"]),
                "prompt_extract": str(extract_path),
                "prompt_extract_sha256": observed_extract_sha,
            }
        )

    exclusion_paths = [Path(path) for path in config["selection"]["exclusion_manifests"]]
    excluded_hashes, excluded_prompts = exclusion_keys(exclusion_paths)
    _, transformers = require_ml_dependencies()
    tokenizer = transformers.AutoTokenizer.from_pretrained(
        config["model"]["id"], revision=config["model"]["revision"]
    )

    max_tokens = int(config["selection"]["max_prompt_tokens"])
    seen_ids: set[str] = set()
    seen_prompts: set[str] = set()
    rejected: Counter[str] = Counter()
    prompt_token_counts: list[int] = []
    source_rows_observed = 0
    candidates: list[str] = []

    def audit_batch(prompts: list[str]) -> None:
        if not prompts:
            return
        lengths = tokenizer(
            prompts,
            add_special_tokens=True,
            truncation=True,
            max_length=max_tokens + 1,
            return_length=True,
        )["length"]
        for length in lengths:
            value = int(length)
            prompt_token_counts.append(value)
            if value > max_tokens:
                rejected["too_long"] += 1

    for item in source_files:
        path = Path(item["prompt_extract"])
        shard_rows = 0
        with path.open(encoding="utf-8") as handle:
            for expected_shard_row, line in enumerate(handle):
                row = json.loads(line)
                shard_rows += 1
                source_rows_observed += 1
                if int(row["shard_row"]) != expected_shard_row:
                    raise ValueError(f"Non-contiguous shard row in {path}")
                prompt_id = str(row["prompt_id"])
                prompt = str(row["prompt"])
                prompt_norm = normalized(prompt)
                prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
                if prompt_id in seen_ids:
                    rejected["duplicate_prompt_id"] += 1
                    continue
                seen_ids.add(prompt_id)
                if not prompt_norm:
                    rejected["empty_prompt"] += 1
                    continue
                if prompt_norm in seen_prompts:
                    rejected["duplicate_normalized_prompt"] += 1
                    continue
                seen_prompts.add(prompt_norm)
                if prompt_hash in excluded_hashes or prompt_norm in excluded_prompts:
                    rejected["prior_study_overlap"] += 1
                    continue
                candidates.append(prompt)
                if len(candidates) >= args.batch_size:
                    audit_batch(candidates)
                    candidates.clear()
        if shard_rows != int(item["rows"]):
            raise ValueError(f"Row count mismatch: {path}")
    audit_batch(candidates)

    if source_rows_observed != source_rows_expected:
        raise ValueError("Total source row count mismatch")
    eligible_records = len(prompt_token_counts) - rejected["too_long"]
    required_records = 2 * int(config["selection"]["samples_per_split"])
    result = {
        "schema_version": 1,
        "status": "capacity_valid" if eligible_records >= required_records else "capacity_insufficient",
        "config": str(args.config),
        "config_sha256": file_sha256(args.config),
        "source": {
            "dataset": config["source"]["dataset"],
            "revision": config["source"]["revision"],
            "split": config["source"]["split"],
            "dataset_card": {
                "path": str(card_path),
                "sha256": card_sha256,
            },
            "files": source_files,
            "rows": source_rows_observed,
            "unique_prompt_ids": len(seen_ids),
            "unique_normalized_prompts": len(seen_prompts),
        },
        "selection": {
            "required_records": required_records,
            "eligible_records": eligible_records,
            "capacity_surplus": eligible_records - required_records,
            "max_prompt_tokens": max_tokens,
            "rejected": dict(sorted(rejected.items())),
            "prompt_tokens_before_length_rejection": {
                "minimum": min(prompt_token_counts),
                "median": percentile(prompt_token_counts, 0.5),
                "p95": percentile(prompt_token_counts, 0.95),
                "p99": percentile(prompt_token_counts, 0.99),
                "maximum_censored_at": max(prompt_token_counts),
            },
            "exclusion_manifest_sha256": {
                str(path): file_sha256(path) for path in exclusion_paths
            },
        },
        "authorization": "source audit only; no manifests, thresholds, or generations produced",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "capacity_valid" else 1


if __name__ == "__main__":
    raise SystemExit(main())
