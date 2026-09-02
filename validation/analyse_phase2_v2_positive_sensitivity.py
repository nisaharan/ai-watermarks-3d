#!/usr/bin/env python3
"""Evaluate the predeclared v2 watermarked-positive sensitivity screen."""

from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from ai_watermarks_phase2.calibration_gate import clopper_pearson_upper
from ai_watermarks_phase2.positive_sensitivity import iter_records, run_digest
from ai_watermarks_phase2.smoke import load_json
from ai_watermarks_phase2.variance_pilot import file_sha256, write_result


def clopper_pearson_lower(successes: int, samples: int, alpha: float) -> float:
    if successes == 0:
        return 0.0
    return 1.0 - clopper_pearson_upper(samples - successes, samples, alpha)


def evaluate(
    records: Iterable[dict[str, Any]],
    thresholds: dict[str, Any],
    samples_per_cell: int,
    minimum_detections: int,
) -> list[dict[str, Any]]:
    threshold_lookup = {
        (row["scheme"], row["key_id"], int(row["length"])): float(row["threshold"])
        for row in thresholds["operational_thresholds"]
    }
    grouped: dict[tuple[str, str, int], list[float]] = defaultdict(list)
    variants: dict[tuple[str, str, int], set[str]] = defaultdict(set)
    for record in records:
        scheme = record["scheme"]
        key_id = record["key_id"]
        for prefix in record["prefix_results"]:
            cell = (scheme, key_id, int(prefix["length"]))
            grouped[cell].append(float(prefix["score"]["value"]))
            variants[cell].add(record["variant"])
    if len(grouped) != 60:
        raise ValueError(f"Expected 60 cells, found {len(grouped)}")
    cells: list[dict[str, Any]] = []
    for (scheme, key_id, length), values in sorted(grouped.items()):
        if len(values) != samples_per_cell:
            raise ValueError(f"Incomplete cell: {scheme}/{key_id}/{length}")
        if len(variants[(scheme, key_id, length)]) != 1:
            raise ValueError("Named variants must remain explicit and unpooled")
        threshold_key = key_id if scheme == "kgw" else "shared"
        threshold = threshold_lookup[(scheme, threshold_key, length)]
        detections = sum(value > threshold for value in values)
        cells.append(
            {
                "scheme": scheme,
                "key_id": key_id,
                "length": length,
                "variant": next(iter(variants[(scheme, key_id, length)])),
                "threshold": threshold,
                "samples": samples_per_cell,
                "strict_detections": detections,
                "detection_rate": detections / samples_per_cell,
                "one_sided_95_percent_lower_bound_descriptive": clopper_pearson_lower(
                    detections, samples_per_cell, 0.05
                ),
                "passed": detections >= minimum_detections,
            }
        )
    return cells


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path, default=Path("configs/phase2-v2-positive-sensitivity.json")
    )
    parser.add_argument(
        "--run-dir", type=Path, default=Path("results/phase2-v2-positive-sensitivity/run")
    )
    parser.add_argument(
        "--output", type=Path, default=Path("results/phase2-v2-positive-sensitivity/analysis.json")
    )
    args = parser.parse_args(argv)
    if args.output.exists():
        raise FileExistsError(f"Refusing to replace sensitivity analysis: {args.output}")
    config = load_json(args.config)
    metadata = load_json(args.run_dir / "run.json")
    if metadata.get("status") != "positive_sensitivity_complete":
        raise ValueError("Positive-sensitivity run is not complete")
    if metadata.get("pilot_id") != config["pilot_id"]:
        raise ValueError("Run and config pilot IDs differ")
    if metadata.get("confirmation_scores_used") is not False:
        raise ValueError("Run does not preserve confirmation separation")
    threshold_path = Path(config["provisional_thresholds"]["artifact"])
    thresholds = load_json(threshold_path)
    if thresholds.get("pilot_id") != config["pilot_id"]:
        raise ValueError("Threshold and config pilot IDs differ")
    screen = config["screen"]
    cells = evaluate(
        iter_records(args.run_dir),
        thresholds,
        int(screen["samples_per_cell"]),
        int(screen["minimum_detections_per_cell"]),
    )
    summaries = []
    for scheme in ("kgw", "synthid"):
        for length in (128, 256, 512):
            rates = [
                row["detection_rate"]
                for row in cells
                if row["scheme"] == scheme and row["length"] == length
            ]
            summaries.append(
                {
                    "scheme": scheme,
                    "length": length,
                    "minimum_cell_rate": min(rates),
                    "median_cell_rate": statistics.median(rates),
                    "maximum_cell_rate": max(rates),
                }
            )
    passed = all(row["passed"] for row in cells)
    result = {
        "schema_version": 1,
        "status": "sensitivity_screen_passed" if passed else "sensitivity_screen_failed",
        "pilot_id": config["pilot_id"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": config["scope"],
        "input_sha256": {
            "config": file_sha256(args.config),
            "thresholds": file_sha256(threshold_path),
            "run_digest": run_digest(args.run_dir),
            "analysis_source": file_sha256(Path(__file__)),
        },
        "screen": screen,
        "cells": cells,
        "failed_cells": [
            {
                key: row[key]
                for key in (
                    "scheme",
                    "key_id",
                    "length",
                    "strict_detections",
                    "detection_rate",
                )
            }
            for row in cells
            if not row["passed"]
        ],
        "scheme_length_summaries": summaries,
        "interpretation": {
            "confirmatory_claim": False,
            "attacks_authorized": False,
            "v1_confirmation_scores_used": False,
            "next_step": (
                "approve and freeze the final v2 null protocol and compute budget"
                if passed
                else "reassess the threshold margin before any v2 null generation"
            ),
        },
    }
    write_result(args.output, result)
    print(
        json.dumps(
            {
                "status": result["status"],
                "failed_cells": len(result["failed_cells"]),
                "output": str(args.output),
            },
            indent=2,
        )
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
