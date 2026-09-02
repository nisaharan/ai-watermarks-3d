#!/usr/bin/env python3
"""Prepare blinded candidate/control response pairs for KGW task-quality review."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from ai_watermarks_phase2.kgw_joint_protocol import CONFIG_PATH, validate_protocol
from ai_watermarks_phase2.kgw_joint_stage import RESULT_ROOT, iter_records
from ai_watermarks_phase2.smoke import load_json
from ai_watermarks_phase2.variance_pilot import file_sha256, write_result


def pair_rank(
    protocol_id: str,
    stage: str,
    gamma: float,
    delta: float,
    key_id: str,
    prompt_sha256: str,
) -> str:
    material = (
        f"{protocol_id}\0{stage}\0{gamma}\0{delta}\0{key_id}\0{prompt_sha256}"
    )
    return hashlib.sha256(material.encode()).hexdigest()


def candidate_pairs(
    config: dict[str, Any],
    stage: str,
    run_dir: Path,
    gamma: float,
    delta: float,
) -> list[tuple[dict[str, Any], dict[str, Any], str]]:
    controls = {}
    candidates = {}
    for row in iter_records(run_dir):
        key = (row["key_id"], row["prompt_id"])
        if row["condition"] == "unwatermarked_control":
            controls[key] = row
        elif float(row["gamma"]) == gamma and float(row["delta"]) == delta:
            candidates[key] = row
    if set(controls) != set(candidates):
        raise ValueError("Candidate/control key-prompt pairs are incomplete")
    ranked = [
        (
            candidates[key],
            controls[key],
            pair_rank(
                config["protocol_id"],
                stage,
                gamma,
                delta,
                str(key[0]),
                str(candidates[key]["prompt_sha256"]),
            ),
        )
        for key in controls
    ]
    ranked.sort(key=lambda item: item[2])
    return ranked


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    parser.add_argument("--stage", choices=("stage_a", "stage_b"), required=True)
    parser.add_argument("--analysis", type=Path)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--packet-output", type=Path)
    parser.add_argument("--answer-key-output", type=Path)
    args = parser.parse_args(argv)
    config = load_json(args.config)
    validate_protocol(config)
    stage_label = args.stage.replace("_", "-")
    analysis_path = args.analysis or RESULT_ROOT / f"{stage_label}-analysis.json"
    run_dir = args.run_dir or RESULT_ROOT / stage_label / "run"
    packet_output = args.packet_output or RESULT_ROOT / f"{stage_label}-blinded-review-packet.json"
    answer_output = args.answer_key_output or RESULT_ROOT / f"{stage_label}-blinded-review-answer-key.json"
    if packet_output.exists() or answer_output.exists():
        raise FileExistsError("Refusing to replace frozen blinded-review materials")
    analysis = load_json(analysis_path)
    if analysis.get("protocol_id") != config["protocol_id"]:
        raise ValueError("Analysis and protocol differ")
    if args.stage == "stage_a":
        candidates = [
            (float(row["gamma"]), float(row["delta"]))
            for row in analysis["candidate_decisions"]
            if row["automated_passed"]
        ]
    else:
        decision = analysis["candidate_decision"]
        candidates = (
            [(float(decision["gamma"]), float(decision["delta"]))]
            if decision["automated_passed"]
            else []
        )
    if not candidates:
        raise ValueError("No automatically eligible candidate requires blinded review")
    prompts = {
        row["id"]: row["prompt"]
        for row in load_json(Path(config["prompt_manifests"][args.stage]))["records"]
    }
    sample_pairs = int(config["blinded_task_quality_guardrail"]["sample_pairs_per_candidate"])
    packet_pairs = []
    answer_pairs = []
    for gamma, delta in candidates:
        ranked = candidate_pairs(config, args.stage, run_dir, gamma, delta)
        if len(ranked) < sample_pairs:
            raise ValueError("Not enough paired outputs for blinded review")
        for pair_index, (candidate, control, rank) in enumerate(ranked[:sample_pairs]):
            pair_id = hashlib.sha256(
                f"{config['protocol_id']}\0{args.stage}\0{gamma}\0{delta}\0{rank}".encode()
            ).hexdigest()[:20]
            candidate_is_a = int(rank[-1], 16) % 2 == 0
            response_a = candidate["text"] if candidate_is_a else control["text"]
            response_b = control["text"] if candidate_is_a else candidate["text"]
            packet_pairs.append(
                {
                    "pair_id": pair_id,
                    "candidate_group": f"candidate-{candidates.index((gamma, delta)) + 1:02d}",
                    "pair_index": pair_index,
                    "prompt": prompts[candidate["prompt_id"]],
                    "response_a": response_a,
                    "response_b": response_b,
                    "rating_options": {
                        "preferred_response": ["A", "B", "tie"],
                        "unusable_response": ["none", "A", "B", "both"],
                    },
                }
            )
            answer_pairs.append(
                {
                    "pair_id": pair_id,
                    "candidate_group": packet_pairs[-1]["candidate_group"],
                    "gamma": gamma,
                    "delta": delta,
                    "candidate_label": "A" if candidate_is_a else "B",
                    "control_label": "B" if candidate_is_a else "A",
                    "selection_rank": rank,
                    "key_id": candidate["key_id"],
                    "prompt_id": candidate["prompt_id"],
                }
            )
    packet = {
        "schema_version": 1,
        "status": "kgw_joint_blinded_review_packet_frozen",
        "protocol_id": config["protocol_id"],
        "stage": args.stage,
        "instructions": "Two raters independently review every pair. Copy pair_id and record preferred_response plus unusable_response. Do not inspect the separate answer key.",
        "pairs": packet_pairs,
    }
    write_result(packet_output, packet)
    answer = {
        "schema_version": 1,
        "status": "kgw_joint_blinded_review_answer_key_frozen",
        "protocol_id": config["protocol_id"],
        "stage": args.stage,
        "packet_sha256": file_sha256(packet_output),
        "pairs": answer_pairs,
    }
    write_result(answer_output, answer)
    print(
        json.dumps(
            {
                "status": packet["status"],
                "stage": args.stage,
                "candidates": len(candidates),
                "pairs": len(packet_pairs),
                "packet": str(packet_output),
                "packet_sha256": file_sha256(packet_output),
                "answer_key": str(answer_output),
                "answer_key_sha256": file_sha256(answer_output),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
