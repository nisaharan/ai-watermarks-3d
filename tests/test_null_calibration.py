from collections import Counter
from pathlib import Path

from ai_watermarks_phase2.null_calibration import _tail_diagnostic
from ai_watermarks_phase2.smoke import load_json


def test_frozen_null_prompt_manifest_matches_the_design():
    config = load_json(Path("configs/phase2-null-calibration.json"))
    manifest = load_json(Path("data/phase2-null-calibration-prompts.json"))
    records = manifest["records"]

    assert len(records) == config["selection"]["target_samples"] == 500
    assert Counter(item["category"] for item in records) == Counter(
        config["selection"]["category_allocation"]
    )
    assert len({item["id"] for item in records}) == len(records)
    assert len({item["prompt_sha256"] for item in records}) == len(records)
    assert max(item["prompt_tokens"] for item in records) <= config["selection"][
        "max_prompt_tokens"
    ]


def test_tail_diagnostic_uses_strict_empirical_cutoff_and_wilson_interval():
    diagnostic = _tail_diagnostic([float(value) for value in range(1, 101)], 0.05)

    assert diagnostic["cutoff"] == 95.0
    assert diagnostic["exceedances"] == 5
    assert diagnostic["empirical_rate"] == 0.05
    lower, upper = diagnostic["wilson_95_percent"]
    assert lower < 0.05 < upper
