#!/usr/bin/env python3
"""Build the frozen, stratified Phase 2 null-calibration prompt manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from ai_watermarks_phase2.native import require_ml_dependencies
from ai_watermarks_phase2.smoke import load_json


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def normalized(value: str) -> str:
    return " ".join(value.split()).casefold()


def format_prompt(row: dict[str, Any]) -> str:
    instruction = " ".join(str(row["instruction"]).split())
    context = str(row.get("context", "")).strip()
    if not context:
        return instruction
    return f"{instruction}\n\nReference context:\n{context}"


def rank(seed: str, category: str, row_index: int, prompt: str) -> str:
    material = f"{seed}\0{category}\0{row_index}\0{normalized(prompt)}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def select_rows(
    rows: list[dict[str, Any]], config: dict[str, Any], tokenizer: Any
) -> list[dict[str, Any]]:
    selection = config["selection"]
    allocation = selection["category_allocation"]
    max_tokens = int(selection["max_prompt_tokens"])
    seed = str(selection["selection_seed"])
    candidates: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: set[str] = set()

    for row_index, row in enumerate(rows):
        category = row.get("category")
        if category not in allocation:
            continue
        prompt = format_prompt(row)
        dedupe_key = normalized(prompt)
        if not dedupe_key or dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        token_count = len(
            tokenizer(
                prompt,
                add_special_tokens=True,
                truncation=True,
                max_length=max_tokens + 1,
            )["input_ids"]
        )
        if token_count > max_tokens:
            continue
        candidates[category].append(
            {
                "source_row": row_index,
                "category": category,
                "prompt": prompt,
                "prompt_tokens": token_count,
                "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
                "selection_rank": rank(seed, category, row_index, prompt),
            }
        )

    selected: list[dict[str, Any]] = []
    for category, quota in allocation.items():
        available = sorted(
            candidates[category], key=lambda item: (item["selection_rank"], item["source_row"])
        )
        if len(available) < int(quota):
            raise ValueError(
                f"Category {category!r} has {len(available)} eligible rows, needs {quota}"
            )
        selected.extend(available[: int(quota)])

    selected.sort(
        key=lambda item: hashlib.sha256(
            f"{seed}\0final-order\0{item['selection_rank']}".encode("utf-8")
        ).hexdigest()
    )
    for index, item in enumerate(selected):
        item["id"] = f"null-{index:04d}"
        del item["selection_rank"]
    return selected


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument(
        "--config", type=Path, default=Path("configs/phase2-null-calibration.json")
    )
    parser.add_argument(
        "--output", type=Path, default=Path("data/phase2-null-calibration-prompts.json")
    )
    args = parser.parse_args(argv)

    config = load_json(args.config)
    source_bytes = args.source.read_bytes()
    observed_sha = sha256_bytes(source_bytes)
    expected_sha = config["source"]["file_sha256"]
    if observed_sha != expected_sha:
        raise ValueError(f"Source SHA-256 mismatch: expected {expected_sha}, found {observed_sha}")
    rows = [json.loads(line) for line in source_bytes.splitlines() if line.strip()]

    _, transformers = require_ml_dependencies()
    smoke_config = load_json(Path(config["watermark_config"]))
    tokenizer = transformers.AutoTokenizer.from_pretrained(
        smoke_config["model"]["id"], revision=smoke_config["model"]["revision"]
    )
    selected = select_rows(rows, config, tokenizer)
    target = int(config["selection"]["target_samples"])
    if len(selected) != target:
        raise ValueError(f"Expected {target} selected prompts, found {len(selected)}")

    manifest = {
        "schema_version": 1,
        "scope": config["scope"],
        "source": config["source"],
        "selection": config["selection"],
        "model_tokenizer": {
            "id": smoke_config["model"]["id"],
            "revision": smoke_config["model"]["revision"],
        },
        "records": selected,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "manifest_complete", "records": len(selected), "output": str(args.output)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
