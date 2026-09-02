#!/usr/bin/env python3
"""Freeze leakage-safe calibration and confirmation prompt manifests."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from ai_watermarks_phase2.native import require_ml_dependencies
from ai_watermarks_phase2.smoke import load_json
from prepare_phase2_null_prompts import format_prompt, normalized, sha256_bytes


def manifest_records(path: Path) -> list[dict[str, Any]]:
    value = load_json(path)
    if isinstance(value, list):
        return value
    if isinstance(value, dict) and isinstance(value.get("records"), list):
        return value["records"]
    raise ValueError(f"Unsupported exclusion-manifest shape: {path}")


def exclusion_keys(paths: list[Path]) -> tuple[set[int], set[str], set[str]]:
    rows: set[int] = set()
    hashes: set[str] = set()
    prompts: set[str] = set()
    for path in paths:
        for record in manifest_records(path):
            if isinstance(record.get("source_row"), int):
                rows.add(record["source_row"])
            prompt = record.get("prompt")
            if isinstance(prompt, str) and prompt.strip():
                prompts.add(normalized(prompt))
                hashes.add(hashlib.sha256(prompt.encode("utf-8")).hexdigest())
            if isinstance(record.get("prompt_sha256"), str):
                hashes.add(record["prompt_sha256"])
    return rows, hashes, prompts


def hamilton_quotas(counts: dict[str, int], target: int) -> dict[str, int]:
    total = sum(counts.values())
    raw = {category: target * count / total for category, count in counts.items()}
    quotas = {category: math.floor(value) for category, value in raw.items()}
    remaining = target - sum(quotas.values())
    order = sorted(counts, key=lambda category: (-(raw[category] - quotas[category]), category))
    for category in order[:remaining]:
        quotas[category] += 1
    if sum(quotas.values()) != target:
        raise RuntimeError("Hamilton allocation did not reach its target")
    return quotas


def rank(seed: str, split: str, candidate: dict[str, Any]) -> str:
    material = (
        f"{seed}\0{split}\0{candidate['category']}\0{candidate['source_row']}\0"
        f"{candidate['prompt_sha256']}"
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def build_manifest(
    *,
    config: dict[str, Any],
    split: str,
    records: list[dict[str, Any]],
    quotas: dict[str, int],
    eligible_counts: dict[str, int],
    exclusion_paths: list[Path],
    generator_sha256: str,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "protocol_id": config["protocol_id"],
        "scope": config["scope"],
        "split_role": split,
        "source": config["source"],
        "selection": {
            **config["selection"],
            "category_allocation": dict(sorted(quotas.items())),
            "eligible_category_counts_before_split_selection": dict(
                sorted(eligible_counts.items())
            ),
            "exclusion_manifest_sha256": {
                str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in exclusion_paths
            },
            "generator_sha256": generator_sha256,
        },
        "model_tokenizer": config["model"],
        "record_count": len(records),
        "records": records,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument(
        "--config", type=Path, default=Path("configs/phase2-confirmatory-null.json")
    )
    parser.add_argument(
        "--calibration-output",
        type=Path,
        default=Path("data/phase2-confirmatory-calibration-prompts.json"),
    )
    parser.add_argument(
        "--confirmation-output",
        type=Path,
        default=Path("data/phase2-confirmatory-confirmation-prompts.json"),
    )
    parser.add_argument("--capacity-only", action="store_true")
    args = parser.parse_args(argv)

    config = load_json(args.config)
    source_bytes = args.source.read_bytes()
    observed_sha = sha256_bytes(source_bytes)
    if observed_sha != config["source"]["file_sha256"]:
        raise ValueError(
            f"Source SHA-256 mismatch: expected {config['source']['file_sha256']}, "
            f"found {observed_sha}"
        )
    source_rows = [json.loads(line) for line in source_bytes.splitlines() if line.strip()]
    exclusion_paths = [Path(path) for path in config["selection"]["exclusion_manifests"]]
    excluded_rows, excluded_hashes, excluded_prompts = exclusion_keys(exclusion_paths)

    _, transformers = require_ml_dependencies()
    tokenizer = transformers.AutoTokenizer.from_pretrained(
        config["model"]["id"], revision=config["model"]["revision"]
    )
    max_tokens = int(config["selection"]["max_prompt_tokens"])
    candidates: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen = set(excluded_prompts)
    rejected = Counter()
    for source_row, row in enumerate(source_rows):
        prompt = format_prompt(row)
        prompt_norm = normalized(prompt)
        prompt_sha = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        if source_row in excluded_rows or prompt_sha in excluded_hashes or prompt_norm in seen:
            rejected["excluded_or_duplicate"] += 1
            continue
        seen.add(prompt_norm)
        token_count = len(
            tokenizer(
                prompt,
                add_special_tokens=True,
                truncation=True,
                max_length=max_tokens + 1,
            )["input_ids"]
        )
        if token_count > max_tokens:
            rejected["too_long"] += 1
            continue
        category = str(row["category"])
        candidates[category].append(
            {
                "source_row": source_row,
                "category": category,
                "prompt": prompt,
                "prompt_tokens": token_count,
                "prompt_sha256": prompt_sha,
            }
        )

    counts = {category: len(items) for category, items in candidates.items()}
    split_size = int(config["selection"]["samples_per_split"])
    quotas = hamilton_quotas(counts, split_size)
    insufficient = {
        category: {"eligible": counts[category], "needed": 2 * quota}
        for category, quota in quotas.items()
        if counts[category] < 2 * quota
    }
    capacity = {
        "status": "capacity_valid" if not insufficient else "capacity_insufficient",
        "source_rows": len(source_rows),
        "excluded_source_rows": len(excluded_rows),
        "eligible_records": sum(counts.values()),
        "eligible_category_counts": dict(sorted(counts.items())),
        "per_split_category_allocation": dict(sorted(quotas.items())),
        "rejected": dict(sorted(rejected.items())),
        "insufficient": insufficient,
    }
    print(json.dumps(capacity, indent=2))
    if insufficient:
        return 1
    if args.capacity_only:
        return 0

    seed = str(config["selection"]["selection_seed"])
    selected: dict[str, list[dict[str, Any]]] = {"calibration": [], "confirmation": []}
    used_rows: set[int] = set()
    for split in ("calibration", "confirmation"):
        for category, quota in quotas.items():
            available = [item for item in candidates[category] if item["source_row"] not in used_rows]
            available.sort(key=lambda item: (rank(seed, split, item), item["source_row"]))
            chosen = available[:quota]
            if len(chosen) != quota:
                raise RuntimeError(f"Could not fill {split}/{category}: {len(chosen)} of {quota}")
            selected[split].extend(chosen)
            used_rows.update(item["source_row"] for item in chosen)
        selected[split].sort(
            key=lambda item: hashlib.sha256(
                f"{seed}\0{split}\0final\0{item['prompt_sha256']}".encode("utf-8")
            ).hexdigest()
        )
        for index, item in enumerate(selected[split]):
            item["id"] = f"{split}-{index:04d}"

    calibration_hashes = {item["prompt_sha256"] for item in selected["calibration"]}
    confirmation_hashes = {item["prompt_sha256"] for item in selected["confirmation"]}
    if calibration_hashes & confirmation_hashes:
        raise RuntimeError("Calibration and confirmation prompt hashes overlap")
    generator_sha = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    manifests = {
        "calibration": build_manifest(
            config=config,
            split="calibration",
            records=selected["calibration"],
            quotas=quotas,
            eligible_counts=counts,
            exclusion_paths=exclusion_paths,
            generator_sha256=generator_sha,
        ),
        "confirmation": build_manifest(
            config=config,
            split="confirmation",
            records=selected["confirmation"],
            quotas=quotas,
            eligible_counts=counts,
            exclusion_paths=exclusion_paths,
            generator_sha256=generator_sha,
        ),
    }
    for path, split in (
        (args.calibration_output, "calibration"),
        (args.confirmation_output, "confirmation"),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(manifests[split], indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "manifests_complete",
                "calibration": str(args.calibration_output),
                "confirmation": str(args.confirmation_output),
                "records_per_split": split_size,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
