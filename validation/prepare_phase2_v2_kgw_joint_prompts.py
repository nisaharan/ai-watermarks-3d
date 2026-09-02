#!/usr/bin/env python3
"""Freeze three fresh, mutually disjoint UltraChat manifests for KGW feasibility."""

from __future__ import annotations

import argparse
import hashlib
import heapq
import json
from pathlib import Path
from typing import Any

from ai_watermarks_phase2.kgw_joint_protocol import CONFIG_PATH, PROTOCOL_ID, validate_protocol
from ai_watermarks_phase2.native import require_ml_dependencies
from ai_watermarks_phase2.smoke import load_json
from ai_watermarks_phase2.variance_pilot import file_sha256, write_result
from audit_phase2_ultrachat_source import exclusion_keys, normalized


ROLE_ORDER = ("development_null", "stage_a", "stage_b")


def selection_rank(seed: str, prompt_id: str, prompt_sha256: str) -> str:
    material = f"{seed}\0kgw-joint-feasibility\0{prompt_id}\0{prompt_sha256}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    parser.add_argument("--tokenizer-batch-size", type=int, default=512)
    args = parser.parse_args(argv)

    config = load_json(args.config)
    validate_protocol(config)
    output_paths = {
        role: Path(config["prompt_manifests"][role]) for role in ROLE_ORDER
    }
    existing = [path for path in output_paths.values() if path.exists()]
    if existing:
        raise FileExistsError(f"Refusing to replace frozen manifests: {existing}")

    source = load_json(Path(config["source_config"]))
    if source.get("status") != "draft_not_authorized_for_generation":
        raise ValueError("UltraChat source config must remain the non-executable v2 draft")
    selection = config["prompt_selection"]
    counts = {role: int(selection["roles"][role]) for role in ROLE_ORDER}
    total = sum(counts.values())
    exclusion_paths = [Path(path) for path in selection["exclude_manifests"]]
    excluded_hashes, excluded_prompts = exclusion_keys(exclusion_paths)

    _, transformers = require_ml_dependencies()
    tokenizer = transformers.AutoTokenizer.from_pretrained(
        config["model"]["id"], revision=config["model"]["revision"]
    )
    max_tokens = int(selection["max_prompt_tokens"])
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
            if int(length) > max_tokens:
                continue
            rank = selection_rank(
                selection["seed"], row["source_prompt_id"], row["prompt_sha256"]
            )
            candidate = {**row, "prompt_tokens": int(length), "selection_rank": rank}
            entry = (-int(rank, 16), candidate)
            if len(heap) < total:
                heapq.heappush(heap, entry)
            elif int(rank, 16) < -heap[0][0]:
                heapq.heapreplace(heap, entry)

    source_rows = 0
    for source_index, item in enumerate(source["source"]["files"]):
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
                prompt_id, prompt = str(row["prompt_id"]), str(row["prompt"])
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
                if len(pending) >= args.tokenizer_batch_size:
                    consider_batch(pending)
                    pending.clear()
        if shard_rows != int(item["rows"]):
            raise ValueError(f"Source row count mismatch: {extract_path}")
    consider_batch(pending)
    expected_source_rows = sum(int(item["rows"]) for item in source["source"]["files"])
    if source_rows != expected_source_rows:
        raise ValueError("Total source row count mismatch")
    if len(heap) != total:
        raise ValueError(f"Only {len(heap)} eligible prompts; need {total}")

    selected = [entry[1] for entry in heap]
    selected.sort(key=lambda row: (row["selection_rank"], row["source_prompt_id"]))
    cursor = 0
    generator_hash = file_sha256(Path(__file__))
    exclusion_hashes = {str(path): file_sha256(path) for path in exclusion_paths}
    summaries = []
    for role in ROLE_ORDER:
        records = selected[cursor : cursor + counts[role]]
        cursor += counts[role]
        for index, row in enumerate(records):
            row["id"] = f"kgw-joint-{role.replace('_', '-')}-{index:04d}"
        manifest = {
            "schema_version": 1,
            "status": f"kgw_joint_{role}_prompt_manifest_frozen",
            "protocol_id": PROTOCOL_ID,
            "split_role": role,
            "scope": "Fresh development-only UltraChat prompts; never v2 calibration or confirmation data",
            "source": source["source"],
            "model_tokenizer": config["model"],
            "selection": {
                **selection,
                "role": role,
                "role_count": counts[role],
                "global_rank_slice_start": cursor - counts[role],
                "global_rank_slice_stop": cursor,
                "method": "consecutive slices of the lowest global SHA-256 ranks after frozen exclusions, normalized deduplication, and tokenizer-length filtering",
                "exclusion_manifest_sha256": exclusion_hashes,
                "generator_sha256": generator_hash,
            },
            "records": records,
        }
        write_result(output_paths[role], manifest)
        summaries.append(
            {
                "role": role,
                "records": len(records),
                "output": str(output_paths[role]),
                "sha256": file_sha256(output_paths[role]),
            }
        )
    print(json.dumps({"status": "kgw_joint_prompt_manifests_frozen", "manifests": summaries}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
