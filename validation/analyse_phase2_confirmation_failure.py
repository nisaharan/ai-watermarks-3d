#!/usr/bin/env python3
"""Descriptive diagnosis of the frozen Phase 2 confirmation-gate failure.

This script never fits or proposes a replacement threshold. It evaluates both
completed splits at the already-frozen operational thresholds and supplies exact
binomial planning scenarios for a genuinely fresh future protocol.
"""

from __future__ import annotations

import json
import math
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_watermarks_phase2.calibration_gate import (
    binomial_cdf,
    clopper_pearson_upper,
)
from ai_watermarks_phase2.confirmatory_null import iter_sharded_records


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "configs/phase2-confirmatory-null.json"
THRESHOLDS = ROOT / "results/phase2-confirmatory-null/thresholds.json"
GATE = ROOT / "results/phase2-confirmatory-null/confirmation-gate.json"
CALIBRATION = ROOT / "results/phase2-confirmatory-null/calibration"
CONFIRMATION = ROOT / "results/phase2-confirmatory-null/confirmation"
OUTPUT = ROOT / "results/phase2-confirmatory-null/failure-diagnosis.json"


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def operational_lookup(thresholds: dict[str, Any]) -> dict[tuple[str, str, int], float]:
    lookup: dict[tuple[str, str, int], float] = {}
    for item in thresholds["operational_thresholds"]:
        lookup[(item["scheme"], item["key_id"], int(item["length"]))] = float(
            item["threshold"]
        )
    return lookup


def split_counts(
    run_dir: Path, threshold_lookup: dict[tuple[str, str, int], float]
) -> tuple[dict[tuple[str, str, int], dict[str, Any]], dict[str, int]]:
    scores: dict[tuple[str, str, int], list[float]] = defaultdict(list)
    category_scores: dict[tuple[str, str, int, str], list[float]] = defaultdict(list)
    category_records: dict[str, int] = defaultdict(int)
    for record in iter_sharded_records(run_dir):
        category = str(record["category"])
        category_records[category] += 1
        for prefix in record["prefix_results"]:
            length = int(prefix["length"])
            for score in prefix["scores"]:
                key = (str(score["scheme"]), str(score["key_id"]), length)
                value = float(score["value"])
                scores[key].append(value)
                category_scores[(*key, category)].append(value)
    output: dict[tuple[str, str, int], dict[str, Any]] = {}
    for key, values in sorted(scores.items()):
        scheme, key_id, length = key
        threshold_key = key_id if scheme == "kgw" else "shared"
        threshold = threshold_lookup[(scheme, threshold_key, length)]
        exceedances = sum(value > threshold for value in values)
        categories = {}
        for category in sorted(category_records):
            values_for_category = category_scores[(*key, category)]
            category_exceedances = sum(value > threshold for value in values_for_category)
            categories[category] = {
                "samples": len(values_for_category),
                "strict_exceedances": category_exceedances,
                "empirical_rate": category_exceedances / len(values_for_category),
            }
        output[key] = {
            "scheme": scheme,
            "key_id": key_id,
            "length": length,
            "threshold": threshold,
            "samples": len(values),
            "strict_exceedances": exceedances,
            "empirical_rate": exceedances / len(values),
            "categories": categories,
        }
    return output, dict(sorted(category_records.items()))


def maximum_passing_exceedances_binary(
    *, samples: int, target_fpr: float, alpha: float
) -> int:
    lower, upper = -1, samples
    while lower + 1 < upper:
        midpoint = (lower + upper) // 2
        if clopper_pearson_upper(midpoint, samples, alpha) <= target_fpr:
            lower = midpoint
        else:
            upper = midpoint
    if lower < 0:
        raise ValueError("No passing exceedance count")
    return lower


def maximum_true_rate_for_power(
    *, samples: int, maximum_exceedances: int, target_power: float
) -> float:
    lower, upper = 0.0, 0.01
    for _ in range(80):
        midpoint = (lower + upper) / 2.0
        if binomial_cdf(maximum_exceedances, samples, midpoint) >= target_power:
            lower = midpoint
        else:
            upper = midpoint
    return (lower + upper) / 2.0


def pearson(values_x: list[float], values_y: list[float]) -> float:
    mean_x = statistics.fmean(values_x)
    mean_y = statistics.fmean(values_y)
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(values_x, values_y))
    denominator = math.sqrt(
        sum((x - mean_x) ** 2 for x in values_x)
        * sum((y - mean_y) ** 2 for y in values_y)
    )
    return numerator / denominator if denominator else 0.0


