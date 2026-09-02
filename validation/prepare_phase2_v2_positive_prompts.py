#!/usr/bin/env python3
"""Freeze fresh UltraChat prompts for the v2 positive-sensitivity screen."""

from __future__ import annotations

import argparse
import hashlib
import heapq
import json
from pathlib import Path
from typing import Any

from ai_watermarks_phase2.native import require_ml_dependencies
from ai_watermarks_phase2.smoke import load_json
from audit_phase2_ultrachat_source import (
    exclusion_keys,
    file_sha256,
    normalized,
)


def selection_rank(seed: str, prompt_id: str, prompt_sha256: str) -> str:
    material = f"{seed}\0positive-sensitivity\0{prompt_id}\0{prompt_sha256}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


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
        default=Path("data/phase2-v2-positive-sensitivity-prompts.json"),
    )
    parser.add_argument("--prompts", type=int, default=50)
    parser.add_argument("--batch-size", type=int, default=512)
    args = parser.parse_args(argv)
    if args.output.exists():
        raise FileExistsError(f"Refusing to replace frozen manifest: {args.output}")
    if args.prompts < 1:
        parser.error("--prompts must be positive")

    config = load_json(args.config)
    if config.get("status") != "draft_not_authorized_for_generation":
        raise ValueError("Prompt preparation requires the non-executable v2 draft")
    exclusion_paths = [Path(path) for path in config["selection"]["exclusion_manifests"]]
    excluded_hashes, excluded_prompts = exclusion_keys(exclusion_paths)
    _, transformers = require_ml_dependencies()
    tokenizer = transformers.AutoTokenizer.from_pretrained(
        config["model"]["id"], revision=config["model"]["revision"]
    )
    max_tokens = int(config["selection"]["max_prompt_tokens"])
    seed = "phase2-v2-positive-sensitivity-v1"
    seen_ids: set[str] = set()
    seen_prompts: set[str] = set()
    heap: list[tuple[int, dict[str, Any]]] = []
    pending: list[dict[str, Any]] = []

    def consider_batch(rows: list[dict[str, Any]]) -> None:
        if not rows:
            return
        lengths = tokenizer(
            [row["prompt"] for row in rows],
            add_special_tokens=True,
            truncation=True,
            max_length=max_tokens + 1,
            return_length=True,
        )["length"]
        for row, length in zip(rows, lengths, strict=True):
            prompt_tokens = int(length)
            if prompt_tokens > max_tokens:
                continue
            rank = selection_rank(seed, row["source_prompt_id"], row["prompt_sha256"])
            candidate = {**row, "prompt_tokens": prompt_tokens, "selection_rank": rank}
            rank_int = int(rank, 16)
            entry = (-rank_int, candidate)
            if len(heap) < args.prompts:
                heapq.heappush(heap, entry)
            elif rank_int < -heap[0][0]:
                heapq.heapreplace(heap, entry)

    source_rows = 0
    for source_index, item in enumerate(config["source"]["files"]):
        source_path = Path(item["path"])
        extract_path = Path(item["prompt_extract"])
        if file_sha256(source_path) != item["sha256"]:
            raise ValueError(f"Source hash mismatch: {source_path}")
        if file_sha256(extract_path) != item["prompt_extract_sha256"]:
            raise ValueError(f"Extract hash mismatch: {extract_path}")
        shard_rows = 0
        with extract_path.open(encoding="utf-8") as handle:
            for expected_row, line in enumerate(handle):
                row = json.loads(line)
                shard_rows += 1
                source_rows += 1
                if int(row["shard_row"]) != expected_row:
                    raise ValueError(f"Non-contiguous source rows: {extract_path}")
                prompt_id = str(row["prompt_id"])
                prompt = str(row["prompt"])
                prompt_norm = normalized(prompt)
                prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
                if prompt_id in seen_ids:
                    continue
                seen_ids.add(prompt_id)
                if not prompt_norm or prompt_norm in seen_prompts:
                    continue
                seen_prompts.add(prompt_norm)
                if prompt_hash in excluded_hashes or prompt_norm in excluded_prompts:
                    continue
                pending.append(
                    {
                        "source_shard": source_index,
                        "source_row": expected_row,
                        "source_prompt_id": prompt_id,
                        "prompt": prompt,
                        "prompt_sha256": prompt_hash,
                    }
                )
                if len(pending) >= args.batch_size:
                    consider_batch(pending)
                    pending.clear()
        if shard_rows != int(item["rows"]):
            raise ValueError(f"Source row count mismatch: {extract_path}")
    consider_batch(pending)
    if source_rows != sum(int(item["rows"]) for item in config["source"]["files"]):
        raise ValueError("Total source row count mismatch")
    if len(heap) != args.prompts:
        raise ValueError(f"Only {len(heap)} eligible prompts; need {args.prompts}")

    records = [entry[1] for entry in heap]
    records.sort(key=lambda row: (row["selection_rank"], row["source_prompt_id"]))
    for index, row in enumerate(records):
        row["id"] = f"positive-sensitivity-{index:03d}"
    if len({row["prompt_sha256"] for row in records}) != args.prompts:
        raise RuntimeError("Selected prompt hashes are not unique")

    manifest = {
        "schema_version": 1,
        "status": "positive_sensitivity_prompt_manifest_frozen",
        "pilot_id": "phase2-v2-positive-sensitivity-v1",
        "scope": "Fresh development-only UltraChat prompts; not calibration or confirmation data",
        "source": config["source"],
        "model_tokenizer": config["model"],
        "selection": {
            "seed": seed,
            "method": "lowest SHA-256 ranks after frozen exclusions, normalized deduplication, and tokenizer-length filtering",
            "prompt_count": args.prompts,
            "max_prompt_tokens": max_tokens,
            "exclusion_manifest_sha256": {
                str(path): file_sha256(path) for path in exclusion_paths
            },
            "generator_sha256": file_sha256(Path(__file__)),
        },
        "records": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": manifest["status"],
                "records": len(records),
                "output": str(args.output),
                "sha256": file_sha256(args.output),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
