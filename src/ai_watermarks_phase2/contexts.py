"""Scheme-aware effective context-survival measurement."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Sequence

from .alignment import mapping_is_valid

Deduplication = Literal["none", "context", "window"]


@dataclass(frozen=True)
class ContextRule:
    """Detector window and repeated-context semantics.

    ``window_size`` includes the scored target token. For Transformers KGW
    SelfHash with ``context_width=4``, the native detector uses a four-token
    window. For SynthID-Text with ``ngram_len=5``, it uses a five-token window
    and masks repeated four-token contexts.
    """

    name: str
    window_size: int
    deduplicate: Deduplication = "none"

    def __post_init__(self) -> None:
        if self.window_size < 1:
            raise ValueError("window_size must be positive")
        if self.deduplicate not in {"none", "context", "window"}:
            raise ValueError(f"Unsupported deduplication rule: {self.deduplicate}")


@dataclass(frozen=True)
class PositionTrace:
    candidate_position: int
    original_position: int | None
    candidate_eligible: bool
    original_eligible: bool
    survives: bool


@dataclass(frozen=True)
class SurvivalMeasurement:
    rule: str
    original_length: int
    candidate_length: int
    original_eligible: int
    candidate_eligible: int
    effective_surviving: int
    survival_rate: float
    traces: tuple[PositionTrace, ...]


def eligible_positions(tokens: Sequence[int], rule: ContextRule) -> tuple[bool, ...]:
    """Return native-style eligibility by position for the declared rule."""

    eligible = [False] * len(tokens)
    seen: set[tuple[int, ...]] = set()
    for position in range(rule.window_size - 1, len(tokens)):
        window = tuple(tokens[position - rule.window_size + 1 : position + 1])
        if rule.deduplicate == "none":
            key = None
        elif rule.deduplicate == "context":
            key = window[:-1]
        else:
            key = window
        if key is not None and key in seen:
            continue
        eligible[position] = True
        if key is not None:
            seen.add(key)
    return tuple(eligible)


def measure_context_survival(
    original: Sequence[int],
    candidate: Sequence[int],
    candidate_to_original: Sequence[int | None],
    rule: ContextRule,
) -> SurvivalMeasurement:
    """Measure exact survival of aligned eligible scoring windows."""

    if not mapping_is_valid(original, candidate, candidate_to_original):
        raise ValueError("candidate_to_original is not a valid identity alignment")

    original_eligible = eligible_positions(original, rule)
    candidate_eligible = eligible_positions(candidate, rule)
    traces: list[PositionTrace] = []
    effective = 0

    for candidate_position in range(len(candidate)):
        original_position = candidate_to_original[candidate_position]
        original_is_eligible = (
            original_position is not None and original_eligible[original_position]
        )
        survives = False
        if candidate_eligible[candidate_position] and original_is_eligible:
            candidate_start = candidate_position - rule.window_size + 1
            original_start = original_position - rule.window_size + 1
            if candidate_start >= 0 and original_start >= 0:
                mapped_window = candidate_to_original[
                    candidate_start : candidate_position + 1
                ]
                expected = tuple(range(original_start, original_position + 1))
                candidate_window = tuple(
                    candidate[candidate_start : candidate_position + 1]
                )
                original_window = tuple(original[original_start : original_position + 1])
                survives = tuple(mapped_window) == expected and candidate_window == original_window
        if survives:
            effective += 1
        traces.append(
            PositionTrace(
                candidate_position=candidate_position,
                original_position=original_position,
                candidate_eligible=candidate_eligible[candidate_position],
                original_eligible=bool(original_is_eligible),
                survives=survives,
            )
        )

    denominator = sum(original_eligible)
    return SurvivalMeasurement(
        rule=rule.name,
        original_length=len(original),
        candidate_length=len(candidate),
        original_eligible=denominator,
        candidate_eligible=sum(candidate_eligible),
        effective_surviving=effective,
        survival_rate=effective / denominator if denominator else 0.0,
        traces=tuple(traces),
    )

