#!/usr/bin/env python3
"""Apply frozen Stage-A KGW joint-feasibility detection and quality guardrails."""

from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_watermarks_phase2.kgw_joint_protocol import (
    CONFIG_PATH,
    candidate_grid,
    clopper_pearson_lower,
    validate_protocol,
)
from ai_watermarks_phase2.kgw_joint_stage import RESULT_ROOT, batch_paths, iter_records, run_digest
from ai_watermarks_phase2.native import TransformersNativeRunner
from ai_watermarks_phase2.smoke import load_json
from ai_watermarks_phase2.variance_pilot import file_sha256, write_result
from validation.analyse_phase2_v2_kgw_bias_development import (
    conditional_nll_batch,
    distinct_ngram_fraction,
    repeated_ngram_fraction,
)


def threshold_lookup(config: dict[str, Any]) -> dict[tuple[float, str, int], float]:
    artifact = load_json(Path(config["development_null_thresholds"]["artifact"]))
    if artifact.get("status") != "kgw_joint_development_thresholds_frozen":
        raise ValueError("Gamma-specific thresholds are not frozen")
    if artifact.get("protocol_id") != config["protocol_id"]:
        raise ValueError("Threshold artifact and Stage-A protocol differ")
    return {
        (float(row["gamma"]), row["key_id"], int(row["length"])): float(
            row["threshold"]
        )
        for row in artifact["operational_thresholds"]
    }


def noops_by_candidate(run_dir: Path) -> dict[tuple[str, float, float], int]:
    values: defaultdict[tuple[str, float, float], int] = defaultdict(int)
    for path in batch_paths(run_dir):
        batch = load_json(path)
        if batch.get("condition") == "watermarked":
            values[
                (
                    str(batch["key_id"]),
                    float(batch["gamma"]),
                    float(batch["delta"]),
                )
            ] += int(batch.get("empty_rejection_noop_events", 0))
    return dict(values)


