"""Run the frozen Phase 2 empirical-null development calibration."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import canonical
from .native import TransformersNativeRunner
from .smoke import git_commit, git_dirty, load_json, sha256_text, source_tree_sha256
from .trace_validation import trace_is_consistent


def _quantile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    index = max(0, math.ceil(probability * len(ordered)) - 1)
    return ordered[index]


def _wilson_interval(successes: int, trials: int, z: float = 1.959963984540054) -> list[float]:
    rate = successes / trials
    denominator = 1.0 + z * z / trials
    centre = (rate + z * z / (2.0 * trials)) / denominator
    half_width = z * math.sqrt(
        rate * (1.0 - rate) / trials + z * z / (4.0 * trials * trials)
    ) / denominator
    return [centre - half_width, centre + half_width]


def _tail_diagnostic(values: list[float], target: float) -> dict[str, Any]:
    cutoff = _quantile(values, 1.0 - target)
    exceedances = sum(value > cutoff for value in values)
    return {
        "target_fpr": target,
        "cutoff": cutoff,
        "decision_rule": "score_strictly_greater_than_cutoff",
        "exceedances": exceedances,
        "empirical_rate": exceedances / len(values),
        "wilson_95_percent": _wilson_interval(exceedances, len(values)),
    }


def summarize(records: list[dict[str, Any]], fpr_targets: list[float]) -> dict[str, Any]:
    summaries: dict[str, Any] = {}
    for scheme in ("kgw", "synthid"):
        values: list[float] = []
        eligible: list[int] = []
        by_category: dict[str, list[float]] = defaultdict(list)
        for record in records:
            score = next(item for item in record["native_scores"] if item["scheme"] == scheme)
            value = float(score["value"])
            values.append(value)
            eligible.append(int(score["eligible_positions"]))
            by_category[record["category"]].append(value)
        mean = statistics.fmean(values)
        variance = statistics.variance(values)
        null_reference = 0.0 if scheme == "kgw" else 0.5
        standard_error = math.sqrt(variance / len(values))
        summaries[scheme] = {
            "samples": len(values),
            "mean": mean,
            "sample_variance": variance,
            "null_mean_reference": null_reference,
            "mean_standard_error": standard_error,
            "mean_reference_deviation_in_standard_errors": (
                mean - null_reference
            ) / standard_error,
            "eligible_positions": {
                "minimum": min(eligible),
                "median": statistics.median(eligible),
                "maximum": max(eligible),
            },
            "development_upper_tail_cutoffs": {
                str(target): _tail_diagnostic(values, target) for target in fpr_targets
            },
            "category_means": {
                category: statistics.fmean(category_values)
                for category, category_values in sorted(by_category.items())
            },
        }
    return summaries


def _write_result(path: Path, result: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path, default=Path("configs/phase2-null-calibration.json")
    )
    parser.add_argument(
        "--prompts", type=Path, default=Path("data/phase2-null-calibration-prompts.json")
    )
    parser.add_argument(
        "--output", type=Path, default=Path("results/phase2-null-calibration/run.json")
    )
    parser.add_argument("--limit", type=int)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--resume", action="store_true", help="Continue from complete batches in --output"
    )
    args = parser.parse_args(argv)

    config = load_json(args.config)
    prompt_manifest = load_json(args.prompts)
    prompts = prompt_manifest["records"]
    target = int(config["selection"]["target_samples"])
    if len(prompts) != target:
        raise ValueError(f"Frozen manifest must contain {target} prompts, found {len(prompts)}")
    limit = target if args.limit is None else args.limit
    if not 1 <= limit <= target:
        parser.error(f"--limit must be between 1 and {target}")
    if args.dry_run:
        print(json.dumps({"status": "configuration_valid", "prompts": len(prompts), "selected": limit}, indent=2))
        return 0

    smoke_config = load_json(Path(config["watermark_config"]))
    if config["variants"] != smoke_config["variants"]:
        raise ValueError("Calibration and watermark configurations declare different variants")
    input_sha256 = {
        "calibration_config": _file_sha256(args.config),
        "prompt_manifest": _file_sha256(args.prompts),
        "watermark_config": _file_sha256(Path(config["watermark_config"])),
    }
    records: list[dict[str, Any]] = []
    if args.resume and args.output.exists():
        previous = load_json(args.output)
        if previous.get("input_sha256") != input_sha256:
            raise ValueError("Cannot resume: input fingerprints differ from the partial run")
        records = previous.get("records", [])
        expected_ids = [item["id"] for item in prompts[: len(records)]]
        observed_ids = [item["prompt_id"] for item in records]
        if observed_ids != expected_ids:
            raise ValueError("Cannot resume: stored records are not the frozen prompt prefix")
    if len(records) >= limit:
        previous["summary"] = summarize(
            records, [float(value) for value in config["analysis"]["development_fpr_targets"]]
        )
        _write_result(args.output, previous)
        print(
            json.dumps(
                {"status": "already_complete", "records": len(records), "output": str(args.output)},
                indent=2,
            )
        )
        return 0

    runner = TransformersNativeRunner(
        model_id=smoke_config["model"]["id"],
        revision=smoke_config["model"]["revision"],
        device=smoke_config["model"]["device"],
    )
    kgw_variant = config["variants"]["kgw"]
    synthid_variant = config["variants"]["synthid"]
    kgw_config = canonical.build_kgw_config(smoke_config["kgw"], kgw_variant)
    synthid_config = canonical.build_synthid_config(smoke_config["synthid"], synthid_variant)
    generation = config["generation"]
    batch_size = int(generation["batch_size"])
    if records and len(records) % batch_size:
        raise ValueError("Cannot resume from an incomplete batch")
    selected = prompts[:limit]

    for batch_start in range(len(records), len(selected), batch_size):
        batch = selected[batch_start : batch_start + batch_size]
        batch_index = batch_start // batch_size
        batch_seed = int(generation["base_seed"]) + batch_index
        generated = runner.generate_batch(
            [item["prompt"] for item in batch],
            seed=batch_seed,
            min_new_tokens=int(generation["min_new_tokens"]),
            max_new_tokens=int(generation["max_new_tokens"]),
            temperature=float(generation["temperature"]),
            top_k=int(generation["top_k"]),
            watermark_config=None,
        )
        for stream_index, (prompt, output) in enumerate(zip(batch, generated, strict=True)):
            _, continuation, text = output
            kgw_score = runner.score_kgw(
                continuation,
                first_generated_position=0,
                config=kgw_config,
                variant=kgw_variant,
                ignore_repeated_ngrams=True,
            )
            synthid_score = runner.score_synthid(
                continuation,
                first_generated_position=0,
                config=synthid_config,
                variant=synthid_variant,
            )
            native_scores = [kgw_score.to_dict(), synthid_score.to_dict()]
            if not all(trace_is_consistent(score, len(continuation)) for score in native_scores):
                raise RuntimeError(f"Trace reconstruction failed for {prompt['id']}")
            records.append(
                {
                    "prompt_id": prompt["id"],
                    "source_row": prompt["source_row"],
                    "category": prompt["category"],
                    "prompt_sha256": prompt["prompt_sha256"],
                    "condition": "unwatermarked",
                    "batch_seed": batch_seed,
                    "batch_stream_index": stream_index,
                    "generated_tokens": len(continuation),
                    "output_sha256": sha256_text(text),
                    "text": text,
                    "native_scores": native_scores,
                }
            )
        partial = {
            "schema_version": 1,
            "status": "calibration_complete" if len(records) == target else "calibration_partial",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "scope": config["scope"],
            "config": config,
            "prompt_manifest_source": str(args.prompts),
            "input_sha256": input_sha256,
            "environment": {
                "git_commit": git_commit(),
                "git_dirty": git_dirty(),
                "source_tree_sha256": source_tree_sha256(),
            },
            "category_counts": dict(sorted(Counter(row["category"] for row in records).items())),
            "records": records,
        }
        if records:
            partial["summary"] = summarize(
                records, [float(value) for value in config["analysis"]["development_fpr_targets"]]
            )
        _write_result(args.output, partial)

    print(json.dumps({"status": partial["status"], "records": len(records), "output": str(args.output)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
