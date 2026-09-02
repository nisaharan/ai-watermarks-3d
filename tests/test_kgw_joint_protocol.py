import json
from pathlib import Path

import pytest

from ai_watermarks_phase2.kgw_joint_protocol import (
    candidate_grid,
    clopper_pearson_lower,
    expected_plan,
    validate_authorization,
    validate_protocol,
)
from ai_watermarks_phase2.kgw_joint_stage import batch_plan, paired_batch_seed
from validation.analyse_phase2_v2_kgw_joint_stage_a import (
    apply_blinded_reviews_and_select,
)
from validation.analyse_phase2_v2_kgw_joint_stage_b import evaluate_stage_b
from validation.prepare_phase2_v2_kgw_blinded_review import pair_rank


CONFIG = Path("configs/phase2-v2-kgw-joint-feasibility.json")


def load_config() -> dict:
    return json.loads(CONFIG.read_text())


def test_joint_protocol_grid_counts_and_exact_null_gate() -> None:
    config = load_config()
    result = validate_protocol(config)
    assert candidate_grid(config) == [
        (gamma, delta)
        for gamma in (0.25, 0.5, 0.7)
        for delta in (2.0, 2.5, 3.0, 4.0)
    ]
    assert expected_plan(config)["stage_a_total_outputs"] == 5200
    assert expected_plan(config)["stage_b_total_outputs"] == 2000
    assert result["development_null_maximum_strict_exceedances"] == 9
    assert result["development_null_upper_bound_at_maximum"] < 0.005
    assert result["development_null_upper_bound_at_next"] > 0.005


def test_detection_interval_is_descriptive_not_the_point_gate() -> None:
    assert clopper_pearson_lower(80, 100, 0.05) < 0.8
    assert clopper_pearson_lower(87, 100, 0.05) >= 0.8


def test_pending_protocol_cannot_self_authorize(tmp_path: Path) -> None:
    config = load_config()
    assert config["separation"]["study_generation_authorized"] is False
    with pytest.raises(FileNotFoundError):
        validate_authorization(CONFIG, tmp_path / "missing-separate-authorization.json")


@pytest.mark.skipif(
    not Path("results/phase2-v2-kgw-joint-feasibility/protocol-freeze.json").exists(),
    reason="protocol freeze is development-only state and is not part of the release",
)
def test_separate_frozen_authorization_validates() -> None:
    authorization = validate_authorization(
        CONFIG,
        Path("configs/phase2-v2-kgw-joint-feasibility-authorization.json"),
    )
    assert authorization["status"] == "kgw_joint_feasibility_generation_approved"


def test_stage_a_plan_pairs_control_and_candidate_seeds() -> None:
    conditions = [(None, None), (0.25, 2.0), (0.5, 2.5)]
    plan = batch_plan([3, 5], conditions, 100, 5)
    assert len(plan) == 120
    seeds = {
        paired_batch_seed(1000, [3, 5], row["key_index"], row["prompt_start"], 5, 100)
        for row in plan
        if row["key_index"] == 3 and row["prompt_start"] == 0
    }
    assert seeds == {1000}


def test_stage_a_selection_uses_nll_tolerance_then_frozen_tiebreakers() -> None:
    config = load_config()
    decisions = []
    for gamma, delta in candidate_grid(config):
        passed = (gamma, delta) in {(0.25, 2.0), (0.5, 2.5), (0.7, 2.0)}
        decisions.append(
            {
                "gamma": gamma,
                "delta": delta,
                "automated_passed": passed,
                "worst_cell_nll_increase": {
                    (0.25, 2.0): 0.020,
                    (0.5, 2.5): 0.016,
                    (0.7, 2.0): 0.018,
                }.get((gamma, delta), 1.0),
            }
        )
    review = {
        "status": "kgw_joint_blinded_review_complete",
        "stage": "stage_a",
        "protocol_id": config["protocol_id"],
        "candidate_reviews": [
            {
                "gamma": gamma,
                "delta": delta,
                "pairs": 50,
                "candidate_unusable_pairs": 0,
                "candidate_worse_pairs": 5,
            }
            for gamma, delta in ((0.25, 2.0), (0.5, 2.5), (0.7, 2.0))
        ],
    }
    _, selected, status = apply_blinded_reviews_and_select(config, decisions, review)
    assert status == "kgw_joint_stage_a_candidate_selected"
    # All three lie within 0.005 of the best NLL; lower delta wins, then gamma
    # closest to 0.5, which selects gamma 0.7 over gamma 0.25.
    assert selected == {"gamma": 0.7, "delta": 2.0}


def test_stage_b_requires_all_cells_and_blinded_veto() -> None:
    config = load_config()
    selection = {
        "status": "kgw_joint_stage_a_candidate_selected",
        "selected_candidate": {"gamma": 0.5, "delta": 2.5},
    }
    cells = [
        {
            "gamma": 0.5,
            "delta": 2.5,
            "detection_passed": True,
            "automated_quality_passed": True,
            "automated_cell_passed": True,
        }
        for _ in range(30)
    ]
    status, _ = evaluate_stage_b(config, cells, selection, None)
    assert status == "kgw_joint_stage_b_awaiting_blinded_review"
    review = {
        "status": "kgw_joint_blinded_review_complete",
        "stage": "stage_b",
        "protocol_id": config["protocol_id"],
        "candidate_reviews": [
            {
                "gamma": 0.5,
                "delta": 2.5,
                "pairs": 50,
                "candidate_unusable_pairs": 1,
                "candidate_worse_pairs": 0,
            }
        ],
    }
    status, decision = evaluate_stage_b(config, cells, selection, review)
    assert status == "kgw_joint_stage_b_failed"
    assert decision["blinded_review_passed"] is False


def test_blinded_pair_rank_is_deterministic_and_parameter_specific() -> None:
    first = pair_rank("protocol", "stage_a", 0.5, 2.5, "03", "prompt-hash")
    assert first == pair_rank("protocol", "stage_a", 0.5, 2.5, "03", "prompt-hash")
    assert first != pair_rank("protocol", "stage_a", 0.5, 3.0, "03", "prompt-hash")
