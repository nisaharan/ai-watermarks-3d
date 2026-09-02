#!/usr/bin/env python3
"""Freeze the prospective closure of the partial KGW joint-feasibility study."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULT_ROOT = ROOT / "results/phase2-v2-kgw-joint-feasibility"
OUTPUT = RESULT_ROOT / "study-closure.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def contiguous_batches(directory: Path) -> list[Path]:
    paths = sorted(directory.glob("batch-*.json"))
    expected = [f"batch-{index:06d}.json" for index in range(len(paths))]
    if [path.name for path in paths] != expected:
        raise RuntimeError(f"Non-contiguous batch sequence in {directory}")
    return paths


def checkpoint_span_hours(paths: list[Path]) -> float:
    if len(paths) < 2:
        return 0.0
    return (paths[-1].stat().st_mtime - paths[0].stat().st_mtime) / 3600.0


def build_closure() -> dict:
    config_path = ROOT / "configs/phase2-v2-kgw-joint-feasibility.json"
    freeze_path = RESULT_ROOT / "protocol-freeze.json"
    authorization_path = ROOT / "configs/phase2-v2-kgw-joint-feasibility-authorization.json"
    thresholds_path = RESULT_ROOT / "development-thresholds.json"
    null_run_path = RESULT_ROOT / "development-null/run.json"
    config = load(config_path)
    null_run = load(null_run_path)
    if null_run.get("status") != "kgw_joint_development_null_complete":
        raise RuntimeError("Development null is not complete")
    stage_a_run_path = RESULT_ROOT / "stage-a/run/run.json"
    if stage_a_run_path.exists() and load(stage_a_run_path).get("status") == "kgw_joint_stage_a_complete":
        raise RuntimeError("Stage A is complete; prospective partial-run closure is inapplicable")

    batch_size = int(config["generation"]["batch_size"])
    null_batches = contiguous_batches(RESULT_ROOT / "development-null/batches")
    stage_a_batches = contiguous_batches(RESULT_ROOT / "stage-a/run/batches")
    if len(null_batches) != 1000:
        raise RuntimeError("Expected exactly 1,000 completed development-null batches")
    if not stage_a_batches:
        raise RuntimeError("Expected a partial Stage A run")

    null_span = checkpoint_span_hours(null_batches)
    stage_a_span = checkpoint_span_hours(stage_a_batches)
    stage_a_outputs = len(stage_a_batches) * batch_size
    target_outputs = int(config["generation"]["stage_a"]["total_outputs"])
    observed_output_interval = max(stage_a_outputs - batch_size, batch_size)
    projected_stage_a_hours = stage_a_span * target_outputs / observed_output_interval
    planned_stage_b_hours = float(config["compute_budget"]["stage_b_generation_and_analysis_hours_if_reached"])
    cap_hours = float(config["compute_budget"]["cpu_wall_clock_cap_hours"])

    return {
        "schema_version": 1,
        "status": "kgw_joint_feasibility_closed_by_prospective_rescope",
        "protocol_id": config["protocol_id"],
        "closed_at": datetime.now(timezone.utc).isoformat(),
        "decision": {
            "action": "close_and_prospectively_rescope_128_token_canonical_kgw_claim",
            "reason": (
                "The user selected the publication-focused re-scope with no more than one "
                "additional day available; completing Stage A, possible blinded review, and "
                "conditional Stage B would not provide a bounded path to a finished paper."
            ),
            "decision_made_without_partial_score_analysis": True,
            "resume_stage_a_authorized": False,
            "stage_b_authorized": False,
            "further_parameter_tuning_authorized": False,
            "attacks_authorized": False,
        },
        "partial_stage_a_disposition": {
            "batch_files": len(stage_a_batches),
            "durable_outputs": stage_a_outputs,
            "target_outputs": target_outputs,
            "batches_contiguous": True,
            "first_batch": stage_a_batches[0].name,
            "last_batch": stage_a_batches[-1].name,
            "outcome_evaluated": False,
            "scores_used_for_selection_or_retuning": False,
            "files_preserved_for_audit": True,
        },
        "compute_record": {
            "measurement": "filesystem checkpoint span; excludes setup and shutdown overhead",
            "development_null_checkpoint_span_hours": round(null_span, 4),
            "stage_a_checkpoint_span_hours_at_closure": round(stage_a_span, 4),
            "stage_a_projected_total_hours_at_observed_rate": round(projected_stage_a_hours, 4),
            "stage_b_planning_hours_if_reached": planned_stage_b_hours,
            "projected_total_through_stage_b_hours": round(
                null_span + projected_stage_a_hours + planned_stage_b_hours, 4
            ),
            "authorization_cap_hours": cap_hours,
        },
        "publication_boundary": {
            "stage_a_supports_no_result_claim": True,
            "joint_gamma_delta_grid_may_not_be_described_as_failed": True,
            "completed_prior_results_remain_reportable": True,
            "next_priority": "publication_pivot_and_reproducibility_package",
        },
        "input_sha256": {
            "protocol_config": file_sha256(config_path),
            "protocol_freeze": file_sha256(freeze_path),
            "authorization": file_sha256(authorization_path),
            "development_thresholds": file_sha256(thresholds_path),
            "development_null_run": file_sha256(null_run_path),
        },
    }


def verify(saved: dict) -> None:
    current = build_closure()
    for key in (
        "schema_version",
        "status",
        "protocol_id",
        "decision",
        "partial_stage_a_disposition",
        "publication_boundary",
        "input_sha256",
    ):
        if saved.get(key) != current.get(key):
            raise RuntimeError(f"Closure verification failed for {key}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        if not OUTPUT.exists():
            raise RuntimeError(f"Missing closure artifact: {OUTPUT}")
        verify(load(OUTPUT))
        print(json.dumps({"status": "closure_verified", "output": str(OUTPUT.relative_to(ROOT))}, indent=2))
        return 0
    if OUTPUT.exists():
        raise RuntimeError(f"Refusing to overwrite immutable closure artifact: {OUTPUT}")
    closure = build_closure()
    OUTPUT.write_text(json.dumps(closure, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": closure["status"], "output": str(OUTPUT.relative_to(ROOT))}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
