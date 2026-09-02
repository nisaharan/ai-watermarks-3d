from ai_watermarks_phase2.attacks import (
    delete_every,
    identity,
    insert_every,
    substitute_every,
    truncate,
)
from ai_watermarks_phase2.contexts import (
    ContextRule,
    eligible_positions,
    measure_context_survival,
)


def test_identity_has_complete_survival():
    original = list(range(20))
    attack = identity(original)
    rule = ContextRule("ordered-4", window_size=4)
    result = measure_context_survival(
        original, attack.tokens, attack.candidate_to_original, rule
    )
    assert result.original_eligible == 17
    assert result.effective_surviving == 17
    assert result.survival_rate == 1.0


def test_single_insertion_breaks_only_windows_crossing_insertion():
    original = list(range(10))
    attack = insert_every(original, interval=100, inserted_token=99, offset=5)
    rule = ContextRule("ordered-3", window_size=3)
    result = measure_context_survival(
        original, attack.tokens, attack.candidate_to_original, rule
    )
    assert result.effective_surviving < result.original_eligible
    assert result.effective_surviving > 0


def test_context_damage_increases_with_window_size():
    original = list(range(40))
    attack = substitute_every(original, interval=8, replacement_token=999)
    short = measure_context_survival(
        original,
        attack.tokens,
        attack.candidate_to_original,
        ContextRule("short", window_size=2),
    )
    long = measure_context_survival(
        original,
        attack.tokens,
        attack.candidate_to_original,
        ContextRule("long", window_size=5),
    )
    assert long.survival_rate < short.survival_rate


def test_deletion_and_truncation_do_not_inflate_denominator():
    original = list(range(30))
    rule = ContextRule("ordered-4", window_size=4)
    deleted = delete_every(original, interval=6)
    truncated = truncate(original, keep=12)
    deleted_result = measure_context_survival(
        original, deleted.tokens, deleted.candidate_to_original, rule
    )
    truncated_result = measure_context_survival(
        original, truncated.tokens, truncated.candidate_to_original, rule
    )
    assert deleted_result.original_eligible == truncated_result.original_eligible == 27
    assert 0 <= deleted_result.survival_rate <= 1
    assert 0 <= truncated_result.survival_rate <= 1


def test_repeated_context_masking_matches_first_occurrence_policy():
    tokens = [1, 2, 3, 1, 2, 4, 1, 2, 5]
    rule = ContextRule("synthid-like", window_size=3, deduplicate="context")
    mask = eligible_positions(tokens, rule)
    assert sum(mask) == 5
    assert mask[2]
    assert not mask[5]
    assert not mask[8]

