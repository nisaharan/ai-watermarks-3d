#!/usr/bin/env python3
"""Map the development-only null-margin versus positive-sensitivity frontier."""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Any

from ai_watermarks_phase2.calibration_gate import (
    binomial_cdf,
    grouped_scores,
    maximum_passing_exceedances,
    threshold_candidate,
)
from ai_watermarks_phase2.confirmatory_null import iter_sharded_records
from ai_watermarks_phase2.positive_sensitivity import iter_records
from ai_watermarks_phase2.smoke import load_json
from ai_watermarks_phase2.variance_pilot import file_sha256, write_result


DESIGN_FPRS = (0.005, 0.0055, 0.006, 0.0065, 0.007, 0.0075, 0.008)


def operational_thresholds(
    grouped: dict[tuple[str, str, int], list[float]], allowed: int
) -> dict[tuple[str, str, int], float]:
    candidates = {
        cell: threshold_candidate(values, allowed) for cell, values in grouped.items()
    }
    output: dict[tuple[str, str, int], float] = {}
    for length in (128, 256, 512):
        for key_index in range(10):
            key_id = f"kgw-{key_index:02d}"
            output[("kgw", key_id, length)] = candidates[("kgw", key_id, length)]
        shared = max(
            candidates[("synthid", f"synthid-{key_index:02d}", length)]
            for key_index in range(10)
        )
        for key_index in range(10):
            output[("synthid", f"synthid-{key_index:02d}", length)] = shared
    return output


def positive_scores(run_dir: Path) -> dict[tuple[str, str, int], list[float]]:
    output: dict[tuple[str, str, int], list[float]] = {}
    for record in iter_records(run_dir):
        for prefix in record["prefix_results"]:
            cell = (record["scheme"], record["key_id"], int(prefix["length"]))
            output.setdefault(cell, []).append(float(prefix["score"]["value"]))
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path, default=Path("configs/phase2-v2-positive-sensitivity.json")
    )
    parser.add_argument(
        "--output", type=Path, default=Path("results/phase2-v2-positive-sensitivity/margin-frontier.json")
    )
    args = parser.parse_args(argv)
    if args.output.exists():
        raise FileExistsError(f"Refusing to replace margin frontier: {args.output}")
    config = load_json(args.config)
    settings = config["provisional_thresholds"]
    if settings.get("confirmation_scores_used") is not False:
        raise ValueError("Confirmation scores are prohibited")
    calibration_run = Path(settings["source_run"])
    positive_run = Path("results/phase2-v2-positive-sensitivity/run")
    positive_metadata = load_json(positive_run / "run.json")
    if positive_metadata.get("status") != "positive_sensitivity_complete":
        raise ValueError("Positive-sensitivity run is incomplete")
    calibration = grouped_scores(iter_sharded_records(calibration_run))
    positives = positive_scores(positive_run)
    if len(calibration) != 60 or len(positives) != 60:
        raise ValueError("Expected 60 calibration and 60 positive cells")
    if any(len(values) != 5000 for values in calibration.values()):
        raise ValueError("Calibration cells are incomplete")
    if any(len(values) != 50 for values in positives.values()):
        raise ValueError("Positive cells are incomplete")

    cells = int(settings["primary_cells"])
    familywise_alpha = 1.0 - float(settings["familywise_confidence"])
    confirmation_samples = 20000
    confirmation_maximum = 156
    screen_minimum = int(config["screen"]["minimum_detections_per_cell"])
    scenarios: list[dict[str, Any]] = []
    for design_fpr in DESIGN_FPRS:
        allowed = maximum_passing_exceedances(
            samples=5000,
            target_fpr=design_fpr,
            familywise_alpha=familywise_alpha,
            cells=cells,
        )
        thresholds = operational_thresholds(calibration, allowed)
        cell_results = []
        for cell, values in sorted(positives.items()):
            threshold = thresholds[cell]
            detections = sum(value > threshold for value in values)
            cell_results.append(
                {
                    "scheme": cell[0],
                    "key_id": cell[1],
                    "length": cell[2],
                    "threshold": threshold,
                    "strict_detections": detections,
                    "detection_rate": detections / len(values),
                    "screen_passed": detections >= screen_minimum,
                }
            )
        single_cell_power = binomial_cdf(
            confirmation_maximum, confirmation_samples, design_fpr
        )
        conservative_family_power = max(0.0, 1.0 - cells * (1.0 - single_cell_power))
        failed = [row for row in cell_results if not row["screen_passed"]]
        scenarios.append(
            {
                "design_fpr": design_fpr,
                "calibration_maximum_strict_exceedances_at_n5000": allowed,
                "calibration_empirical_tail_limit": allowed / 5000,
                "failed_positive_screen_cells": len(failed),
                "minimum_positive_detection_rate": min(
                    row["detection_rate"] for row in cell_results
                ),
                "median_positive_detection_rate": statistics.median(
                    row["detection_rate"] for row in cell_results
                ),
                "single_cell_confirmation_pass_power_if_true_rate_equals_design_fpr": single_cell_power,
                "conservative_60_cell_confirmation_pass_power_if_true_rates_equal_design_fpr": conservative_family_power,
                "failed_cells": failed,
                "cell_results": cell_results,
            }
        )
    eligible = [
        row
        for row in scenarios
        if row["failed_positive_screen_cells"] == 0
        and row[
            "conservative_60_cell_confirmation_pass_power_if_true_rates_equal_design_fpr"
        ]
        >= 0.95
    ]
    result = {
        "schema_version": 1,
        "status": "development_margin_frontier_complete",
        "scope": "Post-screen planning diagnostic; not independent validation and not a confirmatory result",
        "inputs": {
            "v1_calibration_only": True,
            "v1_confirmation_scores_used": False,
            "completed_positive_pilot_used": True,
            "config_sha256": file_sha256(args.config),
            "calibration_run": str(calibration_run),
            "positive_run": str(positive_run),
            "analysis_source_sha256": file_sha256(Path(__file__)),
        },
        "fixed_screen": config["screen"],
        "confirmation_planning": {
            "samples_per_cell": confirmation_samples,
            "maximum_strict_exceedances": confirmation_maximum,
            "cells": cells,
            "target_fpr": 0.01,
        },
        "scenarios": scenarios,
        "lowest_grid_margin_meeting_both_development_criteria": (
            eligible[0]["design_fpr"] if eligible else None
        ),
        "interpretation_boundary": {
            "candidate_selection_is_post_screen": True,
            "fresh_positive_validation_required_before_protocol_freeze": True,
            "replacement_null_generation_authorized": False,
            "attacks_authorized": False,
        },
    }
    write_result(args.output, result)
    print(
        json.dumps(
            {
                "status": result["status"],
                "candidate": result["lowest_grid_margin_meeting_both_development_criteria"],
                "output": str(args.output),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
