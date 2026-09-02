"""Fit frozen null thresholds and evaluate the one-shot confirmation gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from collections.abc import Iterable
from typing import Any

from .confirmatory_null import iter_sharded_records, sharded_run_digest
from .smoke import load_json
from .variance_pilot import file_sha256, write_result


def binomial_cdf(exceedances: int, samples: int, probability: float) -> float:
    if not 0.0 <= probability <= 1.0:
        raise ValueError("probability must lie in [0, 1]")
    if not 0 <= exceedances <= samples:
        raise ValueError("exceedances must lie in [0, samples]")
    if probability == 0.0:
        return 1.0
    if probability == 1.0:
        return 1.0 if exceedances == samples else 0.0
    q = 1.0 - probability
    term = q**samples
    total = term
    for k in range(exceedances):
        term *= (samples - k) / (k + 1) * probability / q
        total += term
    return min(1.0, total)


def clopper_pearson_upper(exceedances: int, samples: int, alpha: float) -> float:
    """Exact one-sided upper binomial confidence limit."""

    if exceedances == samples:
        return 1.0
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must lie in (0, 1)")
    lower, upper = 0.0, 1.0
    for _ in range(100):
        midpoint = (lower + upper) / 2.0
        if binomial_cdf(exceedances, samples, midpoint) > alpha:
            lower = midpoint
        else:
            upper = midpoint
    return (lower + upper) / 2.0


def maximum_passing_exceedances(
    *, samples: int, target_fpr: float, familywise_alpha: float, cells: int
) -> int:
    alpha = familywise_alpha / cells
    maximum = None
    for value in range(samples + 1):
        if clopper_pearson_upper(value, samples, alpha) > target_fpr:
            break
        maximum = value
    if maximum is None:
        raise ValueError("No exceedance count can satisfy the declared acceptance rule")
    return maximum


def grouped_scores(records: Iterable[dict[str, Any]]) -> dict[tuple[str, str, int], list[float]]:
    grouped: dict[tuple[str, str, int], list[float]] = defaultdict(list)
    for record in records:
        for prefix in record["prefix_results"]:
            for score in prefix["scores"]:
                grouped[(score["scheme"], score["key_id"], int(prefix["length"]))].append(
                    float(score["value"])
                )
    return grouped


def threshold_candidate(values: list[float], allowed_exceedances: int) -> float:
    if len(values) <= allowed_exceedances:
        raise ValueError("Not enough values for the declared order statistic")
    return sorted(values)[-(allowed_exceedances + 1)]


def prompt_hashes(path: Path) -> set[str]:
    manifest = load_json(path)
    return {record["prompt_sha256"] for record in manifest["records"]}


def validate_complete_run(run_dir: Path, protocol_id: str, split_role: str) -> dict[str, Any]:
    metadata = load_json(run_dir / "run.json")
    if metadata.get("status") != "confirmatory_split_complete":
        raise ValueError(f"{split_role} run is not complete")
    if metadata.get("protocol_id") != protocol_id or metadata.get("split_role") != split_role:
        raise ValueError(f"{split_role} run identity differs from the protocol")
    if int(metadata["records"]) != int(metadata["target_records"]):
        raise ValueError(f"{split_role} record count differs from target")
    return metadata


def fit_thresholds(protocol_path: Path, run_dir: Path, output: Path) -> dict[str, Any]:
    if output.exists():
        raise FileExistsError(f"Refusing to replace frozen threshold artifact: {output}")
    protocol = load_json(protocol_path)
    validate_complete_run(run_dir, protocol["protocol_id"], "calibration")
    samples = int(protocol["selection"]["samples_per_split"])
    acceptance = protocol["acceptance"]
    allowed = maximum_passing_exceedances(
        samples=samples,
        target_fpr=float(acceptance["target_fpr"]),
        familywise_alpha=1.0 - float(acceptance["familywise_confidence"]),
        cells=int(acceptance["primary_cells"]),
    )
    if allowed != int(acceptance["maximum_exceedances_per_5000"]):
        raise ValueError("Computed exact-binomial acceptance count differs from protocol")
    grouped = grouped_scores(iter_sharded_records(run_dir))
    if len(grouped) != int(acceptance["primary_cells"]):
        raise ValueError("Calibration does not contain all declared primary cells")
    alpha = (1.0 - float(acceptance["familywise_confidence"])) / int(
        acceptance["primary_cells"]
    )
    candidates = []
    candidate_lookup = {}
    for (scheme, key_id, length), values in sorted(grouped.items()):
        if len(values) != samples:
            raise ValueError(f"Incomplete calibration cell: {scheme}/{key_id}/{length}")
        threshold = threshold_candidate(values, allowed)
        exceedances = sum(value > threshold for value in values)
        upper = clopper_pearson_upper(exceedances, samples, alpha)
        item = {
            "scheme": scheme,
            "key_id": key_id,
            "length": length,
            "samples": samples,
            "candidate_threshold": threshold,
            "strict_exceedances": exceedances,
            "empirical_rate": exceedances / samples,
            "exact_upper_bound": upper,
        }
        candidates.append(item)
        candidate_lookup[(scheme, key_id, length)] = threshold

    operational = []
    for length in (128, 256, 512):
        for key_index in range(10):
            key_id = f"kgw-{key_index:02d}"
            operational.append(
                {
                    "scheme": "kgw",
                    "key_id": key_id,
                    "length": length,
                    "threshold": candidate_lookup[("kgw", key_id, length)],
                    "policy": "key_conditional",
                }
            )
        synthid_threshold = max(
            candidate_lookup[("synthid", f"synthid-{key_index:02d}", length)]
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
    artifact = {
        "schema_version": 1,
        "status": "thresholds_frozen",
        "protocol_id": protocol["protocol_id"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "protocol_sha256": file_sha256(protocol_path),
        "calibration_run_digest": sharded_run_digest(run_dir),
        "calibration_prompt_manifest": "data/phase2-confirmatory-calibration-prompts.json",
        "calibration_prompt_manifest_sha256": file_sha256(
            Path("data/phase2-confirmatory-calibration-prompts.json")
        ),
        "acceptance": acceptance,
        "per_cell_alpha": alpha,
        "maximum_passing_exceedances": allowed,
        "candidate_cells": candidates,
        "operational_thresholds": operational,
    }
    write_result(output, artifact)
    return artifact


def evaluate_confirmation(
    protocol_path: Path, run_dir: Path, thresholds_path: Path, output: Path
) -> dict[str, Any]:
    if output.exists():
        raise FileExistsError(f"Refusing to replace one-shot confirmation result: {output}")
    protocol = load_json(protocol_path)
    metadata = validate_complete_run(run_dir, protocol["protocol_id"], "confirmation")
    thresholds = load_json(thresholds_path)
    if thresholds.get("status") != "thresholds_frozen":
        raise ValueError("Threshold artifact is not frozen")
    if thresholds.get("protocol_sha256") != file_sha256(protocol_path):
        raise ValueError("Protocol changed after thresholds were frozen")
    if metadata["input_sha256"].get("thresholds") != file_sha256(thresholds_path):
        raise ValueError("Confirmation generation did not use this threshold artifact")
    calibration_manifest = Path(thresholds["calibration_prompt_manifest"])
    confirmation_manifest = Path("data/phase2-confirmatory-confirmation-prompts.json")
    if prompt_hashes(calibration_manifest) & prompt_hashes(confirmation_manifest):
        raise ValueError("Calibration and confirmation prompt hashes overlap")

    samples = int(protocol["selection"]["samples_per_split"])
    acceptance = protocol["acceptance"]
    alpha = (1.0 - float(acceptance["familywise_confidence"])) / int(
        acceptance["primary_cells"]
    )
    threshold_lookup = {
        (item["scheme"], item["key_id"], item["length"]): item["threshold"]
        for item in thresholds["operational_thresholds"]
    }
    cells = []
    grouped: dict[tuple[str, str, int], list[float]] = defaultdict(list)
    category_values: dict[tuple[str, str, int, str], list[float]] = defaultdict(list)
    for record in iter_sharded_records(run_dir):
        for prefix in record["prefix_results"]:
            for score in prefix["scores"]:
                grouped[(score["scheme"], score["key_id"], int(prefix["length"]))].append(
                    float(score["value"])
                )
                category_values[
                    (score["scheme"], score["key_id"], int(prefix["length"]), record["category"])
                ].append(float(score["value"]))
    for (scheme, key_id, length), values in sorted(grouped.items()):
        threshold_key = key_id if scheme == "kgw" else "shared"
        threshold = threshold_lookup[(scheme, threshold_key, length)]
        exceedances = sum(value > threshold for value in values)
        upper = clopper_pearson_upper(exceedances, samples, alpha)
        category_rates = {
            category: sum(value > threshold for value in category_scores)
            / len(category_scores)
            for (cell_scheme, cell_key, cell_length, category), category_scores in category_values.items()
            if (cell_scheme, cell_key, cell_length) == (scheme, key_id, length)
        }
        cells.append(
            {
                "scheme": scheme,
                "key_id": key_id,
                "length": length,
                "threshold": threshold,
                "samples": len(values),
                "strict_exceedances": exceedances,
                "empirical_rate": exceedances / len(values),
                "exact_upper_bound": upper,
                "passed": upper <= float(acceptance["target_fpr"]),
                "category_rates_diagnostic": dict(sorted(category_rates.items())),
            }
        )
    if len(cells) != int(acceptance["primary_cells"]):
        raise ValueError("Confirmation does not contain all declared primary cells")
    result = {
        "schema_version": 1,
        "status": "confirmation_gate_passed" if all(item["passed"] for item in cells) else "confirmation_gate_failed",
        "protocol_id": protocol["protocol_id"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "protocol_sha256": file_sha256(protocol_path),
        "thresholds_sha256": file_sha256(thresholds_path),
        "confirmation_run_digest": sharded_run_digest(run_dir),
        "acceptance": acceptance,
        "per_cell_alpha": alpha,
        "cells": cells,
        "failed_cells": [
            {key: item[key] for key in ("scheme", "key_id", "length", "strict_exceedances", "exact_upper_bound")}
            for item in cells
            if not item["passed"]
        ],
        "one_shot": True,
        "post_confirmation_retuning_authorized": False,
    }
    write_result(output, result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    fit = subparsers.add_parser("fit")
    fit.add_argument("--protocol", type=Path, default=Path("configs/phase2-confirmatory-null.json"))
    fit.add_argument("--run-dir", type=Path, default=Path("results/phase2-confirmatory-null/calibration"))
    fit.add_argument("--output", type=Path, default=Path("results/phase2-confirmatory-null/thresholds.json"))
    evaluate = subparsers.add_parser("evaluate")
    evaluate.add_argument("--protocol", type=Path, default=Path("configs/phase2-confirmatory-null.json"))
    evaluate.add_argument("--run-dir", type=Path, default=Path("results/phase2-confirmatory-null/confirmation"))
    evaluate.add_argument("--thresholds", type=Path, default=Path("results/phase2-confirmatory-null/thresholds.json"))
    evaluate.add_argument("--output", type=Path, default=Path("results/phase2-confirmatory-null/confirmation-gate.json"))
    args = parser.parse_args(argv)
    if args.command == "fit":
        artifact = fit_thresholds(args.protocol, args.run_dir, args.output)
        print(json.dumps({"status": artifact["status"], "output": str(args.output)}, indent=2))
        return 0
    result = evaluate_confirmation(args.protocol, args.run_dir, args.thresholds, args.output)
    print(json.dumps({"status": result["status"], "output": str(args.output), "failed_cells": len(result["failed_cells"])}, indent=2))
    return 0 if result["status"] == "confirmation_gate_passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
