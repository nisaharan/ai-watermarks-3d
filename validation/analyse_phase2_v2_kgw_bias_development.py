#!/usr/bin/env python3
"""Evaluate the predeclared targeted KGW bias experiment and quality guardrails."""

from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from ai_watermarks_phase2.kgw_bias_development import iter_records, run_digest
from ai_watermarks_phase2.native import TransformersNativeRunner
from ai_watermarks_phase2.smoke import load_json
from ai_watermarks_phase2.variance_pilot import file_sha256, write_result


def repeated_ngram_fraction(tokens: list[int], n: int) -> float:
    grams = [tuple(tokens[index:index + n]) for index in range(len(tokens) - n + 1)]
    return 1.0 - len(set(grams)) / len(grams) if grams else 0.0


def distinct_ngram_fraction(tokens: list[int], n: int) -> float:
    grams = [tuple(tokens[index:index + n]) for index in range(len(tokens) - n + 1)]
    return len(set(grams)) / len(grams) if grams else 1.0


def conditional_nll_batch(
    runner: TransformersNativeRunner,
    prompts: list[str],
    continuations: list[list[int]],
    lengths: list[int],
    logit_chunk: int = 16,
) -> list[dict[int, float]]:
    """Return base-model continuation NLL without materialising full-sequence logits."""
    torch = runner.torch
    encoded = runner.tokenizer(prompts, padding=True, return_tensors="pt").to(runner.device)
    prompt_width = int(encoded["input_ids"].shape[1])
    continuation_tensor = torch.tensor(continuations, dtype=torch.long, device=runner.device)
    input_ids = torch.cat([encoded["input_ids"], continuation_tensor], dim=1)
    attention_mask = torch.cat([
        encoded["attention_mask"],
        torch.ones_like(continuation_tensor, dtype=encoded["attention_mask"].dtype),
    ], dim=1)
    base_model = getattr(runner.model, "model", None)
    if base_model is None or not hasattr(runner.model, "lm_head"):
        raise RuntimeError("Model does not expose a base model and lm_head for bounded-memory NLL")
    with torch.inference_mode():
        hidden = base_model(
            input_ids=input_ids, attention_mask=attention_mask,
            use_cache=False, return_dict=True,
        ).last_hidden_state[:, prompt_width - 1:prompt_width + max(lengths) - 1, :]
        losses = torch.empty(
            (len(prompts), max(lengths)), dtype=torch.float64, device="cpu"
        )
        for start in range(0, max(lengths), logit_chunk):
            stop = min(start + logit_chunk, max(lengths))
            logits = runner.model.lm_head(hidden[:, start:stop, :]).float()
            targets = continuation_tensor[:, start:stop]
            token_losses = torch.nn.functional.cross_entropy(
                logits.reshape(-1, logits.shape[-1]), targets.reshape(-1), reduction="none"
            ).reshape(len(prompts), stop - start)
            losses[:, start:stop] = token_losses.double().cpu()
    cumulative = losses.cumsum(dim=1)
    return [
        {length: float(cumulative[row, length - 1].item() / length) for length in lengths}
        for row in range(len(prompts))
    ]


def cell_results(
    records: Iterable[dict[str, Any]], thresholds: dict[str, Any],
    lengths: list[int], samples: int, minimum_detections: int,
    quality_by_output: dict[tuple[str, str, float], dict[int, float]],
) -> list[dict[str, Any]]:
    threshold_lookup = {
        (row["key_id"], int(row["length"])): float(row["threshold"])
        for row in thresholds["operational_thresholds"] if row["scheme"] == "kgw"
    }
    grouped: dict[tuple[str, float, int], list[dict[str, float]]] = defaultdict(list)
    variants: dict[tuple[str, float, int], set[str]] = defaultdict(set)
    for record in records:
        output_key = (record["prompt_id"], record["key_id"], float(record["bias"]))
        for prefix in record["prefix_results"]:
            length = int(prefix["length"])
            tokens = [int(v) for v in record["token_ids"][:length]]
            cell = (record["key_id"], float(record["bias"]), length)
            grouped[cell].append({
                "score": float(prefix["score"]["value"]),
                "nll": quality_by_output[output_key][length],
                "repeated_4gram_fraction": repeated_ngram_fraction(tokens, 4),
                "distinct_2gram_fraction": distinct_ngram_fraction(tokens, 2),
            })
            variants[cell].add(record["variant"])
    cells = []
    for (key_id, bias, length), rows in sorted(grouped.items()):
        if len(rows) != samples or len(variants[(key_id, bias, length)]) != 1:
            raise ValueError(f"Incomplete or pooled cell: {key_id}/{bias}/{length}")
        threshold = threshold_lookup[(key_id, length)]
        detections = sum(row["score"] > threshold for row in rows)
        cells.append({
            "scheme": "kgw", "key_id": key_id, "bias": bias, "length": length,
            "variant": next(iter(variants[(key_id, bias, length)])),
            "threshold": threshold, "samples": samples,
            "strict_detections": detections, "detection_rate": detections / samples,
            "detection_passed": detections >= minimum_detections,
            "quality_means": {
                name: statistics.fmean(row[name] for row in rows)
                for name in ("nll", "repeated_4gram_fraction", "distinct_2gram_fraction")
            },
        })
    return cells