def build_cells(
    config: dict[str, Any],
    records: list[dict[str, Any]],
    nll: dict[tuple[str, str, float | None, float | None], dict[int, float]],
    noops: dict[tuple[str, float, float], int],
    stage: str = "stage_a",
) -> list[dict[str, Any]]:
    lengths = [int(value) for value in config["generation"][stage]["paired_prefix_lengths"]]
    samples = int(config["detection_guardrail"]["samples_per_cell"])
    minimum = int(config["detection_guardrail"]["minimum_detections_per_cell"])
    thresholds = threshold_lookup(config)
    control: defaultdict[tuple[str, int], list[dict[str, float]]] = defaultdict(list)
    candidate: defaultdict[
        tuple[str, float, float, int], list[dict[str, float]]
    ] = defaultdict(list)
    variants: defaultdict[tuple[str, float, float, int], set[str]] = defaultdict(set)
    for record in records:
        key_id = str(record["key_id"])
        gamma = None if record["gamma"] is None else float(record["gamma"])
        delta = None if record["delta"] is None else float(record["delta"])
        quality_key = (record["prompt_id"], key_id, gamma, delta)
        for length in lengths:
            tokens = [int(value) for value in record["token_ids"][:length]]
            decoded_counts = record.get("decoded_character_count_by_prefix", {})
            decoded_empty = record.get("decoded_empty_by_prefix", {})
            row = {
                "nll": nll[quality_key][length],
                "repeated_4gram_fraction": repeated_ngram_fraction(tokens, 4),
                "distinct_2gram_fraction": distinct_ngram_fraction(tokens, 2),
                "decoded_character_count": float(decoded_counts[str(length)]),
                "decoded_empty": float(bool(decoded_empty[str(length)])),
            }
            if record["condition"] == "unwatermarked_control":
                control[(key_id, length)].append(row)
                continue
            prefix = next(
                item for item in record["prefix_results"] if int(item["length"]) == length
            )
            row["score"] = float(prefix["score"]["value"])
            cell = (key_id, float(gamma), float(delta), length)
            candidate[cell].append(row)
            variants[cell].add(str(record["variant"]))

    cells = []
    quality = config["automated_quality_guardrails"]
    generated_tokens = int(config["generation"][stage]["generated_tokens"])
    for (key_id, gamma, delta, length), rows in sorted(candidate.items()):
        base = control[(key_id, length)]
        if len(rows) != samples or len(base) != samples or len(variants[(key_id, gamma, delta, length)]) != 1:
            raise ValueError(f"Incomplete or pooled cell: {key_id}/{gamma}/{delta}/{length}")
        threshold = thresholds[(gamma, key_id, length)]
        detections = sum(float(row["score"]) > threshold for row in rows)
        means = {
            name: statistics.fmean(float(row[name]) for row in rows)
            for name in (
                "nll",
                "repeated_4gram_fraction",
                "distinct_2gram_fraction",
                "decoded_character_count",
                "decoded_empty",
            )
        }
        base_means = {
            name: statistics.fmean(float(row[name]) for row in base)
            for name in means
        }
        deltas = {
            "conditional_base_model_nll_nats_per_token": means["nll"] - base_means["nll"],
            "repeated_4gram_fraction": means["repeated_4gram_fraction"] - base_means["repeated_4gram_fraction"],
            "distinct_2gram_fraction": means["distinct_2gram_fraction"] - base_means["distinct_2gram_fraction"],
        }
        char_ratio = (
            means["decoded_character_count"] / base_means["decoded_character_count"]
            if base_means["decoded_character_count"] > 0
            else float("inf")
        )
        no_op_events = int(noops.get((key_id, gamma, delta), 0))
        no_op_rate = no_op_events / (samples * generated_tokens)
        checks = {
            "conditional_base_model_nll": deltas["conditional_base_model_nll_nats_per_token"]
            <= float(quality["conditional_base_model_nll_max_increase_nats_per_token"]),
            "repeated_4gram_fraction": deltas["repeated_4gram_fraction"]
            <= float(quality["repeated_4gram_fraction_max_absolute_increase"]),
            "distinct_2gram_fraction": deltas["distinct_2gram_fraction"]
            >= -float(quality["distinct_2gram_fraction_max_absolute_decrease"]),
            "decoded_character_count_ratio": float(quality["decoded_character_count_mean_ratio_min"])
            <= char_ratio
            <= float(quality["decoded_character_count_mean_ratio_max"]),
            "empty_decoded_outputs": sum(bool(row["decoded_empty"]) for row in rows)
            <= int(quality["empty_decoded_outputs_allowed"]),
            "empty_rejection_noop_rate": no_op_rate
            <= float(quality["empty_rejection_noop_max_rate"]),
        }
        cells.append(
            {
                "scheme": "kgw",
                "variant": next(iter(variants[(key_id, gamma, delta, length)])),
                "key_id": key_id,
                "gamma": gamma,
                "delta": delta,
                "length": length,
                "threshold": threshold,
                "samples": samples,
                "strict_detections": detections,
                "detection_rate": detections / samples,
                "detection_lower_95_one_sided": clopper_pearson_lower(
                    detections, samples, 0.05
                ),
                "detection_passed": detections >= minimum,
                "quality_means": means,
                "control_quality_means": base_means,
                "quality_deltas_vs_unwatermarked": deltas,
                "decoded_character_count_mean_ratio": char_ratio,
                "empty_rejection_noop_events": no_op_events,
                "empty_rejection_noop_rate": no_op_rate,
                "automated_quality_checks": checks,
                "automated_quality_passed": all(checks.values()),
                "automated_cell_passed": detections >= minimum and all(checks.values()),
            }
        )
    return cells


