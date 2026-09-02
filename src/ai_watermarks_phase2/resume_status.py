"""Report the durable Phase 2 checkpoint and the next authorized action."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .smoke import load_json


ROOT = Path(".")
PROTOCOL = ROOT / "configs/phase2-confirmatory-null.json"
RESULTS = ROOT / "results/phase2-confirmatory-null"
KGW_BIAS_ANALYSIS = ROOT / "results/phase2-v2-kgw-bias-development-v3/analysis.json"
KGW_FEASIBILITY_DECISION = (
    ROOT
    / "docs/research-transformation/phase-2/kgw-feasibility-design-decision.md"
)
KGW_JOINT_CONFIG = ROOT / "configs/phase2-v2-kgw-joint-feasibility.json"
KGW_JOINT_FREEZE = ROOT / "results/phase2-v2-kgw-joint-feasibility/protocol-freeze.json"
KGW_JOINT_AUTHORIZATION = (
    ROOT / "configs/phase2-v2-kgw-joint-feasibility-authorization.json"
)
KGW_JOINT_RESULTS = ROOT / "results/phase2-v2-kgw-joint-feasibility"
KGW_JOINT_CLOSURE = KGW_JOINT_RESULTS / "study-closure.json"


def kgw_joint_next_action() -> dict[str, str]:
    if not KGW_JOINT_CONFIG.exists() or not KGW_JOINT_FREEZE.exists():
        return {
            "id": "preregister_kgw_joint_parameter_study",
            "reason": (
                "The final bounded canonical-SelfHash study has been selected, but "
                "its executable inputs and implementation are not yet fingerprint-frozen."
            ),
            "command": (
                ".venv/bin/python validation/freeze_phase2_v2_kgw_joint_protocol.py; "
                "do not start generation"
            ),
        }
    if not KGW_JOINT_AUTHORIZATION.exists():
        return {
            "id": "approve_kgw_joint_compute_budget",
            "reason": (
                "The protocol, implementation and fresh manifests are frozen. "
                "Generation is locked pending explicit approval of the 24 CPU-hour "
                "and 0.5 GB caps."
            ),
            "command": (
                "Review the frozen KGW joint protocol and explicitly approve its "
                "bounded compute budget; do not generate before approval."
            ),
        }
    null_run = KGW_JOINT_RESULTS / "development-null" / "run.json"
    thresholds = KGW_JOINT_RESULTS / "development-thresholds.json"
    stage_a_run = KGW_JOINT_RESULTS / "stage-a" / "run" / "run.json"
    stage_a_analysis = KGW_JOINT_RESULTS / "stage-a-analysis.json"
    selection = KGW_JOINT_RESULTS / "stage-a-selection.json"
    stage_b_run = KGW_JOINT_RESULTS / "stage-b" / "run" / "run.json"
    stage_b_analysis = KGW_JOINT_RESULTS / "stage-b-analysis.json"
    authorization_arg = (
        "--authorization configs/phase2-v2-kgw-joint-feasibility-authorization.json"
    )
    if KGW_JOINT_CLOSURE.exists():
        closure = load_json(KGW_JOINT_CLOSURE)
        if closure.get("status") != "kgw_joint_feasibility_closed_by_prospective_rescope":
            raise ValueError("Unrecognized KGW joint-feasibility closure status")
        decision = closure.get("decision", {})
        if decision.get("resume_stage_a_authorized") is not False:
            raise ValueError("Closed KGW study must explicitly prohibit Stage A resume")
        if closure.get("partial_stage_a_disposition", {}).get("outcome_evaluated") is not False:
            raise ValueError("Partial Stage A closure must not claim an evaluated outcome")
        return {
            "id": "prepare_phase2_calibration_publication",
            "reason": (
                "The partial joint-KGW study was prospectively closed without score "
                "analysis, and the 128-token claim was re-scoped."
            ),
            "command": (
                "Prepare the calibration, confirmation-gate, feasibility, and "
                "reproducibility evidence for publication; do not resume Stage A."
            ),
        }
    if not null_run.exists() or load_json(null_run).get("status") != "kgw_joint_development_null_complete":
        return {
            "id": "start_or_resume_kgw_joint_development_null",
            "reason": "Compute is approved, but the fresh development null is incomplete.",
            "command": f".venv/bin/python -m ai_watermarks_phase2.kgw_joint_null {authorization_arg}",
        }
    if not thresholds.exists():
        return {
            "id": "fit_kgw_joint_development_thresholds",
            "reason": "The fresh development null is complete; thresholds have not been frozen.",
            "command": ".venv/bin/python validation/fit_phase2_v2_kgw_joint_thresholds.py",
        }
    if not stage_a_run.exists() or load_json(stage_a_run).get("status") != "kgw_joint_stage_a_complete":
        return {
            "id": "start_or_resume_kgw_joint_stage_a",
            "reason": "Development thresholds are frozen, but the factorial Stage A screen is incomplete.",
            "command": f".venv/bin/python -m ai_watermarks_phase2.kgw_joint_stage --stage stage_a {authorization_arg}",
        }
    if not stage_a_analysis.exists():
        return {
            "id": "analyse_kgw_joint_stage_a",
            "reason": "Stage A generation is complete and has not been evaluated.",
            "command": ".venv/bin/python validation/analyse_phase2_v2_kgw_joint_stage_a.py",
        }
    stage_a_status = load_json(stage_a_analysis).get("status")
    if stage_a_status == "kgw_joint_stage_a_awaiting_blinded_review":
        return {
            "id": "complete_kgw_joint_stage_a_blinded_review",
            "reason": "Automated Stage A finalists require the preregistered blinded review.",
            "command": "Prepare, independently rate, collate and apply the frozen Stage A blinded-review packet.",
        }
    if stage_a_status != "kgw_joint_stage_a_candidate_selected" or not selection.exists():
        return {
            "id": "stop_kgw_joint_after_stage_a_failure",
            "reason": "Stage A selected no usable candidate; the preregistered hard stop applies.",
            "command": "Stop the KGW feasibility study; do not run Stage B or another tuning round.",
        }
    if not stage_b_run.exists() or load_json(stage_b_run).get("status") != "kgw_joint_stage_b_complete":
        return {
            "id": "start_or_resume_kgw_joint_stage_b",
            "reason": "One Stage A candidate was selected; independent all-key Stage B is authorized.",
            "command": f".venv/bin/python -m ai_watermarks_phase2.kgw_joint_stage --stage stage_b {authorization_arg}",
        }
    if not stage_b_analysis.exists():
        return {
            "id": "analyse_kgw_joint_stage_b",
            "reason": "Stage B generation is complete and has not been evaluated.",
            "command": ".venv/bin/python validation/analyse_phase2_v2_kgw_joint_stage_b.py",
        }
    stage_b_status = load_json(stage_b_analysis).get("status")
    return {
        "id": (
            "complete_kgw_joint_stage_b_blinded_review"
            if stage_b_status == "kgw_joint_stage_b_awaiting_blinded_review"
            else "report_kgw_joint_terminal_result"
        ),
        "reason": f"Stage B has reached status {stage_b_status}.",
        "command": (
            "Complete the frozen Stage B blinded review."
            if stage_b_status == "kgw_joint_stage_b_awaiting_blinded_review"
            else "Report the terminal feasibility result; do not retune."
        ),
    }


def split_status(role: str, target: int, batch_size: int) -> dict[str, Any]:
    run_dir = RESULTS / role
    metadata_path = run_dir / "run.json"
    paths = sorted((run_dir / "batches").glob("batch-*.json"))
    names = [path.name for path in paths]
    expected_names = [f"batch-{index:06d}.json" for index in range(len(paths))]
    contiguous = names == expected_names
    durable_records = len(paths) * batch_size
    result: dict[str, Any] = {
        "role": role,
        "metadata_exists": metadata_path.exists(),
        "batch_files": len(paths),
        "batches_contiguous": contiguous,
        "durable_records_from_files": durable_records,
        "target_records": target,
    }
    if metadata_path.exists():
        metadata = load_json(metadata_path)
        result.update(
            {
                "metadata_status": metadata.get("status"),
                "metadata_records": metadata.get("records"),
                "metadata_generated_at": metadata.get("generated_at"),
                "metadata_matches_files": metadata.get("records") == durable_records,
            }
        )
    else:
        result.update(
            {
                "metadata_status": "not_started",
                "metadata_records": 0,
                "metadata_generated_at": None,
                "metadata_matches_files": durable_records == 0,
            }
        )
    result["complete"] = (
        result["metadata_status"] == "confirmatory_split_complete"
        and durable_records == target
        and contiguous
        and result["metadata_matches_files"]
    )
    result["partial"] = 0 < durable_records < target
    return result


def determine_next_action(
    calibration: dict[str, Any], confirmation: dict[str, Any]
) -> dict[str, str]:
    thresholds = RESULTS / "thresholds.json"
    gate = RESULTS / "confirmation-gate.json"
    # The gate record is durable proof that both splits were generated and
    # evaluated once. The raw per-batch output is large and is not part of the
    # public release, so its absence must never be read as "generation never
    # ran" and turned into an instruction to start a multi-day run.
    if gate.exists():
        return post_gate_next_action(gate)
    if not calibration["complete"]:
        return {
            "id": "resume_calibration",
            "reason": "Calibration is absent or incomplete; later gates are unauthorized.",
            "command": ".venv/bin/python -m ai_watermarks_phase2.confirmatory_null --split calibration",
        }
    if not thresholds.exists():
        return {
            "id": "fit_and_freeze_thresholds",
            "reason": "Calibration is complete and no frozen threshold artifact exists.",
            "command": ".venv/bin/python -m ai_watermarks_phase2.calibration_gate fit",
        }
    if not confirmation["complete"]:
        return {
            "id": "start_or_resume_confirmation",
            "reason": "Frozen thresholds exist, but confirmation is absent or incomplete.",
            "command": (
                ".venv/bin/python -m ai_watermarks_phase2.confirmatory_null "
                "--split confirmation "
                "--thresholds results/phase2-confirmatory-null/thresholds.json "
                "--authorize-confirmation"
            ),
        }
    return {
        "id": "evaluate_confirmation_once",
        "reason": "Confirmation is complete and has not yet been evaluated.",
        "command": ".venv/bin/python -m ai_watermarks_phase2.calibration_gate evaluate",
    }


def post_gate_next_action(gate: Path) -> dict[str, str]:
    """What to do once the one-shot confirmation has been evaluated."""
    gate_result = load_json(gate)
    if gate_result.get("status") == "confirmation_gate_passed":
        return {
            "id": "positive_variance_pilot",
            "reason": "The one-shot null confirmation gate passed; positive power work is authorized.",
            "command": "Implement and run the predeclared watermarked-positive variance pilot before attacks.",
        }
    if KGW_BIAS_ANALYSIS.exists():
        development = load_json(KGW_BIAS_ANALYSIS)
        if (
            development.get("status") == "kgw_bias_development_failed"
            and development.get("selected_bias") is None
        ):
            if KGW_FEASIBILITY_DECISION.exists():
                return kgw_joint_next_action()
            return {
                "id": "decide_kgw_feasibility",
                "reason": (
                    "The v1 null gate failed, the v2 positive screen failed, and "
                    "the final fresh KGW bias bracket selected no candidate. "
                    "Bias-only tuning, the v2 null run, and attacks are closed."
                ),
                "command": (
                    "Prepare and approve a formal KGW feasibility/design decision: "
                    "either justify a genuinely new preregistered KGW parameter-family "
                    "study or define a separately scoped future protocol. Do not start "
                    "more generation yet."
                ),
            }
    return {
        "id": "stop_and_report_failed_gate",
        "reason": "The one-shot confirmation gate failed; attacks and post-hoc retuning are unauthorized.",
        "command": "Document failed cells and reassess the research claim without reusing confirmation for tuning.",
    }


def build_status() -> dict[str, Any]:
    protocol = load_json(PROTOCOL)
    target = int(protocol["selection"]["samples_per_split"])
    batch_size = int(protocol["generation"]["batch_size"])
    calibration = split_status("calibration", target, batch_size)
    confirmation = split_status("confirmation", target, batch_size)
    return {
        "schema_version": 1,
        "protocol_id": protocol["protocol_id"],
        "note": "Saved artifacts are authoritative; process liveness must be checked separately.",
        "calibration": calibration,
        "thresholds_exists": (RESULTS / "thresholds.json").exists(),
        "confirmation": confirmation,
        "confirmation_gate_exists": (RESULTS / "confirmation-gate.json").exists(),
        "kgw_bias_development_analysis_exists": KGW_BIAS_ANALYSIS.exists(),
        "kgw_feasibility_decision_exists": KGW_FEASIBILITY_DECISION.exists(),
        "kgw_joint_protocol_config_exists": KGW_JOINT_CONFIG.exists(),
        "kgw_joint_protocol_freeze_exists": KGW_JOINT_FREEZE.exists(),
        "kgw_joint_generation_authorization_exists": KGW_JOINT_AUTHORIZATION.exists(),
        "kgw_joint_closure_exists": KGW_JOINT_CLOSURE.exists(),
        "next_action": determine_next_action(calibration, confirmation),
        "integrity_constraints": [
            "Do not alter fingerprinted inputs during a partial run.",
            "Do not use partial scores to change the frozen protocol.",
            "Do not begin attacks unless the one-shot confirmation gate passes.",
        ],
    }


def main() -> int:
    status = build_status()
    print(json.dumps(status, indent=2))
    split_values = (status["calibration"], status["confirmation"])
    if any(
        not value["batches_contiguous"] or not value["metadata_matches_files"]
        for value in split_values
    ):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
