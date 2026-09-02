#!/usr/bin/env python3
"""Diagnose whether KGW empirical-null displacement is key-specific."""

from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path
from typing import Any

from ai_watermarks_phase2 import canonical
from ai_watermarks_phase2.native import require_ml_dependencies
from ai_watermarks_phase2.smoke import load_json

DEFAULT_KEYS = [15485863, 32452843, 49979687, 67867967, 86028121]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--result", type=Path, default=Path("results/phase2-null-calibration/run.json")
    )
    parser.add_argument("--samples", type=int, default=100)
    parser.add_argument("--keys", type=int, nargs="+", default=DEFAULT_KEYS)
    parser.add_argument(
        "--output", type=Path, default=Path("results/phase2-null-calibration/key-diagnostic.json")
    )
    args = parser.parse_args()

    result = load_json(args.result)
    records = result["records"][: args.samples]
    if not records:
        raise ValueError("No calibration records available")
    smoke_config = load_json(Path(result["config"]["watermark_config"]))
    torch, transformers = require_ml_dependencies()
    model_config = transformers.AutoConfig.from_pretrained(
        smoke_config["model"]["id"], revision=smoke_config["model"]["revision"]
    )
    eligible_ngrams = []
    reported_base = []
    for record in records:
        score = next(item for item in record["native_scores"] if item["scheme"] == "kgw")
        eligible_ngrams.append(
            [row["context_token_ids"] for row in score["position_traces"] if row["eligible"]]
        )
        reported_base.append(float(score["value"]))

    diagnostics: list[dict[str, Any]] = []
    for key in args.keys:
        settings = dict(smoke_config["kgw"], hashing_key=key)
        config = canonical.build_kgw_config(settings, canonical.KGW_AUTHOR_VARIANT)
        processor = config.construct_processor(
            model_config.vocab_size, smoke_config["model"]["device"]
        )
        scored: list[int] = []
        hits: list[int] = []
        for record_ngrams in eligible_ngrams:
            scored.append(len(record_ngrams))
            record_hits = 0
            for ngram in record_ngrams:
                tensor = torch.tensor(ngram, dtype=torch.long)
                record_hits += int(ngram[-1] in processor._get_greenlist_ids(tensor))
            hits.append(record_hits)
        gamma = float(settings["greenlist_ratio"])
        z_scores = [
            float((hit - gamma * count) / math.sqrt(count * gamma * (1 - gamma)))
            for count, hit in zip(scored, hits, strict=True)
        ]
        diagnostics.append(
            {
                "hashing_key": key,
                "samples": len(z_scores),
                "mean_z": statistics.fmean(z_scores),
                "sample_variance_z": statistics.variance(z_scores),
                "aggregate_green_rate": float(sum(hits) / sum(scored)),
                "matches_stored_base_scores": key == int(smoke_config["kgw"]["hashing_key"])
                and all(
                    math.isclose(left, right, rel_tol=0.0, abs_tol=1e-12)
                    for left, right in zip(z_scores, reported_base, strict=True)
                ),
            }
        )

    report = {
        "schema_version": 1,
        "scope": "KGW key-sensitivity diagnostic; not a benchmark result",
        "source_result": str(args.result),
        "sample_selection": f"first {len(records)} records from frozen hash-randomized manifest",
        "variant": canonical.KGW_AUTHOR_VARIANT,
        "diagnostics": diagnostics,
        "across_key_mean_z": statistics.fmean(item["mean_z"] for item in diagnostics),
        "across_key_range_z": [
            min(item["mean_z"] for item in diagnostics),
            max(item["mean_z"] for item in diagnostics),
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