def automated_candidate_decisions(
    config: dict[str, Any], cells: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    decisions = []
    for gamma, delta in candidate_grid(config):
        rows = [
            row
            for row in cells
            if row["gamma"] == gamma and row["delta"] == delta
        ]
        passed = bool(rows) and all(row["automated_cell_passed"] for row in rows)
        decisions.append(
            {
                "gamma": gamma,
                "delta": delta,
                "targeted_cells": len(rows),
                "failed_detection_cells": sum(
                    not row["detection_passed"] for row in rows
                ),
                "failed_automated_quality_cells": sum(
                    not row["automated_quality_passed"] for row in rows
                ),
                "worst_cell_nll_increase": max(
                    (
                        float(
                            row["quality_deltas_vs_unwatermarked"][
                                "conditional_base_model_nll_nats_per_token"
                            ]
                        )
                        for row in rows
                    ),
                    default=float("inf"),
                ),
                "automated_passed": passed,
            }
        )
    return decisions


def apply_blinded_reviews_and_select(
    config: dict[str, Any],
    decisions: list[dict[str, Any]],
    review: dict[str, Any] | None,
) -> tuple[list[dict[str, Any]], dict[str, float] | None, str]:
    eligible = [row for row in decisions if row["automated_passed"]]
    if not eligible:
        return decisions, None, "kgw_joint_stage_a_no_candidate"
    if review is None:
        return decisions, None, "kgw_joint_stage_a_awaiting_blinded_review"
    if review.get("status") != "kgw_joint_blinded_review_complete" or review.get("stage") != "stage_a":
        raise ValueError("Blinded review artifact has the wrong status or stage")
    if review.get("protocol_id") != config["protocol_id"]:
        raise ValueError("Blinded review and protocol differ")
    review_lookup = {
        (float(row["gamma"]), float(row["delta"])): row
        for row in review.get("candidate_reviews", [])
    }
    guard = config["blinded_task_quality_guardrail"]
    for row in decisions:
        if not row["automated_passed"]:
            row["blinded_review_passed"] = None
            row["eligible"] = False
            continue
        reviewed = review_lookup.get((row["gamma"], row["delta"]))
        if reviewed is None:
            raise ValueError("An automatically eligible candidate lacks blinded review")
        if int(reviewed["pairs"]) != int(guard["sample_pairs_per_candidate"]):
            raise ValueError("Blinded review pair count differs from the protocol")
        passed = (
            int(reviewed["candidate_unusable_pairs"])
            <= int(guard["candidate_unusable_pairs_allowed"])
            and int(reviewed["candidate_worse_pairs"])
            <= int(guard["candidate_worse_pairs_allowed"])
        )
        row["blinded_review"] = reviewed
        row["blinded_review_passed"] = passed
        row["eligible"] = passed
    finalists = [row for row in decisions if row.get("eligible")]
    if not finalists:
        return decisions, None, "kgw_joint_stage_a_no_candidate"
    best_nll = min(float(row["worst_cell_nll_increase"]) for row in finalists)
    tolerance = float(config["stage_a_selection_rule"]["nll_tie_tolerance_nats_per_token"])
    tied = [
        row
        for row in finalists
        if float(row["worst_cell_nll_increase"]) <= best_nll + tolerance
    ]
    selected = min(
        tied,
        key=lambda row: (
            float(row["delta"]),
            abs(float(row["gamma"]) - 0.5),
            float(row["gamma"]),
        ),
    )
    return (
        decisions,
        {"gamma": float(selected["gamma"]), "delta": float(selected["delta"])},
        "kgw_joint_stage_a_candidate_selected",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    parser.add_argument("--run-dir", type=Path, default=RESULT_ROOT / "stage-a" / "run")
    parser.add_argument("--blinded-review", type=Path)
    parser.add_argument("--output", type=Path, default=RESULT_ROOT / "stage-a-analysis.json")
    parser.add_argument("--selection-output", type=Path)
    args = parser.parse_args(argv)
    if args.output.exists():
        raise FileExistsError(f"Refusing to replace Stage-A analysis: {args.output}")

    config = load_json(args.config)
    validate_protocol(config)
    metadata = load_json(args.run_dir / "run.json")
    if metadata.get("status") != "kgw_joint_stage_a_complete":
        raise ValueError("Stage-A run is not complete")
    if metadata.get("protocol_id") != config["protocol_id"]:
        raise ValueError("Stage-A run and protocol differ")
    if metadata.get("confirmation_scores_used") is not False:
        raise ValueError("Stage A does not preserve confirmation separation")

    records = list(iter_records(args.run_dir))
    prompt_manifest = load_json(Path(config["prompt_manifests"]["stage_a"]))
    prompts = {row["id"]: row["prompt"] for row in prompt_manifest["records"]}
    lengths = [int(value) for value in config["generation"]["stage_a"]["paired_prefix_lengths"]]
    runner = TransformersNativeRunner(
        model_id=config["model"]["id"],
        revision=config["model"]["revision"],
        device=config["model"]["device"],
    )
    quality: dict[
        tuple[str, str, float | None, float | None], dict[int, float]
    ] = {}
    batch_size = int(config["generation"]["batch_size"])
    for start in range(0, len(records), batch_size):
        block = records[start : start + batch_size]
        nlls = conditional_nll_batch(
            runner,
            [prompts[row["prompt_id"]] for row in block],
            [[int(value) for value in row["token_ids"]] for row in block],
            lengths,
        )
        for row, values in zip(block, nlls, strict=True):
            if not all(math.isfinite(value) for value in values.values()):
                raise RuntimeError("Non-finite conditional NLL")
            quality[
                (
                    row["prompt_id"],
                    row["key_id"],
                    None if row["gamma"] is None else float(row["gamma"]),
                    None if row["delta"] is None else float(row["delta"]),
                )
            ] = values
        print(
            f"quality checkpoint outputs {min(start + batch_size, len(records))}/{len(records)}",
            flush=True,
        )
    cells = build_cells(config, records, quality, noops_by_candidate(args.run_dir))
    decisions = automated_candidate_decisions(config, cells)
    review = load_json(args.blinded_review) if args.blinded_review else None
    decisions, selected, status = apply_blinded_reviews_and_select(
        config, decisions, review
    )
    result = {
        "schema_version": 1,
        "status": status,
        "protocol_id": config["protocol_id"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_sha256": {
            "protocol_config": file_sha256(args.config),
            "development_thresholds": file_sha256(
                Path(config["development_null_thresholds"]["artifact"])
            ),
            "stage_a_run_digest": run_digest(args.run_dir),
            "analysis_source": file_sha256(Path(__file__)),
            **(
                {"blinded_review": file_sha256(args.blinded_review)}
                if args.blinded_review
                else {}
            ),
        },
        "cells": cells,
        "candidate_decisions": decisions,
        "selected_candidate": selected,
        "interpretation": {
            "confirmatory_claim": False,
            "attacks_authorized": False,
            "replacement_null_generation_authorized": False,
            "v1_confirmation_scores_used": False,
        },
    }
    write_result(args.output, result)
    selection_output = args.selection_output or Path(
        config["stage_a_selection_rule"]["selection_artifact"]
    )
    if status != "kgw_joint_stage_a_awaiting_blinded_review":
        if selection_output.exists():
            raise FileExistsError(
                f"Refusing to replace frozen Stage-A selection: {selection_output}"
            )
        write_result(
            selection_output,
            {
                "schema_version": 1,
                "status": status,
                "protocol_id": config["protocol_id"],
                "generated_at": result["generated_at"],
                "selected_candidate": selected,
                "stage_a_analysis_sha256": file_sha256(args.output),
                "failure_consequence": config["stop_rules"]["no_stage_a_candidate"],
            },
        )
    print(
        json.dumps(
            {
                "status": status,
                "automatically_eligible_candidates": sum(
                    row["automated_passed"] for row in decisions
                ),
                "selected_candidate": selected,
                "output": str(args.output),
                "selection_output": (
                    None
                    if status == "kgw_joint_stage_a_awaiting_blinded_review"
                    else str(selection_output)
                ),
            },
            indent=2,
        )
    )
    if status == "kgw_joint_stage_a_candidate_selected":
        return 0
    if status == "kgw_joint_stage_a_awaiting_blinded_review":
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
