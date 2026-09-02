import json
from collections import Counter
from pathlib import Path

import pytest

from ai_watermarks_phase2.calibration_gate import (
    clopper_pearson_upper,
    maximum_passing_exceedances,
    threshold_candidate,
)
from ai_watermarks_phase2.confirmatory_null import effective_config
from ai_watermarks_phase2.smoke import load_json
from ai_watermarks_phase2.variance_pilot import validate_design


PROTOCOL_PATH = Path("configs/phase2-confirmatory-null.json")
CALIBRATION_PATH = Path("data/phase2-confirmatory-calibration-prompts.json")
CONFIRMATION_PATH = Path("data/phase2-confirmatory-confirmation-prompts.json")


def test_exact_familywise_acceptance_boundary_is_28_of_5000():
    protocol = load_json(PROTOCOL_PATH)
    acceptance = protocol["acceptance"]
    alpha = (1.0 - acceptance["familywise_confidence"]) / acceptance["primary_cells"]

    maximum = maximum_passing_exceedances(
        samples=protocol["selection"]["samples_per_split"],
        target_fpr=acceptance["target_fpr"],
        familywise_alpha=1.0 - acceptance["familywise_confidence"],
        cells=acceptance["primary_cells"],
    )

    assert maximum == acceptance["maximum_exceedances_per_5000"] == 28
    assert clopper_pearson_upper(28, 5000, alpha) < 0.01
    assert clopper_pearson_upper(29, 5000, alpha) > 0.01
    assert 5000 - maximum == acceptance["minimum_order_statistic_index_one_based"]


def test_threshold_candidate_uses_strict_greater_than_and_is_tie_conservative():
    values = [0.1, 0.2, 0.3, 0.4, 0.5]
    threshold = threshold_candidate(values, allowed_exceedances=2)
    assert threshold == 0.3
    assert sum(value > threshold for value in values) == 2

    tied = [0.1, 0.3, 0.3, 0.3, 0.5]
    threshold = threshold_candidate(tied, allowed_exceedances=2)
    assert threshold == 0.3
    assert sum(value > threshold for value in tied) == 1


def test_confirmatory_manifests_are_disjoint_matched_and_exclude_prior_prompts():
    calibration = load_json(CALIBRATION_PATH)
    confirmation = load_json(CONFIRMATION_PATH)
    assert calibration["split_role"] == "calibration"
    assert confirmation["split_role"] == "confirmation"
    assert calibration["record_count"] == confirmation["record_count"] == 5000
    assert calibration["selection"]["category_allocation"] == confirmation["selection"][
        "category_allocation"
    ]
    assert Counter(item["category"] for item in calibration["records"]) == Counter(
        calibration["selection"]["category_allocation"]
    )
    assert Counter(item["category"] for item in confirmation["records"]) == Counter(
        confirmation["selection"]["category_allocation"]
    )

    calibration_rows = {item["source_row"] for item in calibration["records"]}
    confirmation_rows = {item["source_row"] for item in confirmation["records"]}
    calibration_hashes = {item["prompt_sha256"] for item in calibration["records"]}
    confirmation_hashes = {item["prompt_sha256"] for item in confirmation["records"]}
    assert not calibration_rows & confirmation_rows
    assert not calibration_hashes & confirmation_hashes

    prior_rows = set()
    prior_hashes = set()
    for name in calibration["selection"]["exclusion_manifests"]:
        value = json.loads(Path(name).read_text(encoding="utf-8"))
        records = value if isinstance(value, list) else value["records"]
        prior_rows.update(
            item["source_row"] for item in records if isinstance(item.get("source_row"), int)
        )
        prior_hashes.update(item["prompt_sha256"] for item in records if item.get("prompt_sha256"))
    assert not prior_rows & (calibration_rows | confirmation_rows)
    assert not prior_hashes & (calibration_hashes | confirmation_hashes)


@pytest.mark.parametrize("split,path", [("calibration", CALIBRATION_PATH), ("confirmation", CONFIRMATION_PATH)])
def test_effective_confirmatory_design_is_valid(split, path):
    protocol = load_json(PROTOCOL_PATH)
    config = effective_config(protocol, split)
    prompts = load_json(path)["records"]
    validate_design(config, prompts)
