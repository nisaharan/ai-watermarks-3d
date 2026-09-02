from ai_watermarks_phase2.alignment import align_identical_tokens, mapping_is_valid
from ai_watermarks_phase2.attacks import delete_every, insert_every, substitute_every


def test_alignment_maps_equal_blocks_and_not_substitutions():
    original = [1, 2, 3, 4, 5]
    candidate = [1, 2, 99, 4, 5]
    mapping = align_identical_tokens(original, candidate)
    assert mapping == (0, 1, None, 3, 4)
    assert mapping_is_valid(original, candidate, mapping)


def test_invalid_non_monotonic_mapping_is_rejected():
    assert not mapping_is_valid([1, 2], [2, 1], [1, 0])


def test_inferred_alignment_exceeds_synthetic_gate():
    correct = 0
    total = 0
    for fixture in range(100):
        original = list(range(fixture * 1000, fixture * 1000 + 100))
        for attack in (
            delete_every(original, interval=7, offset=fixture % 7),
            substitute_every(
                original,
                interval=9,
                offset=fixture % 9,
                replacement_token=-1,
            ),
            insert_every(
                original,
                interval=11,
                offset=fixture % 11,
                inserted_token=-1,
            ),
        ):
            inferred = align_identical_tokens(original, attack.tokens)
            correct += sum(
                expected == observed
                for expected, observed in zip(
                    attack.candidate_to_original, inferred, strict=True
                )
            )
            total += len(inferred)
    assert correct / total >= 0.995

