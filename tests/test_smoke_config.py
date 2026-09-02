from copy import deepcopy
from pathlib import Path

import pytest

from ai_watermarks_phase2.smoke import load_json, main, validate_configuration


def test_committed_smoke_configuration_is_valid():
    config = load_json(Path("configs/phase2-smoke.json"))
    prompts = load_json(Path("data/phase2-smoke-prompts.json"))
    validate_configuration(config, prompts)


@pytest.mark.parametrize(
    ("section", "setting", "value", "message"),
    [
        ("generation", "min_new_tokens", 0, "min_new_tokens"),
        ("generation", "temperature", 0, "temperature"),
        ("generation", "top_k", True, "top_k"),
        ("kgw", "greenlist_ratio", 1.0, "greenlist_ratio"),
        ("synthid", "ngram_len", 1, "ngram_len"),
        ("attacks", "interval", 0, "interval"),
    ],
)
def test_configuration_rejects_invalid_numeric_settings(
    section, setting, value, message
):
    config = load_json(Path("configs/phase2-smoke.json"))
    prompts = load_json(Path("data/phase2-smoke-prompts.json"))
    invalid = deepcopy(config)
    invalid[section][setting] = value

    with pytest.raises(ValueError, match=message):
        validate_configuration(invalid, prompts)


@pytest.mark.parametrize("limit", ["0", "-1", "11"])
def test_smoke_cli_rejects_limits_that_cannot_form_a_valid_gate(limit):
    with pytest.raises(SystemExit) as error:
        main(["--limit", limit, "--dry-run"])

    assert error.value.code == 2
