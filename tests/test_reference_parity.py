"""Exact parity of the canonical adapters against the pinned reference sources.

This is the deterministic fixture gate: it needs no model and no smoke run, only
the reference files named in `configs/phase2-reference-sources.json`. Populate
them with `validation/phase2_reference_crosscheck.py` (without `--offline`).
"""

import sys
from pathlib import Path

import pytest

from ai_watermarks_phase2 import canonical
from ai_watermarks_phase2.smoke import load_json

torch = pytest.importorskip("torch")
pytest.importorskip("transformers")

CACHE = Path(".cache/phase2-references")
MANIFEST = Path("configs/phase2-reference-sources.json")
CONFIG = load_json(Path("configs/phase2-smoke.json"))
DEVICE = torch.device("cpu")
# Parity is a property of the keyed PRF, not of any particular model, so the
# fixture uses a small synthetic vocabulary and a fixed token sequence.
VOCAB_SIZE = 4096
FIXTURE = [7, 19, 3, 4095, 512, 7, 19, 3, 4095, 88, 1024, 2, 2, 640, 331, 7, 19, 3, 41, 900]

pytestmark = pytest.mark.skipif(
    not (CACHE / "kgw" / "alternative_prf_schemes.py").exists(),
    reason="pinned reference sources are not cached; run the cross-check online first",
)


@pytest.fixture(scope="module")
def references():
    sys.path.insert(0, "validation")
    import phase2_reference_crosscheck as crosscheck

    crosscheck.fetch_sources(load_json(MANIFEST), CACHE, offline=True)
    return crosscheck.load_kgw_reference(CACHE), crosscheck.load_synthid_reference(CACHE)


def test_kgw_author_variant_matches_the_reference_green_lists(references):
    kgw_reference, _ = references
    settings = CONFIG["kgw"]
    reference = kgw_reference.WatermarkDetector(
        vocab=list(range(VOCAB_SIZE)),
        gamma=float(settings["greenlist_ratio"]),
        delta=float(settings["bias"]),
        seeding_scheme="selfhash",
        select_green_tokens=True,
        device=DEVICE,
        tokenizer=object(),
        normalizers=[],
        ignore_repeated_ngrams=True,
    )
    processor = canonical.build_kgw_config(
        settings, canonical.KGW_AUTHOR_VARIANT
    ).construct_processor(VOCAB_SIZE, DEVICE)

    width = int(settings["context_width"])
    compared = 0
    for position in range(width - 1, len(FIXTURE)):
        ngram = tuple(FIXTURE[position - width + 1 : position + 1])
        target = FIXTURE[position]
        mine = target in processor._get_greenlist_ids(torch.tensor(ngram))
        theirs = reference._get_ngram_score_cached(ngram, target)
        assert bool(mine) is bool(theirs), f"green-hit mismatch at position {position}"
        compared += 1
    assert compared == len(FIXTURE) - width + 1


def test_kgw_transformers_variant_diverges_from_the_reference(references):
    kgw_reference, _ = references
    settings = CONFIG["kgw"]
    reference = kgw_reference.WatermarkDetector(
        vocab=list(range(VOCAB_SIZE)),
        gamma=float(settings["greenlist_ratio"]),
        delta=float(settings["bias"]),
        seeding_scheme="selfhash",
        select_green_tokens=True,
        device=DEVICE,
        tokenizer=object(),
        normalizers=[],
        ignore_repeated_ngrams=True,
    )
    processor = canonical.build_kgw_config(
        settings, canonical.KGW_TRANSFORMERS_VARIANT
    ).construct_processor(VOCAB_SIZE, DEVICE)

    width = int(settings["context_width"])
    hits = []
    for position in range(width - 1, len(FIXTURE)):
        ngram = tuple(FIXTURE[position - width + 1 : position + 1])
        target = FIXTURE[position]
        mine = bool(target in processor._get_greenlist_ids(torch.tensor(ngram)))
        hits.append(mine == bool(reference._get_ngram_score_cached(ngram, target)))
    assert not all(hits), "the Transformers variant is expected to diverge"


def test_synthid_deepmind_variant_matches_the_reference(references):
    _, synthid_reference = references
    settings = CONFIG["synthid"]
    reference = synthid_reference.SynthIDLogitsProcessor(
        ngram_len=int(settings["ngram_len"]),
        keys=settings["keys"],
        context_history_size=int(settings["context_history_size"]),
        temperature=0.8,
        top_k=40,
        device=DEVICE,
        skip_first_ngram_calls=bool(settings["skip_first_ngram_calls"]),
    )
    processor = canonical.build_synthid_config(
        settings, canonical.SYNTHID_DEEPMIND_VARIANT
    ).construct_processor(VOCAB_SIZE, DEVICE)

    ids = torch.tensor([FIXTURE], dtype=torch.long)
    assert processor.hash_iv == reference.hash_iv
    assert torch.equal(processor.compute_g_values(ids), reference.compute_g_values(ids))
    assert torch.equal(
        processor.compute_context_repetition_mask(ids),
        reference.compute_context_repetition_mask(ids),
    )


def test_synthid_transformers_variant_diverges_from_the_reference(references):
    _, synthid_reference = references
    settings = CONFIG["synthid"]
    reference = synthid_reference.SynthIDLogitsProcessor(
        ngram_len=int(settings["ngram_len"]),
        keys=settings["keys"],
        context_history_size=int(settings["context_history_size"]),
        temperature=0.8,
        top_k=40,
        device=DEVICE,
        skip_first_ngram_calls=bool(settings["skip_first_ngram_calls"]),
    )
    processor = canonical.build_synthid_config(
        settings, canonical.SYNTHID_TRANSFORMERS_VARIANT
    ).construct_processor(VOCAB_SIZE, DEVICE)

    ids = torch.tensor([FIXTURE], dtype=torch.long)
    assert not torch.equal(processor.compute_g_values(ids), reference.compute_g_values(ids))
    # Only the g-values diverge; eligibility masking is shared.
    assert torch.equal(
        processor.compute_context_repetition_mask(ids),
        reference.compute_context_repetition_mask(ids),
    )
