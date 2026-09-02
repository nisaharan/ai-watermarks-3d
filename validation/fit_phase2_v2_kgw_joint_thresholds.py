#!/usr/bin/env python3
"""Fit frozen gamma-specific thresholds from the fresh KGW development null."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_watermarks_phase2.calibration_gate import (
    clopper_pearson_upper,
    maximum_passing_exceedances,
    threshold_candidate,
)
from ai_watermarks_phase2.kgw_joint_null import DEFAULT_OUTPUT, iter_records, run_digest
from ai_watermarks_phase2.kgw_joint_protocol import CONFIG_PATH, validate_protocol
from ai_watermarks_phase2.smoke import load_json
from ai_watermarks_phase2.variance_pilot import file_sha256, write_result


def fit(config_path: Path, run_dir: Path) -> dict[str, Any]:
    config = load_json(config_path)
    validate_protocol(config)
    metadata = load_json(run_dir / "run.json")
    if metadata.get("status") != "kgw_joint_development_null_complete":
        raise ValueError("Development-null run is not complete")
    if metadata.get("protocol_id") != config["protocol_id"]:
        raise ValueError("Development-null run and protocol differ")
    if metadata.get("confirmation_scores_used") is not False:
        raise ValueError("Development null does not preserve confirmation separation")

    settings = config["development_null_thresholds"]
    samples = int(settings["samples"])
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
        raise ValueError("Exact-binomial maximum differs from the preregistration")

    grouped: dict[tuple[float, str, int], list[float]] = defaultdict(list)
    for record in iter_records(run_dir):
        for prefix in record["prefix_results"]:
            length = int(prefix["length"])
            for score in prefix["scores"]:
                grouped[(float(score["greenlist_ratio"]), score["key_id"], length)].append(
                    float(score["value"])
                )
    if len(grouped) != cells:
        raise ValueError(f"Expected {cells} gamma-key-length cells, found {len(grouped)}")

    operational = []
    for (gamma, key_id, length), values in sorted(grouped.items()):
        if len(values) != samples:
            raise ValueError(f"Incomplete cell: gamma={gamma}/{key_id}/{length}")
        threshold = threshold_candidate(values, allowed)
        exceedances = sum(value > threshold for value in values)
        upper = clopper_pearson_upper(exceedances, samples, per_cell_alpha)
        if upper > float(settings["design_fpr"]):
            raise RuntimeError("Fitted threshold does not satisfy its exact design bound")
        operational.append(
            {
                "scheme": "kgw",
                "variant": config["variant"]["id"],
                "gamma": gamma,
                "key_id": key_id,
                "length": length,
                "samples": samples,
                "threshold": threshold,
                "strict_exceedances": exceedances,
                "empirical_rate": exceedances / samples,
                "exact_upper_bound": upper,
                "policy": "gamma_key_model_length_conditional",
            }
        )
    return {
        "schema_version": 1,
        "status": "kgw_joint_development_thresholds_frozen",
        "protocol_id": config["protocol_id"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "Development-only feasibility thresholds; never valid for v2 confirmation",
        "input_sha256": {
            "protocol_config": file_sha256(config_path),
            "development_null_run_digest": run_digest(run_dir),
            "fitter_source": file_sha256(Path(__file__)),
        },
        "separation": {
            "source_role": "fresh_ultrachat_development_null_only",
            "confirmation_scores_loaded": False,
            "replacement_confirmatory_threshold": False,
        },
        "design_fpr": float(settings["design_fpr"]),
        "familywise_confidence": float(settings["familywise_confidence"]),
        "primary_cells": cells,
        "per_cell_alpha": per_cell_alpha,
        "maximum_strict_exceedances": allowed,
        "decision_rule": settings["decision_rule"],
        "operational_thresholds": operational,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    config = load_json(args.config)
    output = args.output or Path(config["development_null_thresholds"]["artifact"])
    if output.exists():
        raise FileExistsError(f"Refusing to replace frozen thresholds: {output}")
    artifact = fit(args.config, args.run_dir)
    write_result(output, artifact)
    print(
        json.dumps(
            {
                "status": artifact["status"],
                "output": str(output),
                "cells": len(artifact["operational_thresholds"]),
                "maximum_strict_exceedances": artifact[
                    "maximum_strict_exceedances"
                ],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
