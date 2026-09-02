from pathlib import Path

import pytest

from ai_watermarks_phase2.resume_status import build_status

# The full routing depends on development artifacts that the public release
# excludes on purpose: the v2 bias brackets and the abandoned joint study. In a
# clone those are absent, so only the safety property is asserted there.
DEVELOPMENT_STATE = Path("results/phase2-v2-kgw-joint-feasibility/study-closure.json")

GENERATION_ENTRY_POINTS = ("confirmatory_null", "kgw_joint_stage", "--split")


def test_resume_status_never_instructs_new_generation() -> None:
    """The study is over. No state of the working tree should start a run.

    The raw per-batch output is not part of the release, and its absence used to
    read as "calibration never ran", which routed a clone to a multi-day
    generation command.
    """
    action = build_status()["next_action"]
    assert action["id"] in {
        "prepare_phase2_calibration_publication",
        "stop_and_report_failed_gate",
    }
    for entry_point in GENERATION_ENTRY_POINTS:
        assert entry_point not in action["command"]


@pytest.mark.skipif(
    not DEVELOPMENT_STATE.exists(),
    reason="development artifacts are retained locally and are not part of the release",
)
def test_current_resume_priority_routes_to_publication() -> None:
    status = build_status()
    assert status["kgw_bias_development_analysis_exists"] is True
    assert status["kgw_feasibility_decision_exists"] is True
    assert status["kgw_joint_protocol_config_exists"] is True
    assert status["kgw_joint_protocol_freeze_exists"] is True
    assert status["kgw_joint_generation_authorization_exists"] is True
    assert status["kgw_joint_closure_exists"] is True
    assert status["next_action"]["id"] == "prepare_phase2_calibration_publication"
    assert "do not resume Stage A" in status["next_action"]["command"]
