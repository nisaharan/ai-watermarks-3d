#!/usr/bin/env python3
"""Fit provisional 0.5% thresholds from v1 calibration data only."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_watermarks_phase2.calibration_gate import (
    clopper_pearson_upper,
    grouped_scores,
    maximum_passing_exceedances,
    threshold_candidate,
    validate_complete_run,
)
from ai_watermarks_phase2.confirmatory_null import (
    iter_sharded_records,
    sharded_run_digest,
)
from ai_watermarks_phase2.smoke import load_json
from ai_watermarks_phase2.variance_pilot import file_sha256, write_result


def fit(config_path: Path) -> dict[str, Any]:
    config = load_json(config_path)
    if config.get("status") != "development_only_predeclared":
        raise ValueError("Threshold fit requires the predeclared development config")
    settings = config["provisional_thresholds"]
    if settings.get("source_role") != "v1_calibration_only":
        raise ValueError("Only v1 calibration data are authorized")
    if settings.get("confirmation_scores_used") is not False:
        raise ValueError("Confirmation scores must remain prohibited")
    protocol_path = Path(settings["source_protocol"])
    run_dir = Path(settings["source_run"])
    prompt_path = Path(settings["source_prompt_manifest"])
    protocol = load_json(protocol_path)
    validate_complete_run(run_dir, protocol["protocol_id"], "calibration")
    samples = int(settings["source_samples_per_cell"])
    cells = int(settings["primary_cells"])
    familywise_alpha = 1.0 - float(settings["familywise_confidence"])
    per_cell_alpha = familywise_alpha / cells
    allowed = maximum_passing_exceedances(
        samples=samples,
        target_fpr=float(settings["design_fpr"]),
        familywise_alpha=familywise_alpha,
        cells=cells,
    )
    if allowed != int(settings["maximum_strict_exceedances"]):
        raise ValueError("Computed calibration-only cutoff differs from the config")
    grouped = grouped_scores(iter_sharded_records(run_dir))
    if len(grouped) != cells:
        raise ValueError("Calibration run does not contain all 60 cells")

    candidates: list[dict[str, Any]] = []
    lookup: dict[tuple[str, str, int], float] = {}
    for (scheme, key_id, length), values in sorted(grouped.items()):
        if len(values) != samples:
            raise ValueError(f"Incomplete cell: {scheme}/{key_id}/{length}")
        threshold = threshold_candidate(values, allowed)
        exceedances = sum(value > threshold for value in values)
        upper = clopper_pearson_upper(exceedances, samples, per_cell_alpha)
        candidates.append(
            {
                "scheme": scheme,
                "key_id": key_id,
                "length": length,
                "samples": samples,
                "candidate_threshold": threshold,
                "strict_exceedances": exceedances,
                "empirical_rate": exceedances / samples,
                "exact_upper_bound": upper,
            }
        )
        lookup[(scheme, key_id, length)] = threshold

    operational: list[dict[str, Any]] = []
    for length in (128, 256, 512):
        for key_index in range(10):
            key_id = f"kgw-{key_index:02d}"
            operational.append(
                {
                    "scheme": "kgw",
                    "key_id": key_id,
                    "length": length,
                    "threshold": lookup[("kgw", key_id, length)],
                    "policy": "key_conditional",
                }
            )
        synthid_threshold = max(
            lookup[("synthid", f"synthid-{key_index:02d}", length)]
            for key_index in range(10)
        )
        operational.append(
            {
                "scheme": "synthid",
                "key_id": "shared",
                "length": length,
                "threshold": synthid_threshold,
                "policy": "maximum_of_key_specific_candidates",
            }
        )

    return {
        "schema_version": 1,
        "status": "development_thresholds_frozen",
        "pilot_id": config["pilot_id"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "Development-only sensitivity stress test; never valid for v2 confirmation",
        "input_sha256": {
            "development_config": file_sha256(config_path),
            "v1_protocol": file_sha256(protocol_path),
            "v1_calibration_prompt_manifest": file_sha256(prompt_path),
            "v1_calibration_run_digest": sharded_run_digest(run_dir),
            "fitter_source": file_sha256(Path(__file__)),
        },
        "separation": {
            "source_split": "calibration",
            "confirmation_scores_loaded": False,
            "confirmation_path_accepted_by_tool": False,
            "replacement_confirmatory_threshold": False,
        },
        "design_fpr": float(settings["design_fpr"]),
        "per_cell_alpha": per_cell_alpha,
        "maximum_strict_exceedances": allowed,
        "candidate_cells": candidates,
        "operational_thresholds": operational,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/phase2-v2-positive-sensitivity.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/phase2-v2-positive-sensitivity/provisional-thresholds.json"),
    )
    args = parser.parse_args(argv)
    if args.output.exists():
        raise FileExistsError(f"Refusing to replace development thresholds: {args.output}")
    artifact = fit(args.config)
    write_result(args.output, artifact)
    print(
        json.dumps(
            {
                "status": artifact["status"],
                "output": str(args.output),
                "maximum_strict_exceedances": artifact["maximum_strict_exceedances"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
