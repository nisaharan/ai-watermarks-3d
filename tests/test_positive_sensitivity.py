import json
from pathlib import Path

from ai_watermarks_phase2.positive_sensitivity import batch_plan, condition_ids
from validation.analyse_phase2_confirmation_failure import (
    maximum_passing_exceedances_binary,
)
from validation.analyse_phase2_v2_positive_sensitivity import evaluate


def test_predeclared_positive_screen_shape_and_calibration_cutoff() -> None:
    config = json.loads(
        Path("configs/phase2-v2-positive-sensitivity.json").read_text(encoding="utf-8")
    )
    threshold = config["provisional_thresholds"]
    assert config["status"] == "development_only_predeclared"
    assert threshold["confirmation_scores_used"] is False
    assert config["generation"]["total_watermarked_outputs"] == 1000
    assert len(condition_ids()) == 20
    assert len(batch_plan(50, 5)) == 200
    assert maximum_passing_exceedances_binary(
        samples=threshold["source_samples_per_cell"],
        target_fpr=threshold["design_fpr"],
        alpha=threshold["per_cell_alpha"],
    ) == threshold["maximum_strict_exceedances"] == 10


def synthetic_thresholds() -> dict:
    operational = []
    for length in (128, 256, 512):
        for index in range(10):
            operational.append(
                {
                    "scheme": "kgw",
                    "key_id": f"kgw-{index:02d}",
                    "length": length,
                    "threshold": 0.5,
                }
            )
        operational.append(
            {
                "scheme": "synthid",
                "key_id": "shared",
                "length": length,
                "threshold": 0.5,
            }
        )
    return {"operational_thresholds": operational}


def synthetic_records() -> list[dict]:
    records = []
    for scheme, key_id, _ in condition_ids():
        for sample in range(50):
            prefix_results = []
            for length in (128, 256, 512):
                successes = 39 if (scheme, key_id, length) == ("kgw", "kgw-00", 128) else 40
                prefix_results.append(
                    {
                        "length": length,
                        "score": {"value": 1.0 if sample < successes else 0.0},
                    }
                )
            records.append(
                {
                    "scheme": scheme,
                    "key_id": key_id,
                    "variant": (
                        "kgw_author_selfhash_v1"
                        if scheme == "kgw"
                        else "synthid_deepmind_hash_v1"
                    ),
                    "prefix_results": prefix_results,
                }
            )
    return records


def test_positive_screen_keeps_cells_explicit_and_applies_fixed_minimum() -> None:
    cells = evaluate(synthetic_records(), synthetic_thresholds(), 50, 40)
    assert len(cells) == 60
    failed = [row for row in cells if not row["passed"]]
    assert len(failed) == 1
    assert (failed[0]["scheme"], failed[0]["key_id"], failed[0]["length"]) == (
        "kgw",
        "kgw-00",
        128,
    )
    assert failed[0]["strict_detections"] == 39
