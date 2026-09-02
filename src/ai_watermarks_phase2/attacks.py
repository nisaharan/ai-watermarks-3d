"""Deterministic token attacks with exact provenance maps."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .alignment import mapping_is_valid


@dataclass(frozen=True)
class AttackResult:
    name: str
    parameters: dict[str, int | float | str]
    tokens: tuple[int, ...]
    candidate_to_original: tuple[int | None, ...]

    def validate_against(self, original: Sequence[int]) -> None:
        if not mapping_is_valid(original, self.tokens, self.candidate_to_original):
            raise ValueError(f"Invalid provenance map for attack {self.name!r}")


def identity(tokens: Sequence[int]) -> AttackResult:
    result = AttackResult(
        name="identity",
        parameters={},
        tokens=tuple(tokens),
        candidate_to_original=tuple(range(len(tokens))),
    )
    result.validate_against(tokens)
    return result


def delete_every(tokens: Sequence[int], *, interval: int, offset: int = 0) -> AttackResult:
    _positive_interval(interval)
    kept = [i for i in range(len(tokens)) if (i - offset) % interval != 0]
    result = AttackResult(
        name="delete_every",
        parameters={"interval": interval, "offset": offset},
        tokens=tuple(tokens[i] for i in kept),
        candidate_to_original=tuple(kept),
    )
    result.validate_against(tokens)
    return result


def substitute_every(
    tokens: Sequence[int], *, interval: int, replacement_token: int, offset: int = 0
) -> AttackResult:
    _positive_interval(interval)
    attacked: list[int] = []
    mapping: list[int | None] = []
    for i, token in enumerate(tokens):
        if (i - offset) % interval == 0:
            attacked.append(replacement_token)
            # A replacement can be a token-level no-op.  Context survival is
            # defined over token IDs, so preserve provenance when the requested
            # replacement is identical to the source token.
            mapping.append(i if replacement_token == token else None)
        else:
            attacked.append(token)
            mapping.append(i)
    result = AttackResult(
        name="substitute_every",
        parameters={
            "interval": interval,
            "offset": offset,
            "replacement_token": replacement_token,
        },
        tokens=tuple(attacked),
        candidate_to_original=tuple(mapping),
    )
    result.validate_against(tokens)
    return result


def insert_every(
    tokens: Sequence[int], *, interval: int, inserted_token: int, offset: int = 0
) -> AttackResult:
    _positive_interval(interval)
    attacked: list[int] = []
    mapping: list[int | None] = []
    for i, token in enumerate(tokens):
        if (i - offset) % interval == 0:
            attacked.append(inserted_token)
            mapping.append(None)
        attacked.append(token)
        mapping.append(i)
    result = AttackResult(
        name="insert_every",
        parameters={
            "interval": interval,
            "offset": offset,
            "inserted_token": inserted_token,
        },
        tokens=tuple(attacked),
        candidate_to_original=tuple(mapping),
    )
    result.validate_against(tokens)
    return result


def truncate(tokens: Sequence[int], *, keep: int) -> AttackResult:
    if keep < 0:
        raise ValueError("keep must be non-negative")
    kept = min(keep, len(tokens))
    result = AttackResult(
        name="truncate",
        parameters={"keep": keep},
        tokens=tuple(tokens[:kept]),
        candidate_to_original=tuple(range(kept)),
    )
    result.validate_against(tokens)
    return result


def replace_span(
    tokens: Sequence[int], *, start: int, stop: int, replacement: Sequence[int]
) -> AttackResult:
    if not 0 <= start <= stop <= len(tokens):
        raise ValueError("span must satisfy 0 <= start <= stop <= len(tokens)")
    attacked = tuple(tokens[:start]) + tuple(replacement) + tuple(tokens[stop:])
    mapping = (
        tuple(range(start))
        + (None,) * len(replacement)
        + tuple(range(stop, len(tokens)))
    )
    result = AttackResult(
        name="replace_span",
        parameters={"start": start, "stop": stop, "replacement_length": len(replacement)},
        tokens=attacked,
        candidate_to_original=mapping,
    )
    result.validate_against(tokens)
    return result


def _positive_interval(interval: int) -> None:
    if interval <= 0:
        raise ValueError("interval must be positive")
