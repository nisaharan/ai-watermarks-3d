#!/usr/bin/env python3
"""Validate a Phase 2 native smoke result without making benchmark claims."""

from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from ai_watermarks_phase2.trace_validation import trace_is_consistent


def load(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def native_value(record: dict[str, Any], scheme: str) -> float:
    return next(
        float(score["value"])
        for score in record["native_scores"]
        if score["scheme"] == scheme
    )


def attack_native_value(attack: dict[str, Any], scheme: str) -> float:
    return next(
        float(score["value"])
        for score in attack["native_scores"]
        if score["scheme"] == scheme
    )


def context_value(attack: dict[str, Any], rule: str) -> float:
    return next(
        float(item["survival_rate"])
        for item in attack["context_measurements"]
        if item["rule"] == rule
    )


def mean_by_condition(records: list[dict[str, Any]], scheme: str) -> dict[str, float]:
    grouped: dict[str, list[float]] = defaultdict(list)
    for record in records:
        grouped[record["condition"]].append(native_value(record, scheme))
    return {condition: statistics.fmean(values) for condition, values in grouped.items()}


def mean_attack_values(
    records: list[dict[str, Any]], *, condition: str, scheme: str, rule: str
) -> dict[str, dict[str, float]]:
    scores: dict[str, list[float]] = defaultdict(list)
    survival: dict[str, list[float]] = defaultdict(list)
    for record in records:
        if record["condition"] != condition:
            continue
        for attack in record["attacks"]:
            scores[attack["attack"]].append(attack_native_value(attack, scheme))
            survival[attack["attack"]].append(context_value(attack, rule))
    return {
        attack: {
            "mean_native_score": statistics.fmean(values),
            "mean_context_survival": statistics.fmean(survival[attack]),
        }
        for attack, values in scores.items()
    }


def validate(result: dict[str, Any], repeat: dict[str, Any] | None) -> dict[str, Any]:
    records = result["records"]
    counts = Counter(record["condition"] for record in records)
    kgw_means = mean_by_condition(records, "kgw")
    synthid_means = mean_by_condition(records, "synthid")
    kgw_attacks = mean_attack_values(
        records,
        condition="kgw",
        scheme="kgw",
        rule="kgw_selfhash_no_repeat",
    )
    synthid_attacks = mean_attack_values(
        records,
        condition="synthid",
        scheme="synthid",
        rule="synthid_repeated_context_mask",
    )

    checks = {
        "trace_schema_version": result.get("schema_version") == 2,
        "record_count": len(records) == 30,
        "balanced_conditions": counts
        == Counter({"unwatermarked": 10, "kgw": 10, "synthid": 10}),
        "declared_length": all(record["generated_tokens"] == 48 for record in records),
        "finite_native_scores": all(
            math.isfinite(float(score["value"]))
            for record in records
            for score in record["native_scores"]
        ),
        "positive_eligible_counts": all(
            int(score["eligible_positions"]) > 0
            for record in records
            for score in record["native_scores"]
        ),
        "native_traces_reconstruct_scores": all(
            trace_is_consistent(score, int(record["generated_tokens"]))
            for record in records
            for score in record["native_scores"]
        ),
        "attack_traces_reconstruct_scores": all(
            trace_is_consistent(score, int(attack["candidate_tokens"]))
            for record in records
            for attack in record["attacks"]
            for score in attack["native_scores"]
        ),
        "identity_survival": all(
            item["survival_rate"] == 1.0
            for record in records
            for attack in record["attacks"]
            if attack["attack"] == "identity"
            for item in attack["context_measurements"]
        ),
        "edits_reduce_context_survival": all(
            item["survival_rate"] < 1.0
            for record in records
            for attack in record["attacks"]
            if attack["attack"] != "identity"
            for item in attack["context_measurements"]
        ),
        "kgw_signal_separation": kgw_means["kgw"] - kgw_means["unwatermarked"]
        > 2.0,
        "synthid_signal_separation": synthid_means["synthid"]
        - synthid_means["unwatermarked"]
        > 0.05,
        "kgw_edit_direction": all(
            kgw_attacks[name]["mean_native_score"]
            < kgw_attacks["identity"]["mean_native_score"]
            for name in ("substitute_every", "delete_every", "truncate")
        ),
        "synthid_edit_direction": all(
            synthid_attacks[name]["mean_native_score"]
            < synthid_attacks["identity"]["mean_native_score"]
            for name in ("substitute_every", "delete_every", "insert_every")
        ),
        "repeat_records_exact": repeat is not None
        and result["records"] == repeat["records"],
        "repeat_environment_exact": repeat is not None
        and result["environment"] == repeat["environment"],
    }
    return {
        "scope": "Phase 2 smoke validation; not a benchmark result",
        "passed": all(checks.values()),
        "checks": checks,
        "condition_counts": dict(sorted(counts.items())),
        "native_score_means": {"kgw": kgw_means, "synthid": synthid_means},
        "attack_means": {"kgw": kgw_attacks, "synthid": synthid_attacks},
        "environment": result["environment"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result", type=Path)
    parser.add_argument("--repeat", type=Path)
    args = parser.parse_args()
    report = validate(load(args.result), load(args.repeat) if args.repeat else None)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
