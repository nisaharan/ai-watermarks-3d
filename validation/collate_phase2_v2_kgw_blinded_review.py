#!/usr/bin/env python3
"""Collate two frozen blinded-rating files into the KGW review decision artifact."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from ai_watermarks_phase2.kgw_joint_protocol import CONFIG_PATH, validate_protocol
from ai_watermarks_phase2.smoke import load_json
from ai_watermarks_phase2.variance_pilot import file_sha256, write_result


def rating_lookup(path: Path, expected_pairs: set[str]) -> dict[str, dict]:
    artifact = load_json(path)
    if artifact.get("status") != "kgw_joint_blinded_ratings_complete":
        raise ValueError(f"Rating file is incomplete: {path}")
    rows = artifact.get("ratings")
    if not isinstance(rows, list):
        raise ValueError(f"Rating rows are missing: {path}")
    lookup = {str(row["pair_id"]): row for row in rows}
    if set(lookup) != expected_pairs or len(lookup) != len(rows):
        raise ValueError(f"Rating pair IDs differ from the packet: {path}")
    for row in rows:
        if row.get("preferred_response") not in {"A", "B", "tie"}:
            raise ValueError(f"Invalid preference: {path}/{row['pair_id']}")
        if row.get("unusable_response") not in {"none", "A", "B", "both"}:
            raise ValueError(f"Invalid unusable response: {path}/{row['pair_id']}")
    return lookup


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--answer-key", type=Path, required=True)
    parser.add_argument("--rater-one", type=Path, required=True)
    parser.add_argument("--rater-two", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output.exists():
        raise FileExistsError(f"Refusing to replace blinded-review result: {args.output}")
    config = load_json(args.config)
    validate_protocol(config)
    packet, answer = load_json(args.packet), load_json(args.answer_key)
    if packet.get("protocol_id") != config["protocol_id"] or answer.get("protocol_id") != config["protocol_id"]:
        raise ValueError("Blinded-review materials and protocol differ")
    if answer.get("packet_sha256") != file_sha256(args.packet):
        raise ValueError("Answer key does not match the frozen packet")
    stage = packet.get("stage")
    if stage != answer.get("stage") or stage not in {"stage_a", "stage_b"}:
        raise ValueError("Blinded-review stage differs")
    answer_lookup = {str(row["pair_id"]): row for row in answer["pairs"]}
    expected = set(answer_lookup)
    if expected != {str(row["pair_id"]) for row in packet["pairs"]}:
        raise ValueError("Packet and answer-key pair IDs differ")
    rater_one = rating_lookup(args.rater_one, expected)
    rater_two = rating_lookup(args.rater_two, expected)
    summaries = defaultdict(lambda: {"pairs": 0, "candidate_unusable_pairs": 0, "candidate_worse_pairs": 0})
    for pair_id, key in answer_lookup.items():
        rows = (rater_one[pair_id], rater_two[pair_id])
        candidate_label, control_label = key["candidate_label"], key["control_label"]
        candidate_unusable = any(
            row["unusable_response"] in {candidate_label, "both"} for row in rows
        )
        candidate_worse = (
            not candidate_unusable
            and all(row["preferred_response"] == control_label for row in rows)
        )
        group = summaries[(float(key["gamma"]), float(key["delta"]))]
        group["pairs"] += 1
        group["candidate_unusable_pairs"] += int(candidate_unusable)
        group["candidate_worse_pairs"] += int(candidate_worse)
    reviews = [
        {"gamma": gamma, "delta": delta, **values}
        for (gamma, delta), values in sorted(summaries.items())
    ]
    result = {
        "schema_version": 1,
        "status": "kgw_joint_blinded_review_complete",
        "protocol_id": config["protocol_id"],
        "stage": stage,
        "input_sha256": {
            "packet": file_sha256(args.packet),
            "answer_key": file_sha256(args.answer_key),
            "rater_one": file_sha256(args.rater_one),
            "rater_two": file_sha256(args.rater_two),
            "collator_source": file_sha256(Path(__file__)),
        },
        "rater_ids": [
            load_json(args.rater_one).get("rater_id"),
            load_json(args.rater_two).get("rater_id"),
        ],
        "candidate_reviews": reviews,
    }
    if any(not value for value in result["rater_ids"]) or len(set(result["rater_ids"])) != 2:
        raise ValueError("Two distinct non-empty frozen rater IDs are required")
    write_result(args.output, result)
    print(json.dumps({"status": result["status"], "stage": stage, "candidate_reviews": reviews, "output": str(args.output)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