def apply_quality_and_select(config: dict[str, Any], cells: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], float | None]:
    guard = config["quality_guardrails"]
    reference_bias = float(guard["reference_bias"])
    lookup = {(row["key_id"], row["bias"], row["length"]): row for row in cells}
    for row in cells:
        reference = lookup[(row["key_id"], reference_bias, row["length"])]
        values, base = row["quality_means"], reference["quality_means"]
        deltas = {
            "conditional_base_model_nll_nats_per_token": values["nll"] - base["nll"],
            "repeated_4gram_fraction": values["repeated_4gram_fraction"] - base["repeated_4gram_fraction"],
            "distinct_2gram_fraction": values["distinct_2gram_fraction"] - base["distinct_2gram_fraction"],
        }
        checks = {
            "conditional_base_model_nll": deltas["conditional_base_model_nll_nats_per_token"] <= float(guard["conditional_base_model_nll_max_increase_nats_per_token"]),
            "repeated_4gram_fraction": deltas["repeated_4gram_fraction"] <= float(guard["repeated_4gram_fraction_max_absolute_increase"]),
            "distinct_2gram_fraction": deltas["distinct_2gram_fraction"] >= -float(guard["distinct_2gram_fraction_max_absolute_decrease"]),
        }
        row["quality_deltas_vs_bias_2_control"] = deltas
        row["quality_checks"] = checks
        row["quality_passed"] = all(checks.values())
        row["cell_passed"] = row["detection_passed"] and row["quality_passed"]
    decisions = []
    selected = None
    for bias in [float(value) for value in config["generation"]["bias_candidates_in_selection_order"]]:
        bias_cells = [row for row in cells if row["bias"] == bias]
        passed = bool(bias_cells) and all(row["cell_passed"] for row in bias_cells)
        decisions.append({
            "bias": bias, "targeted_cells": len(bias_cells),
            "failed_detection_cells": sum(not row["detection_passed"] for row in bias_cells),
            "failed_quality_cells": sum(not row["quality_passed"] for row in bias_cells),
            "passed": passed,
        })
        if selected is None and passed:
            selected = bias
    return cells, decisions, selected


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/phase2-v2-kgw-bias-development.json"))
    parser.add_argument("--run-dir", type=Path, default=Path("results/phase2-v2-kgw-bias-development/run"))
    parser.add_argument("--output", type=Path, default=Path("results/phase2-v2-kgw-bias-development/analysis.json"))
    args = parser.parse_args(argv)
    if args.output.exists():
        raise FileExistsError(f"Refusing to replace analysis: {args.output}")
    config, metadata = load_json(args.config), load_json(args.run_dir / "run.json")
    if metadata.get("status") != "kgw_bias_development_complete":
        raise ValueError("KGW bias development run is not complete")
    if metadata.get("experiment_id") != config.get("experiment_id"):
        raise ValueError("Run and config experiment IDs differ")
    if metadata.get("confirmation_scores_used") is not False:
        raise ValueError("Run does not preserve confirmation separation")
    records = list(iter_records(args.run_dir))
    prompts = {row["id"]: row["prompt"] for row in load_json(Path(config["prompt_manifest"]))["records"]}
    lengths = [int(value) for value in config["generation"]["paired_prefix_lengths"]]
    runner = TransformersNativeRunner(
        model_id=config["model"]["id"], revision=config["model"]["revision"],
        device=config["model"]["device"],
    )
    quality: dict[tuple[str, str, float], dict[int, float]] = {}
    batch_size = int(config["generation"]["batch_size"])
    for start in range(0, len(records), batch_size):
        block = records[start:start + batch_size]
        nlls = conditional_nll_batch(
            runner, [prompts[row["prompt_id"]] for row in block],
            [[int(v) for v in row["token_ids"]] for row in block], lengths,
        )
        for row, nll in zip(block, nlls, strict=True):
            if not all(math.isfinite(value) for value in nll.values()):
                raise RuntimeError("Non-finite quality loss")
            quality[(row["prompt_id"], row["key_id"], float(row["bias"]))] = nll
        print(f"quality checkpoint outputs {min(start + batch_size, len(records))}/{len(records)}", flush=True)
    thresholds = load_json(Path(config["provisional_thresholds"]["artifact"]))
    cells = cell_results(
        records, thresholds, lengths,
        int(config["detection_guardrail"]["samples_per_cell"]),
        int(config["detection_guardrail"]["minimum_detections_per_cell"]), quality,
    )
    cells, decisions, selected = apply_quality_and_select(config, cells)
    result = {
        "schema_version": 1,
        "status": "kgw_bias_candidate_selected" if selected is not None else "kgw_bias_development_failed",
        "experiment_id": config["experiment_id"], "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": config["scope"],
        "input_sha256": {
            "config": file_sha256(args.config),
            "thresholds": file_sha256(Path(config["provisional_thresholds"]["artifact"])),
            "run_digest": run_digest(args.run_dir), "analysis_source": file_sha256(Path(__file__)),
        },
        "guardrails": {
            "detection": config["detection_guardrail"],
            "quality": config["quality_guardrails"],
            "selection": config["selection_rule"],
        },
        "cells": cells, "candidate_decisions": decisions, "selected_bias": selected,
        "interpretation": {
            "confirmatory_claim": False, "attacks_authorized": False,
            "full_v2_null_generation_authorized": False, "v1_confirmation_scores_used": False,
            "next_step": (
                "fresh independent all-ten-key KGW positive validation at 128, 256 and 512 tokens"
                if selected is not None else "reassess KGW design without weakening the predeclared 1%/60-cell claim post hoc"
            ),
        },
    }
    write_result(args.output, result)
    print(json.dumps({
        "status": result["status"], "selected_bias": selected,
        "candidate_decisions": decisions, "output": str(args.output),
    }, indent=2))
    return 0 if selected is not None else 1


if __name__ == "__main__":
    raise SystemExit(main())
