import json
from pathlib import Path

from validation.analyse_phase2_confirmation_failure import (
    maximum_passing_exceedances_binary,
)


def test_v2_draft_cutoffs_are_exact() -> None:
    config = json.loads(
        Path("configs/phase2-confirmatory-null-v2-draft.json").read_text(
            encoding="utf-8"
        )
    )
    acceptance = config["acceptance"]
    alpha = (1.0 - acceptance["familywise_confidence"]) / acceptance["primary_cells"]
    assert config["status"] == "draft_not_authorized_for_generation"
    assert maximum_passing_exceedances_binary(
        samples=20000,
        target_fpr=acceptance["calibration_design_fpr"],
        alpha=alpha,
    ) == acceptance["maximum_calibration_exceedances_per_20000"] == 69
    assert maximum_passing_exceedances_binary(
        samples=20000,
        target_fpr=acceptance["confirmation_target_fpr"],
        alpha=alpha,
    ) == acceptance["maximum_confirmation_exceedances_per_20000"] == 156


def test_ultrachat_source_audit_has_capacity_without_authorizing_generation() -> None:
    audit = json.loads(
        Path("data/phase2-ultrachat-source-audit.json").read_text(encoding="utf-8")
    )
    assert audit["status"] == "capacity_valid"
    assert audit["source"]["rows"] == 207865
    assert audit["selection"]["required_records"] == 40000
    assert audit["selection"]["eligible_records"] == 203109
    assert audit["selection"]["capacity_surplus"] == 163109
    assert audit["selection"]["rejected"]["prior_study_overlap"] == 204
    assert "no manifests, thresholds, or generations produced" in audit["authorization"]
