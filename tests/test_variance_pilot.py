from pathlib import Path

from ai_watermarks_phase2.key_schedule import derive_schedule, is_prime
from ai_watermarks_phase2.smoke import load_json
from ai_watermarks_phase2.variance_pilot import validate_design


def test_frozen_key_schedule_is_reproducible_and_uses_prime_kgw_keys():
    config = load_json(Path("configs/phase2-variance-pilot.json"))
    expected = derive_schedule(10)

    assert config["key_schedule"]["kgw"] == expected["kgw"]
    assert config["key_schedule"]["synthid"] == expected["synthid"]
    assert all(is_prime(key) for key in expected["kgw"])


def test_frozen_variance_design_is_valid():
    config = load_json(Path("configs/phase2-variance-pilot.json"))
    prompts = load_json(Path(config["prompt_manifest"]))["records"]

    validate_design(config, prompts)


def test_independent_model_replication_design_is_valid_and_balanced():
    config = load_json(Path("configs/phase2-variance-replication.json"))
    prompts = load_json(Path(config["prompt_manifest"]))["records"]

    validate_design(config, prompts)
    assert len(prompts) == 104
    assert set(prompt["category"] for prompt in prompts) == {
        "brainstorming",
        "classification",
        "closed_qa",
        "creative_writing",
        "general_qa",
        "information_extraction",
        "open_qa",
        "summarization",
    }
    assert all(
        sum(prompt["category"] == category for prompt in prompts) == 13
        for category in {prompt["category"] for prompt in prompts}
    )
