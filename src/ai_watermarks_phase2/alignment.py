"""Token alignment utilities.

Only identical token IDs are mapped. This conservative rule avoids treating a
semantic substitute as a surviving watermark token. Deterministic attacks retain
ground-truth provenance and should use that map instead of inferred alignment.
"""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Sequence


def align_identical_tokens(
    original: Sequence[int], candidate: Sequence[int]
) -> tuple[int | None, ...]:
    """Map each candidate token to an identical original token when alignable.

    The mapping is monotonic and one-to-one within equal blocks. Inserted or
    substituted candidate tokens map to ``None``.
    """

    mapping: list[int | None] = [None] * len(candidate)
    matcher = SequenceMatcher(a=list(original), b=list(candidate), autojunk=False)
    for block in matcher.get_matching_blocks():
        for offset in range(block.size):
            mapping[block.b + offset] = block.a + offset
    return tuple(mapping)


def mapping_is_valid(
    original: Sequence[int],
    candidate: Sequence[int],
    candidate_to_original: Sequence[int | None],
) -> bool:
    """Check length, identity, bounds, uniqueness, and monotonicity."""

    if len(candidate) != len(candidate_to_original):
        return False
    seen: set[int] = set()
    last = -1
    for candidate_index, original_index in enumerate(candidate_to_original):
        if original_index is None:
            continue
        if original_index < 0 or original_index >= len(original):
            return False
        if original_index in seen or original_index <= last:
            return False
        if candidate[candidate_index] != original[original_index]:
            return False
        seen.add(original_index)
        last = original_index
    return True

