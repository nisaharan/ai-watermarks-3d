import json
from pathlib import Path

import pytest

from ai_watermarks_phase2 import canonical
from ai_watermarks_phase2.smoke import load_json, validate_configuration

torch = pytest.importorskip("torch")
pytest.importorskip("transformers")

CONFIG = load_json(Path("configs/phase2-smoke.json"))
VOCAB_SIZE = 49152
DEVICE = torch.device("cpu")


def test_committed_configuration_declares_known_variants():
    assert CONFIG["variants"]["kgw"] in canonical.KGW_VARIANTS
    assert CONFIG["variants"]["synthid"] in canonical.SYNTHID_VARIANTS


def test_unknown_variant_is_rejected():
    with pytest.raises(ValueError, match="Unknown KGW variant"):
        canonical.build_kgw_config(CONFIG["kgw"], "kgw_made_up")
    with pytest.raises(ValueError, match="Unknown SynthID variant"):
        canonical.build_synthid_config(CONFIG["synthid"], "synthid_made_up")


def test_configuration_validation_rejects_unknown_variant():
    prompts = load_json(Path("data/phase2-smoke-prompts.json"))
    broken = json.loads(json.dumps(CONFIG))
    broken["variants"]["kgw"] = "kgw_made_up"
    with pytest.raises(ValueError, match="variants.kgw"):
        validate_configuration(broken, prompts)


def test_author_kgw_table_is_key_independent():
    """The authors fix the hashint table; Transformers derives it from the key."""

    author = canonical.build_kgw_config(CONFIG["kgw"], canonical.KGW_AUTHOR_VARIANT)
    rekeyed = dict(CONFIG["kgw"], hashing_key=CONFIG["kgw"]["hashing_key"] + 2)
    author_rekeyed = canonical.build_kgw_config(rekeyed, canonical.KGW_AUTHOR_VARIANT)
    stock = canonical.build_kgw_config(CONFIG["kgw"], canonical.KGW_TRANSFORMERS_VARIANT)

    table = author.construct_processor(VOCAB_SIZE, DEVICE).fixed_table
    assert torch.equal(table, author_rekeyed.construct_processor(VOCAB_SIZE, DEVICE).fixed_table)
    assert not torch.equal(table, stock.construct_processor(VOCAB_SIZE, DEVICE).fixed_table)
    assert torch.equal(table, canonical.author_kgw_fixed_table(DEVICE))


def test_kgw_variants_assign_different_green_lists():
    ngram = torch.tensor([101, 202, 303, 404])
    author = canonical.build_kgw_config(
        CONFIG["kgw"], canonical.KGW_AUTHOR_VARIANT
    ).construct_processor(VOCAB_SIZE, DEVICE)
    stock = canonical.build_kgw_config(
        CONFIG["kgw"], canonical.KGW_TRANSFORMERS_VARIANT
    ).construct_processor(VOCAB_SIZE, DEVICE)
    assert not torch.equal(author._get_greenlist_ids(ngram), stock._get_greenlist_ids(ngram))


def test_synthid_hash_iv_matches_the_reference_derivation():
    import hashlib

    keys = torch.tensor(CONFIG["synthid"]["keys"])
    digest = hashlib.sha256(keys.to(torch.long).numpy().tobytes()).digest()
    expected = int.from_bytes(digest, byteorder="big") % torch.iinfo(torch.int64).max

    processor = canonical.build_synthid_config(
        CONFIG["synthid"], canonical.SYNTHID_DEEPMIND_VARIANT
    ).construct_processor(VOCAB_SIZE, DEVICE)
    assert processor.hash_iv == expected
    assert canonical.synthid_hash_iv(keys) == expected


def test_synthid_variants_assign_different_g_values():
    ids = torch.arange(1, 41, dtype=torch.long)[None, :]
    deepmind = canonical.build_synthid_config(
        CONFIG["synthid"], canonical.SYNTHID_DEEPMIND_VARIANT
    ).construct_processor(VOCAB_SIZE, DEVICE)
    stock = canonical.build_synthid_config(
        CONFIG["synthid"], canonical.SYNTHID_TRANSFORMERS_VARIANT
    ).construct_processor(VOCAB_SIZE, DEVICE)

    deepmind_g = deepmind.compute_g_values(ids)
    stock_g = stock.compute_g_values(ids)
    assert deepmind_g.shape == stock_g.shape
    assert not torch.equal(deepmind_g, stock_g)
    assert set(deepmind_g.unique().tolist()) <= {0, 1}
    # Mask eligibility is unaffected by the g-value derivation.
    assert torch.equal(
        deepmind.compute_context_repetition_mask(ids),
        stock.compute_context_repetition_mask(ids),
    )


def test_variant_round_trips_through_the_configuration_object():
    for variant in canonical.KGW_VARIANTS:
        config = canonical.build_kgw_config(CONFIG["kgw"], variant)
        assert canonical.kgw_variant_of(config) == variant
    for variant in canonical.SYNTHID_VARIANTS:
        config = canonical.build_synthid_config(CONFIG["synthid"], variant)
        assert canonical.synthid_variant_of(config) == variant


def test_inert_settings_are_declared_and_true():
    """A field a variant never reads must be named, so nobody tunes it blindly."""

    assert canonical.inert_settings(canonical.SYNTHID_TRANSFORMERS_VARIANT) == ()
    inert = canonical.inert_settings(canonical.SYNTHID_DEEPMIND_VARIANT)
    assert set(inert) == {"sampling_table_seed", "sampling_table_size"}

    ids = torch.arange(1, 41, dtype=torch.long)[None, :]

    def g_values(variant, **overrides):
        settings = dict(CONFIG["synthid"], **overrides)
        processor = canonical.build_synthid_config(settings, variant).construct_processor(
            VOCAB_SIZE, DEVICE
        )
        return processor.compute_g_values(ids)

    baseline = g_values(canonical.SYNTHID_DEEPMIND_VARIANT)
    for field in inert:
        changed = g_values(canonical.SYNTHID_DEEPMIND_VARIANT, **{field: 4096})
        assert torch.equal(baseline, changed), f"{field} was declared inert but is not"

    live = g_values(canonical.SYNTHID_TRANSFORMERS_VARIANT)
    assert not torch.equal(
        live, g_values(canonical.SYNTHID_TRANSFORMERS_VARIANT, sampling_table_seed=4096)
    )


def test_author_kgw_variant_uses_the_authors_rejection_tail():
    processor = canonical.build_kgw_config(
        CONFIG["kgw"], canonical.KGW_AUTHOR_VARIANT
    ).construct_processor(VOCAB_SIZE, DEVICE)
    stock = canonical.build_kgw_config(
        CONFIG["kgw"], canonical.KGW_TRANSFORMERS_VARIANT
    ).construct_processor(VOCAB_SIZE, DEVICE)

    # The authors break after index 40, so they consider one more candidate.
    assert canonical.KGW_AUTHOR_REJECTION_TAIL_INDEX == 40
    assert type(processor).__name__ == "AuthorKGWLogitsProcessor"
    assert type(stock).__name__ == "WatermarkLogitsProcessor"
