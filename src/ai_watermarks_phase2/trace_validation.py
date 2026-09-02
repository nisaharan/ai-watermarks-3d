"""Pure helpers for reconstructing native scores from exported traces."""

from __future__ import annotations

import math
from typing import Any


def trace_reconstruction(score: dict[str, Any]) -> tuple[int, float]:
    """Reconstruct a native statistic only from its eligible trace rows."""

    eligible = [row for row in score["position_traces"] if row["eligible"]]
    if score["scheme"] == "kgw":
        green_hits = [row["values"]["green_hit"] for row in eligible]
        if any(not isinstance(hit, bool) for hit in green_hits):
            raise ValueError("KGW eligible rows must contain boolean green hits")
        hits = sum(green_hits)
        if hits != int(score["auxiliary"]["green_tokens"]):
            raise ValueError("KGW trace and reported green-token count disagree")
        reported_fraction = float(score["auxiliary"]["green_fraction"])
        reconstructed_fraction = hits / len(eligible) if eligible else float("nan")
        if not _same_float(reconstructed_fraction, reported_fraction):
            raise ValueError("KGW trace and reported green fraction disagree")
        greenlist_ratio = float(score["auxiliary"]["greenlist_ratio"])
        if not 0.0 < greenlist_ratio < 1.0:
            raise ValueError("KGW green-list ratio must be strictly between zero and one")
        if not eligible:
            return 0, float("nan")
        value = (hits - greenlist_ratio * len(eligible)) / math.sqrt(
            len(eligible) * greenlist_ratio * (1 - greenlist_ratio)
        )
        return len(eligible), value
    if score["scheme"] != "synthid":
        raise ValueError(f"Unsupported trace scheme: {score['scheme']}")
    depth = int(score["auxiliary"]["watermarking_depth"])
    if depth <= 0:
        raise ValueError("SynthID watermarking depth must be positive")
    g_values = [row["values"]["g_values"] for row in eligible]
    if any(
        not isinstance(values, list)
        or len(values) != depth
        or any(type(value) is not int or value not in (0, 1) for value in values)
        for values in g_values
    ):
        raise ValueError("SynthID eligible rows must contain one binary value per depth")
    if not eligible:
        return 0, float("nan")
    value = sum(map(sum, g_values)) / (len(eligible) * depth)
    return len(eligible), value


def _same_float(left: float, right: float) -> bool:
    return left == right or (math.isnan(left) and math.isnan(right))


def trace_is_consistent(score: dict[str, Any], token_count: int) -> bool:
    """Check trace shape, eligibility metadata, and exact score reconstruction."""

    traces = score.get("position_traces", [])
    if len(traces) != token_count:
        return False
    if [row["position"] for row in traces] != list(range(token_count)):
        return False
    if any(bool(row["eligible"]) == bool(row["exclusion_reason"]) for row in traces):
        return False
    try:
        eligible, value = trace_reconstruction(score)
        reported_eligible = int(score["eligible_positions"])
        reported = float(score["value"])
    except (KeyError, TypeError, ValueError, OverflowError, ZeroDivisionError):
        return False
    return eligible == reported_eligible and (
        _same_float(value, reported)
        or math.isclose(value, reported, rel_tol=0.0, abs_tol=1e-12)
    )
