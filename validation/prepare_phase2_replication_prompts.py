#!/usr/bin/env python3
"""Freeze a balanced 104-prompt subset for independent-model replication."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


SOURCE = Path("data/phase2-null-calibration-prompts.json")
OUTPUT = Path("data/phase2-variance-replication-prompts.json")
PER_CATEGORY = 13


def main() -> int:
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    counts: Counter[str] = Counter()
    selected = []
    for record in source["records"]:
        category = record["category"]
        if counts[category] >= PER_CATEGORY:
            continue
        item = dict(record)
        item["source_prompt_id"] = item["id"]
        item["id"] = f"replication-{len(selected):04d}"
        selected.append(item)
        counts[category] += 1
    expected_categories = set(source["selection"]["category_allocation"])
    if set(counts) != expected_categories or any(
        counts[category] != PER_CATEGORY for category in expected_categories
    ):
        raise RuntimeError(f"Unable to select balanced replication set: {counts}")

    manifest = {
        "schema_version": 1,
        "scope": "Phase 2 independent-model null replication; not a publication threshold",
        "source": source["source"],
        "parent_manifest": str(SOURCE),
        "selection": {
            "rule": "first 13 frozen null-pilot records within each category",
            "target_samples": len(selected),
            "category_allocation": dict(sorted(counts.items())),
        },
        "model_tokenizer": {
            "id": "Qwen/Qwen2.5-0.5B-Instruct",
            "revision": "7ae557604adf67be50417f59c2c2f167def9a775",
        },
        "record_count": len(selected),
        "records": selected,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), "records": len(selected), "categories": counts}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
