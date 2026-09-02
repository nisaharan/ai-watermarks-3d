from ai_watermarks_phase2.attacks import (
    delete_every,
    identity,
    insert_every,
    replace_span,
    substitute_every,
    truncate,
)


def test_all_deterministic_attacks_emit_valid_provenance():
    original = list(range(20))
    attacks = [
        identity(original),
        delete_every(original, interval=5),
        substitute_every(original, interval=5, replacement_token=99),
        insert_every(original, interval=5, inserted_token=99),
        truncate(original, keep=8),
        replace_span(original, start=5, stop=10, replacement=[91, 92]),
    ]
    for attack in attacks:
        attack.validate_against(original)


def test_identical_substitution_preserves_token_provenance():
    original = [7, 8, 9]
    attack = substitute_every(original, interval=2, replacement_token=7)

    assert attack.tokens == (7, 8, 7)
    assert attack.candidate_to_original == (0, 1, None)
