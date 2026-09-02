#!/usr/bin/env python3
"""Validate and summarize the paired multi-key by length variance pilot."""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from ai_watermarks_phase2.null_calibration import _tail_diagnostic, _wilson_interval
from ai_watermarks_phase2.smoke import load_json


def flatten(result: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in result["records"]:
        for prefix in record["prefix_results"]:
            for score in prefix["scores"]:
                rows.append(
                    {
                        "prompt_id": record["prompt_id"],
                        "category": record["category"],
                        "length": int(prefix["length"]),
                        "scheme": score["scheme"],
                        "key_id": score["key_id"],
                        "value": float(score["value"]),
                        "eligible_positions": int(score["eligible_positions"]),
                    }
                )
    return rows


def validate_result(result: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, bool]:
    config = result["config"]
    records = result["records"]
    target = int(config["selection"]["prompts"])
    prompt_records = load_json(Path(config["prompt_manifest"]))["records"][:target]
    expected_categories = Counter(item["category"] for item in prompt_records)
    lengths = config["generation"]["paired_prefix_lengths"]
    expected_scores = len(config["key_schedule"]["kgw"]) + len(
        config["key_schedule"]["synthid"]
    )
    expected_rows = len(records) * len(lengths) * expected_scores
    unique_cells = {
        (row["prompt_id"], row["length"], row["scheme"], row["key_id"])
        for row in rows
    }
    formula_consistent = True
    for record in records:
        for prefix in record["prefix_results"]:
            for score in prefix["scores"]:
                if score["scheme"] == "kgw":
                    eligible = int(score["eligible_positions"])
                    hits = int(score["green_tokens"])
                    gamma = float(score["greenlist_ratio"])
                    expected = (hits - gamma * eligible) / math.sqrt(
                        eligible * gamma * (1.0 - gamma)
                    )
                    formula_consistent &= expected == float(score["value"])
                    formula_consistent &= hits / eligible == float(
                        score["green_fraction"]
                    )
                else:
                    expected = int(score["g_value_sum"]) / (
                        int(score["eligible_positions"])
                        * int(score["watermarking_depth"])
                    )
                    formula_consistent &= expected == float(score["value"])
    return {
        "status_complete": result.get("status") == "variance_pilot_complete",
        "record_count": len(records) == target,
        "category_allocation": Counter(record["category"] for record in records)
        == expected_categories,
        "generated_lengths": all(
            len(record["token_ids"]) == int(config["generation"]["generated_tokens"])
            for record in records
        ),
        "prefix_shape": all(
            [item["length"] for item in record["prefix_results"]] == lengths
            and all(len(item["scores"]) == expected_scores for item in record["prefix_results"])
            for record in records
        ),
        "expected_score_rows": len(rows) == expected_rows,
        "unique_score_cells": len(unique_cells) == expected_rows,
        "finite_positive_scores": all(
            math.isfinite(row["value"]) and row["eligible_positions"] > 0 for row in rows
        ),
        "compact_formula_reconstruction": formula_consistent,
        "native_trace_audits": len(result.get("native_trace_audits", [])) == len(lengths)
        and all(
            audit["kgw_exact"] and audit["synthid_exact"]
            for audit in result.get("native_trace_audits", [])
        ),
    }


def cell_summaries(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(row["scheme"], row["key_id"], row["length"])].append(row)
    summaries = []
    for (scheme, key_id, length), items in sorted(grouped.items()):
        values = [item["value"] for item in items]
        eligible = [item["eligible_positions"] for item in items]
        mean = statistics.fmean(values)
        variance = statistics.variance(values)
        reference_mean = 0.0 if scheme == "kgw" else 0.5
        standard_error = math.sqrt(variance / len(values))
        summaries.append(
            {
                "scheme": scheme,
                "key_id": key_id,
                "length": length,
                "samples": len(values),
                "mean": mean,
                "sample_variance": variance,
                "reference_mean": reference_mean,
                "mean_deviation_standard_errors": (mean - reference_mean)
                / standard_error,
                "eligible_minimum": min(eligible),
                "eligible_median": statistics.median(eligible),
                "eligible_maximum": max(eligible),
                "tail_5_percent": _tail_diagnostic(values, 0.05),
                "tail_1_percent": _tail_diagnostic(values, 0.01),
                "category_means": {
                    category: statistics.fmean(
                        item["value"] for item in items if item["category"] == category
                    )
                    for category in sorted({item["category"] for item in items})
                },
            }
        )
    return summaries


def key_effects(cells: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for cell in cells:
        grouped[(cell["scheme"], cell["length"])].append(cell)
    results = []
    for (scheme, length), items in sorted(grouped.items()):
        means = [item["mean"] for item in items]
        results.append(
            {
                "scheme": scheme,
                "length": length,
                "keys": len(items),
                "mean_across_key_means": statistics.fmean(means),
                "between_key_standard_deviation": statistics.stdev(means),
                "minimum_key_mean": min(means),
                "maximum_key_mean": max(means),
                "key_mean_range": max(means) - min(means),
                "keys_beyond_three_standard_errors": sum(
                    abs(item["mean_deviation_standard_errors"]) > 3.0 for item in items
                ),
            }
        )
    return results


def theoretical_kgw_tails(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Measure realised FPR at the standard-normal KGW decision thresholds."""

    thresholds = {
        "one_sided_5_percent": (0.05, 1.6448536269514722),
        "one_sided_1_percent": (0.01, 2.3263478740408408),
    }
    grouped: dict[tuple[str, int], list[float]] = defaultdict(list)
    for row in rows:
        if row["scheme"] == "kgw":
            grouped[(row["key_id"], row["length"])].append(row["value"])

    results = []
    for (key_id, length), values in sorted(grouped.items()):
        diagnostics: dict[str, Any] = {}
        for label, (target, cutoff) in thresholds.items():
            exceedances = sum(value > cutoff for value in values)
            diagnostics[label] = {
                "target_fpr": target,
                "cutoff": cutoff,
                "decision_rule": "score_strictly_greater_than_cutoff",
                "exceedances": exceedances,
                "empirical_rate": exceedances / len(values),
                "wilson_95_percent": _wilson_interval(exceedances, len(values)),
            }
        results.append(
            {
                "key_id": key_id,
                "length": length,
                "samples": len(values),
                **diagnostics,
            }
        )
    return results


def pooled_threshold_key_distortion(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Quantify per-key FPR distortion when one pooled empirical cutoff is used."""

    grouped: dict[tuple[str, int], dict[str, list[float]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for row in rows:
        grouped[(row["scheme"], row["length"])][row["key_id"]].append(
            row["value"]
        )

    results = []
    for (scheme, length), by_key in sorted(grouped.items()):
        pooled = [value for values in by_key.values() for value in values]
        for target in (0.05, 0.01):
            pooled_tail = _tail_diagnostic(pooled, target)
            cutoff = float(pooled_tail["cutoff"])
            key_rates = []
            for key_id, values in sorted(by_key.items()):
                exceedances = sum(value > cutoff for value in values)
                key_rates.append(
                    {
                        "key_id": key_id,
                        "exceedances": exceedances,
                        "empirical_rate": exceedances / len(values),
                        "wilson_95_percent": _wilson_interval(
                            exceedances, len(values)
                        ),
                    }
                )
            rates = [item["empirical_rate"] for item in key_rates]
            results.append(
                {
                    "scheme": scheme,
                    "length": length,
                    "target_fpr": target,
                    "pooled_samples": len(pooled),
                    "pooled_cutoff": cutoff,
                    "pooled_exceedances": pooled_tail["exceedances"],
                    "pooled_empirical_rate": pooled_tail["empirical_rate"],
                    "minimum_key_rate": min(rates),
                    "maximum_key_rate": max(rates),
                    "key_rates": key_rates,
                }
            )
    return results


def precision_plan() -> dict[str, Any]:
    z = 1.959963984540054

    def planned(target: float, relative_half_width: float) -> dict[str, Any]:
        approximate = math.ceil(
            z * z * (1.0 - target) / (relative_half_width**2 * target)
        )
        rounded = int(math.ceil(approximate / 1000) * 1000)
        expected = rounded * target
        interval = _wilson_interval(round(expected), rounded)
        return {
            "target_fpr": target,
            "relative_half_width_goal": relative_half_width,
            "formula_sample_size": approximate,
            "recommended_rounded_sample_size": rounded,
            "expected_exceedances": expected,
            "wilson_interval_at_expected_count": interval,
        }

    false_positive_precision = [planned(0.01, 0.30), planned(0.001, 0.30)]
    effect_scenarios = []
    z_alpha = 1.959963984540054
    z_power = 0.8416212335729143
    for standardized_effect in (0.10, 0.20, 0.30, 0.50):
        samples = math.ceil(((z_alpha + z_power) / standardized_effect) ** 2)
        effect_scenarios.append(
            {
                "standardized_mean_effect": standardized_effect,
                "samples_for_80_percent_power_two_sided_5_percent_alpha": samples,
            }
        )
    return {
        "false_positive_precision": false_positive_precision,
        "mean_effect_power_scenarios": effect_scenarios,
        "positive_outcome_caveat": "Attack-condition power remains provisional until repeated watermarked positive and attack variances are measured.",
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = [
        "prompt_id",
        "category",
        "length",
        "scheme",
        "key_id",
        "value",
        "eligible_positions",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input", type=Path, default=Path("results/phase2-variance-pilot/run.json")
    )
    parser.add_argument(
        "--output", type=Path, default=Path("results/phase2-variance-pilot/analysis.json")
    )
    parser.add_argument(
        "--csv", type=Path, default=Path("results/phase2-variance-pilot/scores.csv")
    )
    args = parser.parse_args()

    result = load_json(args.input)
    rows = flatten(result)
    checks = validate_result(result, rows)
    cells = cell_summaries(rows)
    effects = key_effects(cells)
    report = {
        "schema_version": 1,
        "scope": "Phase 2 variance-pilot validation and analysis",
        "source": str(args.input),
        "validation": {
            "passed": all(checks.values()),
            "checks": checks,
        },
        "cell_summaries": cells,
        "key_effects": effects,
        "theoretical_kgw_tails": theoretical_kgw_tails(rows),
        "pooled_threshold_key_distortion": pooled_threshold_key_distortion(rows),
        "precision_plan": precision_plan(),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    write_csv(args.csv, rows)
    print(
        json.dumps(
            {
                "status": "analysis_complete",
                "validation_passed": report["validation"]["passed"],
                "score_rows": len(rows),
                "cells": len(cells),
                "output": str(args.output),
                "csv": str(args.csv),
            },
            indent=2,
        )
    )
    return 0 if report["validation"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