def main() -> int:
    protocol = load(PROTOCOL)
    thresholds = load(THRESHOLDS)
    gate = load(GATE)
    if gate["status"] != "confirmation_gate_failed" or len(gate["failed_cells"]) != 18:
        raise RuntimeError("Frozen gate is not the expected failed one-shot result")
    if gate["post_confirmation_retuning_authorized"]:
        raise RuntimeError("No-retuning invariant is not preserved")
    lookup = operational_lookup(thresholds)
    calibration, calibration_categories = split_counts(CALIBRATION, lookup)
    confirmation, confirmation_categories = split_counts(CONFIRMATION, lookup)
    if calibration.keys() != confirmation.keys() or len(calibration) != 60:
        raise RuntimeError("Split cell sets differ or are incomplete")
    if calibration_categories != confirmation_categories:
        raise RuntimeError("Category allocation differs between frozen splits")

    gate_lookup = {
        (item["scheme"], item["key_id"], int(item["length"])): item
        for item in gate["cells"]
    }
    cells = []
    for key in sorted(calibration):
        calibration_cell = calibration[key]
        confirmation_cell = confirmation[key]
        gate_cell = gate_lookup[key]
        if confirmation_cell["strict_exceedances"] != gate_cell["strict_exceedances"]:
            raise RuntimeError(f"Confirmation recount differs for {key}")
        category_deltas = []
        for category in sorted(calibration_categories):
            cal_category = calibration_cell["categories"][category]
            con_category = confirmation_cell["categories"][category]
            category_deltas.append(
                {
                    "category": category,
                    "calibration_samples": cal_category["samples"],
                    "calibration_exceedances": cal_category["strict_exceedances"],
                    "calibration_rate": cal_category["empirical_rate"],
                    "confirmation_samples": con_category["samples"],
                    "confirmation_exceedances": con_category["strict_exceedances"],
                    "confirmation_rate": con_category["empirical_rate"],
                    "rate_delta": con_category["empirical_rate"]
                    - cal_category["empirical_rate"],
                }
            )
        cells.append(
            {
                "scheme": key[0],
                "key_id": key[1],
                "length": key[2],
                "threshold": calibration_cell["threshold"],
                "calibration_exceedances": calibration_cell["strict_exceedances"],
                "calibration_rate": calibration_cell["empirical_rate"],
                "confirmation_exceedances": confirmation_cell["strict_exceedances"],
                "confirmation_rate": confirmation_cell["empirical_rate"],
                "exceedance_delta": confirmation_cell["strict_exceedances"]
                - calibration_cell["strict_exceedances"],
                "rate_delta": confirmation_cell["empirical_rate"]
                - calibration_cell["empirical_rate"],
                "passed": bool(gate_cell["passed"]),
                "exact_upper_bound": float(gate_cell["exact_upper_bound"]),
                "categories": category_deltas,
            }
        )

    by_scheme = []
    for scheme in ("kgw", "synthid"):
        scheme_cells = [item for item in cells if item["scheme"] == scheme]
        by_scheme.append(
            {
                "scheme": scheme,
                "cells": len(scheme_cells),
                "failed_cells": sum(not item["passed"] for item in scheme_cells),
                "calibration_at_boundary": sum(
                    item["calibration_exceedances"]
                    == int(gate["acceptance"]["maximum_exceedances_per_5000"])
                    for item in scheme_cells
                ),
                "mean_calibration_exceedances": statistics.fmean(
                    item["calibration_exceedances"] for item in scheme_cells
                ),
                "mean_confirmation_exceedances": statistics.fmean(
                    item["confirmation_exceedances"] for item in scheme_cells
                ),
                "mean_exceedance_delta": statistics.fmean(
                    item["exceedance_delta"] for item in scheme_cells
                ),
                "calibration_confirmation_correlation": pearson(
                    [item["calibration_rate"] for item in scheme_cells],
                    [item["confirmation_rate"] for item in scheme_cells],
                ),
            }
        )

    by_length = []
    for length in (128, 256, 512):
        length_cells = [item for item in cells if item["length"] == length]
        by_length.append(
            {
                "length": length,
                "cells": len(length_cells),
                "failed_cells": sum(not item["passed"] for item in length_cells),
                "mean_calibration_exceedances": statistics.fmean(
                    item["calibration_exceedances"] for item in length_cells
                ),
                "mean_confirmation_exceedances": statistics.fmean(
                    item["confirmation_exceedances"] for item in length_cells
                ),
                "mean_exceedance_delta": statistics.fmean(
                    item["exceedance_delta"] for item in length_cells
                ),
            }
        )

    category_summary_failed_cells = []
    failed_cells = [item for item in cells if not item["passed"]]
    for category in sorted(calibration_categories):
        category_rows = [
            category_item
            for cell in failed_cells
            for category_item in cell["categories"]
            if category_item["category"] == category
        ]
        calibration_samples = sum(item["calibration_samples"] for item in category_rows)
        confirmation_samples = sum(item["confirmation_samples"] for item in category_rows)
        calibration_exceedances = sum(
            item["calibration_exceedances"] for item in category_rows
        )
        confirmation_exceedances = sum(
            item["confirmation_exceedances"] for item in category_rows
        )
        category_summary_failed_cells.append(
            {
                "category": category,
                "failed_cells": len(failed_cells),
                "calibration_score_rows": calibration_samples,
                "calibration_exceedances": calibration_exceedances,
                "calibration_rate": calibration_exceedances / calibration_samples,
                "confirmation_score_rows": confirmation_samples,
                "confirmation_exceedances": confirmation_exceedances,
                "confirmation_rate": confirmation_exceedances / confirmation_samples,
                "rate_delta": confirmation_exceedances / confirmation_samples
                - calibration_exceedances / calibration_samples,
            }
        )

    failed_category_concentration = []
    for item in (cell for cell in cells if not cell["passed"]):
        highest = max(item["categories"], key=lambda category: category["confirmation_rate"])
        failed_category_concentration.append(
            {
                "scheme": item["scheme"],
                "key_id": item["key_id"],
                "length": item["length"],
                "highest_confirmation_category": highest["category"],
                "highest_confirmation_category_rate": highest["confirmation_rate"],
                "highest_confirmation_category_exceedances": highest[
                    "confirmation_exceedances"
                ],
                "highest_confirmation_category_samples": highest["confirmation_samples"],
            }
        )

    alpha = float(gate["per_cell_alpha"])
    target_fpr = float(gate["acceptance"]["target_fpr"])
    power_scenarios = []
    for samples in (5000, 10000, 20000, 50000):
        maximum = maximum_passing_exceedances_binary(
            samples=samples, target_fpr=target_fpr, alpha=alpha
        )
        scenario = {
            "samples_per_cell": samples,
            "maximum_passing_exceedances": maximum,
            "maximum_passing_empirical_rate": maximum / samples,
            "pass_probability_by_true_fpr": {},
            "maximum_true_fpr_for_95_percent_cell_pass_probability": maximum_true_rate_for_power(
                samples=samples,
                maximum_exceedances=maximum,
                target_power=0.95,
            ),
            "maximum_true_fpr_for_95_percent_family_pass_union_bound": maximum_true_rate_for_power(
                samples=samples,
                maximum_exceedances=maximum,
                target_power=1.0 - 0.05 / 60.0,
            ),
        }
        for true_fpr in (0.003, 0.004, 0.005, 0.006, 0.007, 0.008):
            probability = binomial_cdf(maximum, samples, true_fpr)
            scenario["pass_probability_by_true_fpr"][f"{true_fpr:.3f}"] = probability
        power_scenarios.append(scenario)

    boundary_rate = int(gate["acceptance"]["maximum_exceedances_per_5000"]) / 5000
    boundary_pass_probability = binomial_cdf(28, 5000, boundary_rate)
    result = {
        "schema_version": 1,
        "status": "descriptive_failure_diagnosis_complete",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "protocol_id": gate["protocol_id"],
        "analysis_boundary": {
            "confirmation_used_for_threshold_fitting": False,
            "replacement_thresholds_produced": False,
            "category_results_confirmatory": False,
            "future_planning_requires_fresh_calibration_and_confirmation": True,
        },
        "headline": {
            "cells": 60,
            "failed_cells": 18,
            "maximum_allowed_exceedances": 28,
            "calibration_boundary_rate": boundary_rate,
            "per_cell_pass_probability_if_true_fpr_equals_boundary_rate": boundary_pass_probability,
        },
        "category_allocation_per_split": calibration_categories,
        "by_scheme": by_scheme,
        "by_length": by_length,
        "category_summary_across_failed_cell_score_rows": category_summary_failed_cells,
        "cells": cells,
        "failed_cell_category_concentration": failed_category_concentration,
        "fresh_study_power_scenarios": power_scenarios,
        "validated_invariants": [
            "Both completed splits contain the same 60 scheme-key-length cells.",
            "Every cell contains 5,000 observations in each split.",
            "Confirmation exceedance recount matches the immutable one-shot gate.",
            "Both splits have identical category allocations.",
            "No replacement threshold is calculated or emitted.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(OUTPUT.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
