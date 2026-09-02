"""Deterministic, auditable key schedules for the Phase 2 variance pilot."""

from __future__ import annotations

import hashlib
import math

SCHEDULE_SEED = "phase2-key-schedule-v1"
PUBLIC_KGW_KEY = 15485863
PUBLIC_SYNTHID_KEYS = (654, 400, 836, 123, 340, 443, 597, 160, 57)


def is_prime(value: int) -> bool:
    if value < 2:
        return False
    if value % 2 == 0:
        return value == 2
    for divisor in range(3, math.isqrt(value) + 1, 2):
        if value % divisor == 0:
            return False
    return True


def derive_kgw_key(condition: int) -> int:
    if condition == 0:
        return PUBLIC_KGW_KEY
    digest = hashlib.sha256(f"{SCHEDULE_SEED}:kgw:{condition}".encode()).digest()
    candidate = 10_000_001 + int.from_bytes(digest[:4], "big") % 1_900_000_000
    candidate |= 1
    while not is_prime(candidate):
        candidate += 2
    return candidate


def derive_synthid_keys(condition: int, depth: int = 9) -> tuple[int, ...]:
    if condition == 0:
        if depth != len(PUBLIC_SYNTHID_KEYS):
            raise ValueError("The public SynthID fixture has depth nine")
        return PUBLIC_SYNTHID_KEYS
    return tuple(
        1
        + int.from_bytes(
            hashlib.sha256(
                f"{SCHEDULE_SEED}:synthid:{condition}:{index}".encode()
            ).digest()[:4],
            "big",
        )
        % 2_000_000_000
        for index in range(depth)
    )


def derive_schedule(conditions: int = 10) -> dict[str, list[object]]:
    return {
        "kgw": [derive_kgw_key(index) for index in range(conditions)],
        "synthid": [list(derive_synthid_keys(index)) for index in range(conditions)],
    }
