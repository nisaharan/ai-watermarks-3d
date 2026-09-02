#!/usr/bin/env python3
"""Evaluate the one-candidate independent Stage-B KGW feasibility validation."""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

from ai_watermarks_phase2.kgw_joint_protocol import CONFIG_PATH, validate_protocol
from ai_watermarks_phase2.kgw_joint_stage import RESULT_ROOT, iter_records, run_digest
from ai_watermarks_phase2.native import TransformersNativeRunner
from ai_watermarks_phase2.smoke import load_json
from ai_watermarks_phase2.variance_pilot import file_sha256, write_result
from validation.analyse_phase2_v2_kgw_bias_development import conditional_nll_batch
from validation.analyse_phase2_v2_kgw_joint_stage_a import (
    build_cells,
    noops_by_candidate,
)


def evaluate_stage_b(
    config: dict,
    cells: list[dict],
    selection: dict,
    review: dict | None,
) -> tuple[str, dict]:
    selected = selection.get("selected_candidate")
    if selection.get("status") != "kgw_joint_stage_a_candidate_selected" or not isinstance(selected, dict):
        raise ValueError("Stage B requires one frozen Stage-A selection")
    gamma, delta = float(selected["gamma"]), float(selected["delta"])
    rows = [
        row for row in cells if row["gamma"] == gamma and row["delta"] == delta
    ]
    expected_cells = len(config["generation"]["stage_b"]["target_key_indices"]) * len(
        config["generation"]["stage_b"]["paired_prefix_lengths"]
    )
    if len(rows) != expected_cells:
        raise ValueError("Stage-B candidate does not contain all 30 key-length cells")
    automated_passed = all(row["automated_cell_passed"] for row in rows)
    decision = {
        "gamma": gamma,
        "delta": delta,
        "targeted_cells": len(rows),
        "failed_detection_cells": sum(not row["detection_passed"] for row in rows),
        "failed_automated_quality_cells": sum(
            not row["automated_quality_passed"] for row in rows
        ),
        "automated_passed": automated_passed,
    }
    if not automated_passed:
        decision["blinded_review_passed"] = None
        return "kgw_joint_stage_b_failed", decision
    if review is None:
        decision["blinded_review_passed"] = None
        return "kgw_joint_stage_b_awaiting_blinded_review", decision
    if review.get("status") != "kgw_joint_blinded_review_complete" or review.get("stage") != "stage_b":
        raise ValueError("Blinded review artifact has the wrong status or stage")
    if review.get("protocol_id") != config["protocol_id"]:
        raise ValueError("Blinded review and protocol differ")
    candidates = review.get("candidate_reviews", [])
    if len(candidates) != 1:
        raise ValueError("Stage-B review must contain exactly one candidate")
    reviewed = candidates[0]
    if (float(reviewed["gamma"]), float(reviewed["delta"])) != (gamma, delta):
        raise ValueError("Stage-B review candidate differs from the selection")
    guard = config["blinded_task_quality_guardrail"]
    if int(reviewed["pairs"]) != int(guard["sample_pairs_per_candidate"]):
        raise ValueError("Stage-B review pair count differs")
    review_passed = (
        int(reviewed["candidate_unusable_pairs"])
        <= int(guard["candidate_unusable_pairs_allowed"])
        and int(reviewed["candidate_worse_pairs"])
        <= int(guard["candidate_worse_pairs_allowed"])
    )
    decision["blinded_review"] = reviewed
    decision["blinded_review_passed"] = review_passed
    return (
        "kgw_joint_stage_b_passed" if review_passed else "kgw_joint_stage_b_failed",
        decision,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    parser.add_argument("--run-dir", type=Path, default=RESULT_ROOT / "stage-b" / "run")
    parser.add_argument("--selection", type=Path)
    parser.add_argument("--blinded-review", type=Path)
    parser.add_argument("--output", type=Path, default=RESULT_ROOT / "stage-b-analysis.json")
    args = parser.parse_args(argv)
    if args.output.exists():
        raise FileExistsError(f"Refusing to replace Stage-B analysis: {args.output}")
    config = load_json(args.config)
    validate_protocol(config)
    selection_path = args.selection or Path(
        config["stage_a_selection_rule"]["selection_artifact"]
    )
    selection = load_json(selection_path)
    metadata = load_json(args.run_dir / "run.json")
    if metadata.get("status") != "kgw_joint_stage_b_complete":
        raise ValueError("Stage-B run is not complete")
    if metadata.get("protocol_id") != config["protocol_id"]:
        raise ValueError("Stage-B run and protocol differ")
    if metadata.get("confirmation_scores_used") is not False:
        raise ValueError("Stage B does not preserve confirmation separation")

    records = list(iter_records(args.run_dir))
    prompt_manifest = load_json(Path(config["prompt_manifests"]["stage_b"]))
    prompts = {row["id"]: row["prompt"] for row in prompt_manifest["records"]}
    lengths = [int(value) for value in config["generation"]["stage_b"]["paired_prefix_lengths"]]
    runner = TransformersNativeRunner(
        model_id=config["model"]["id"],
        revision=config["model"]["revision"],
        device=config["model"]["device"],
    )
    quality = {}
    batch_size = int(config["generation"]["batch_size"])
    for start in range(0, len(records), batch_size):
        block = records[start : start + batch_size]
        nlls = conditional_nll_batch(
            runner,
            [prompts[row["prompt_id"]] for row in block],
            [[int(value) for value in row["token_ids"]] for row in block],
            lengths,
        )
        for row, values in zip(block, nlls, strict=True):
            if not all(math.isfinite(value) for value in values.values()):
                raise RuntimeError("Non-finite conditional NLL")
            quality[
                (
                    row["prompt_id"],
                    row["key_id"],
                    None if row["gamma"] is None else float(row["gamma"]),
                    None if row["delta"] is None else float(row["delta"]),
                )
            ] = values
        print(
            f"quality checkpoint outputs {min(start + batch_size, len(records))}/{len(records)}",
            flush=True,
        )
    cells = build_cells(
        config,
        records,
        quality,
        noops_by_candidate(args.run_dir),
        stage="stage_b",
    )
    review = load_json(args.blinded_review) if args.blinded_review else None
    status, decision = evaluate_stage_b(config, cells, selection, review)
    result = {
        "schema_version": 1,
        "status": status,
        "protocol_id": config["protocol_id"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_sha256": {
            "protocol_config": file_sha256(args.config),
            "development_thresholds": file_sha256(
                Path(config["development_null_thresholds"]["artifact"])
            ),
            "stage_a_selection": file_sha256(selection_path),
            "stage_b_run_digest": run_digest(args.run_dir),
            "analysis_source": file_sha256(Path(__file__)),
            **(
                {"blinded_review": file_sha256(args.blinded_review)}
                if args.blinded_review
                else {}
            ),
        },
        "cells": cells,
        "candidate_decision": decision,
        "interpretation": {
            "confirmatory_claim": False,
            "attacks_authorized": False,
            "replacement_null_generation_authorized": False,
            "next_step": (
                config["stop_rules"]["stage_b_pass"]
                if status == "kgw_joint_stage_b_passed"
                else config["stop_rules"]["stage_b_failure"]
            ),
        },
    }
    write_result(args.output, result)
    print(json.dumps({"status": status, "candidate_decision": decision, "output": str(args.output)}, indent=2))
    if status == "kgw_joint_stage_b_passed":
        return 0
    if status == "kgw_joint_stage_b_awaiting_blinded_review":
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
