import json
from pathlib import Path

from ai_watermarks_phase2.kgw_bias_development import batch_plan, paired_batch_seed
from validation.analyse_phase2_v2_kgw_bias_development import (
    apply_quality_and_select,
    distinct_ngram_fraction,
    repeated_ngram_fraction,
)
from ai_watermarks_phase2.kgw_bias_development_v2 import install_empty_index_safeguard


def test_plan_shape_and_biases_share_paired_seeds() -> None:
    keys, biases = [3, 5, 7, 8], [2.0, 2.5, 3.0]
    plan = batch_plan(keys, biases, 50, 5)
    assert len(plan) == 120
    seeds = {
        paired_batch_seed(100, keys, row["key_index"], row["prompt_start"], 5, 50)
        for row in plan if row["key_index"] == 3 and row["prompt_start"] == 0
    }
    assert seeds == {100}


def test_ngram_quality_metrics() -> None:
    tokens = [1, 2, 1, 2, 1, 2]
    assert repeated_ngram_fraction(tokens, 2) == 0.6
    assert distinct_ngram_fraction(tokens, 2) == 0.4


def test_selection_chooses_lowest_bias_passing_all_guardrails() -> None:
    config = {
        "generation": {"bias_candidates_in_selection_order": [2.0, 2.5, 3.0]},
        "quality_guardrails": {
            "reference_bias": 2.0,
            "conditional_base_model_nll_max_increase_nats_per_token": 0.15,
            "repeated_4gram_fraction_max_absolute_increase": 0.02,
            "distinct_2gram_fraction_max_absolute_decrease": 0.02,
        },
    }
    cells = []
    for bias in (2.0, 2.5, 3.0):
        for key in ("kgw-03", "kgw-05"):
            cells.append({
                "key_id": key, "bias": bias, "length": 128,
                "detection_passed": bias >= 2.5,
                "quality_means": {
                    "nll": 2.0 + 0.05 * (bias - 2.0),
                    "repeated_4gram_fraction": 0.01,
                    "distinct_2gram_fraction": 0.95,
                },
            })
    _, decisions, selected = apply_quality_and_select(config, cells)
    assert selected == 2.5
    assert [row["passed"] for row in decisions] == [False, True, True]


def test_empty_index_safeguard_returns_long_tensor() -> None:
    import torch
    from ai_watermarks_phase2 import canonical

    install_empty_index_safeguard()
    processor_class = canonical.canonical_classes()["AuthorKGWLogitsProcessor"]
    processor = object.__new__(processor_class)
    processor._get_greenlist_ids = lambda _tokens: torch.tensor([], dtype=torch.long)
    scores = torch.arange(50, dtype=torch.float32)
    result = processor._score_rejection_sampling(torch.tensor([1, 2, 3, 4]), scores)
    assert result.dtype == torch.long
    assert result.numel() == 0


def test_final_bracket_is_bounded_and_predeclared() -> None:
    config = json.loads(
        Path("configs/phase2-v2-kgw-bias-development-v3.json").read_text()
    )
    generation = config["generation"]
    assert config["status"] == "development_only_predeclared"
    assert generation["bias_candidates_in_selection_order"] == [2.0, 2.3, 2.4, 2.45]
    assert generation["total_watermarked_outputs"] == 800
    assert len(batch_plan(
        generation["target_key_indices"],
        generation["bias_candidates_in_selection_order"],
        generation["prompts_per_condition"],
        generation["batch_size"],
    )) == 160
    assert "stop bias-only tuning" in config["selection_rule"]["failure_consequence"]
