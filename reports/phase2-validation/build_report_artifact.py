#!/usr/bin/env python3
"""Build the canonical portable-report artifact for the Phase 2 gate decision."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = Path(__file__).resolve().parent


def load(relative: str):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def effect_map(analysis):
    return {
        (item["scheme"], item["length"]): item
        for item in analysis["key_effects"]
    }


def cell_map(analysis, scheme: str, length: int):
    return {
        item["key_id"]: item
        for item in analysis["cell_summaries"]
        if item["scheme"] == scheme and item["length"] == length
    }


def theoretical_map(analysis, length: int):
    return {
        item["key_id"]: item["one_sided_1_percent"]["empirical_rate"]
        for item in analysis["theoretical_kgw_tails"]
        if item["length"] == length
    }


def main() -> int:
    primary = load("results/phase2-variance-pilot/analysis.json")
    replication = load("results/phase2-variance-replication/analysis.json")
    if not primary["validation"]["passed"] or not replication["validation"]["passed"]:
        raise RuntimeError("Both source analyses must pass validation before reporting")

    primary_effects = effect_map(primary)
    replication_effects = effect_map(replication)
    primary_cells = cell_map(primary, "kgw", 512)
    replication_cells = cell_map(replication, "kgw", 512)
    primary_fpr = theoretical_map(primary, 512)
    replication_fpr = theoretical_map(replication, 512)
    key_ids = sorted(primary_cells)
    generated_at = datetime.now(timezone.utc).isoformat()

    sources = [
        {
            "id": "combined-analysis",
            "label": "Validated Phase 2 primary and replication analyses",
            "path": "validation/analyse_phase2_variance.py",
            "query": {
                "description": "DuckDB loads both validated JSON analyses; build_report_artifact.py deterministically selects and reshapes their validated cell_summaries, key_effects and theoretical_kgw_tails into the bounded report datasets.",
                "sql": "SELECT 'primary' AS run, * FROM read_json_auto('results/phase2-variance-pilot/analysis.json')\nUNION ALL BY NAME\nSELECT 'replication' AS run, * FROM read_json_auto('results/phase2-variance-replication/analysis.json');",
                "language": "sql",
                "engine": "DuckDB",
                "executed_at": generated_at,
                "tables_used": [
                    "results/phase2-variance-pilot/run.json",
                    "results/phase2-variance-replication/run.json",
                ],
                "filters": [
                    "unwatermarked condition only",
                    "paired generated-token prefixes at 128, 256 and 512",
                    "ten frozen detector keys per watermark family",
                ],
                "metric_definitions": [
                    "KGW score is the canonical SelfHash green-token z statistic.",
                    "SynthID score is the mean canonical g-value over eligible positions and depth.",
                    "Empirical FPR is the share of null scores strictly above the declared cutoff.",
                ],
            },
        },
        {
            "id": "executed-notebook",
            "label": "Executed analysis notebook",
            "path": "notebooks/phase2-variance-pilot.ipynb",
        },
        {
            "id": "qwen-model-card",
            "label": "Qwen2.5-0.5B-Instruct model card",
            "href": "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct/tree/7ae557604adf67be50417f59c2c2f167def9a775",
        },
    ]

    headline = [{
        "primary_null_prompts": 500,
        "replication_null_prompts": 104,
        "validated_score_rows": 36240,
        "primary_max_nominal_1pct_fpr": max(primary_fpr.values()),
        "replication_max_nominal_1pct_fpr": max(replication_fpr.values()),
        "planned_nulls_per_1pct_cell": 5000,
    }]
    kgw_means = [
        {
            "key": key_id.removeprefix("kgw-"),
            "SmolLM2_n500": primary_cells[key_id]["mean"],
            "Qwen2_5_n104": replication_cells[key_id]["mean"],
        }
        for key_id in key_ids
    ]
    kgw_fprs = [
        {
            "key": key_id.removeprefix("kgw-"),
            "SmolLM2_n500": primary_fpr[key_id],
            "Qwen2_5_n104": replication_fpr[key_id],
            "target": 0.01,
        }
        for key_id in key_ids
    ]
    key_effect_rows = []
    for model, effects in (
        ("SmolLM2-135M-Instruct", primary["key_effects"]),
        ("Qwen2.5-0.5B-Instruct", replication["key_effects"]),
    ):
        for item in effects:
            key_effect_rows.append(
                {
                    "model": model,
                    "scheme": item["scheme"],
                    "length": item["length"],
                    "mean_across_keys": item["mean_across_key_means"],
                    "between_key_sd": item["between_key_standard_deviation"],
                    "minimum_key_mean": item["minimum_key_mean"],
                    "maximum_key_mean": item["maximum_key_mean"],
                    "key_mean_range": item["key_mean_range"],
                    "keys_beyond_3se": item["keys_beyond_three_standard_errors"],
                }
            )

    title = "Phase 2 Watermark Null Calibration: Gate Decision"
    manifest = {
        "version": 1,
        "surface": "report",
        "title": title,
        "description": "Technical validation report for canonical KGW SelfHash and SynthID-Text null calibration.",
        "generatedAt": generated_at,
        "sources": sources,
        "cards": [
            {
                "id": "primary-prompts",
                "dataset": "headline",
                "description": "Independent unwatermarked outputs in the primary SmolLM2 variance pilot.",
                "sourceId": "combined-analysis",
                "metrics": [{"label": "Primary null prompts", "field": "primary_null_prompts", "format": "number"}],
            },
            {
                "id": "replication-prompts",
                "dataset": "headline",
                "description": "Balanced unwatermarked outputs in the independent Qwen2.5 replication.",
                "sourceId": "combined-analysis",
                "metrics": [{"label": "Replication null prompts", "field": "replication_null_prompts", "format": "number"}],
            },
            {
                "id": "validated-rows",
                "dataset": "headline",
                "description": "All scheme × key × length score rows passing the locked validation checks.",
                "sourceId": "combined-analysis",
                "metrics": [{"label": "Validated score rows", "field": "validated_score_rows", "format": "compact"}],
            },
            {
                "id": "primary-max-fpr",
                "dataset": "headline",
                "description": "Largest key-specific false-positive rate under the nominal one-sided 1% KGW threshold at 512 tokens.",
                "sourceId": "combined-analysis",
                "metrics": [{"label": "Primary max nominal 1% FPR", "field": "primary_max_nominal_1pct_fpr", "format": "percent"}],
            },
            {
                "id": "replication-max-fpr",
                "dataset": "headline",
                "description": "Independent-model replication of the largest key-specific nominal 1% KGW false-positive rate at 512 tokens.",
                "sourceId": "combined-analysis",
                "metrics": [{"label": "Replication max nominal 1% FPR", "field": "replication_max_nominal_1pct_fpr", "format": "percent"}],
            },
            {
                "id": "confirmatory-n",
                "dataset": "headline",
                "description": "Planned independent null texts in each of two disjoint primary 1% FPR splits: calibration and confirmation.",
                "sourceId": "combined-analysis",
                "metrics": [{"label": "Planned nulls per 1% cell", "field": "planned_nulls_per_1pct_cell", "format": "compact"}],
            },
        ],
        "charts": [
            {
                "id": "kgw-key-means",
                "title": "KGW null means by frozen detector key at 512 tokens",
                "subtitle": "Both model families show material key-dependent offsets from the zero reference.",
                "type": "line",
                "dataset": "kgw_key_means",
                "sourceId": "combined-analysis",
                "encodings": {
                    "x": {"field": "key", "type": "ordinal", "label": "Frozen key index"},
                    "y": {"fields": ["SmolLM2_n500", "Qwen2_5_n104"], "type": "quantitative", "label": "Mean KGW z-score"},
                },
                "referenceLines": [{"value": 0, "label": "Theoretical null mean"}],
                "layout": "full",
            },
            {
                "id": "kgw-nominal-fpr",
                "title": "Realised KGW FPR under the nominal 1% threshold at 512 tokens",
                "subtitle": "A shared standard-normal cutoff fails to control false positives for individual keys.",
                "type": "line",
                "dataset": "kgw_nominal_fpr",
                "sourceId": "combined-analysis",
                "encodings": {
                    "x": {"field": "key", "type": "ordinal", "label": "Frozen key index"},
                    "y": {"fields": ["SmolLM2_n500", "Qwen2_5_n104", "target"], "type": "quantitative", "format": "percent", "label": "Empirical FPR"},
                },
                "layout": "full",
            },
        ],
        "tables": [
            {
                "id": "key-effects-table",
                "title": "Key-effect summary by model, scheme and length",
                "subtitle": "Exact aggregate values from the validated primary and replication analyses.",
                "dataset": "key_effects",
                "sourceId": "combined-analysis",
                "defaultSort": {"field": "key_mean_range", "direction": "desc"},
                "density": "dense",
                "layout": "full",
                "columns": [
                    {"field": "model", "label": "Model", "type": "text"},
                    {"field": "scheme", "label": "Scheme", "type": "text"},
                    {"field": "length", "label": "Length", "format": "number"},
                    {"field": "mean_across_keys", "label": "Mean across keys", "format": "number"},
                    {"field": "between_key_sd", "label": "Between-key SD", "format": "number"},
                    {"field": "minimum_key_mean", "label": "Minimum key mean", "format": "number"},
                    {"field": "maximum_key_mean", "label": "Maximum key mean", "format": "number"},
                    {"field": "key_mean_range", "label": "Key-mean range", "format": "number"},
                    {"field": "keys_beyond_3se", "label": "Keys beyond 3 SE", "format": "number"},
                ],
            }
        ],
        "blocks": [
            {"id": "title", "type": "markdown", "layout": "full", "body": f"# {title}"},
            {
                "id": "technical-summary",
                "type": "markdown",
                "layout": "full",
                "sourceId": "combined-analysis",
                "body": "## Technical summary\n\n**Decision: no-go for the full attack corpus.** Canonical implementation parity passes, but KGW's nominal and pooled multi-key thresholds do not control key-specific false-positive risk. Keep the canonical code unchanged and require detector-key × model × length-bin empirical calibration with held-out confirmation. SynthID remains materially more key-stable across both tested model families.",
            },
            {"id": "headline-metrics", "type": "metric-strip", "layout": "full", "cardIds": ["primary-prompts", "replication-prompts", "validated-rows", "primary-max-fpr", "replication-max-fpr", "confirmatory-n"]},
            {"id": "key-finding-heading", "type": "markdown", "layout": "full", "body": "## Key findings\n\nThe same frozen ten-key schedule was applied to paired 128-, 256- and 512-token prefixes. The two charts below show the decisive 512-token result."},
            {"id": "means-chart", "type": "chart", "layout": "full", "chartId": "kgw-key-means"},
            {"id": "fpr-chart", "type": "chart", "layout": "full", "chartId": "kgw-nominal-fpr"},
            {
                "id": "scope-data-definitions",
                "type": "markdown",
                "layout": "full",
                "sourceId": "combined-analysis",
                "body": "## Scope, data and definitions\n\nThe primary pilot contains 500 unwatermarked SmolLM2 outputs. The independent replication contains 104 Qwen2.5 outputs balanced at 13 prompts in each of eight Dolly task categories. One 512-token continuation per prompt supplied paired 128/256/512-token prefixes. Each prefix was scored under ten KGW keys and ten SynthID key vectors. KGW's statistic is the canonical SelfHash green-token z-score; SynthID's statistic is the mean canonical g-value over eligible positions and watermark depth.",
            },
            {
                "id": "methodology",
                "type": "markdown",
                "layout": "full",
                "sourceId": "combined-analysis",
                "body": "## Methodology\n\nInputs and key schedules were frozen before scoring. Generation was seeded and checkpointed atomically. Validation required complete planned records, exact category allocation, exact prefix shape, unique scheme × key × length cells, finite positive-position scores, exact aggregate reconstruction and compact/native trace agreement. The Qwen replication ran in a fresh lockfile-derived isolated environment. Empirical cutoffs estimated and evaluated on the same samples are reported only as development diagnostics; they are not confirmatory thresholds.",
            },
            {"id": "effects-table", "type": "table", "layout": "full", "tableId": "key-effects-table"},
            {
                "id": "limitations",
                "type": "markdown",
                "layout": "full",
                "sourceId": "combined-analysis",
                "body": "## Limitations and robustness\n\nThe ten key scores for a text are paired, not 10 independent null texts. The 500-prompt primary cell provides only five expected exceedances at 1% FPR, with a Wilson 95% interval of approximately 0.43%–2.32%; the 104-prompt replication tests the mean/key pattern but is not sized for tail calibration. Results cover two small open model families and three length bins. Attack-condition variance is not yet measured, so attack power remains provisional. The documented SynthID top-k boundary-tie difference remains a decoder-policy difference and is outside this calibration defect.",
            },
            {
                "id": "recommended-next",
                "type": "markdown",
                "layout": "full",
                "sourceId": "combined-analysis",
                "body": "## Recommended next steps\n\n1. Freeze disjoint 5,000-prompt calibration and 5,000-prompt confirmation manifests.\n2. Generate the 10,000 primary-model null outputs and score all frozen keys at every length.\n3. Freeze KGW thresholds by detector key × model × length bin on calibration data; evaluate once on untouched confirmation data.\n4. If false-positive calibration passes, run a small repeated watermarked-positive/attacked-positive variance pilot and finalise attack sample sizes.\n5. Only then open the full attack corpus.\n\nDo not prioritise 0.1% FPR yet: approximately 43,000 nulls per split and cell would be required for the same relative precision goal.",
            },
            {
                "id": "further-questions",
                "type": "markdown",
                "layout": "full",
                "body": "## Further questions\n\n- How transferable are key-conditional KGW thresholds across larger model families and decoding policies?\n- Can a hierarchical calibration model reduce sample cost without losing per-key FPR control?\n- Does category-conditioned language structure explain part of the residual key shift?\n- After calibration, how much repeated-positive variance is needed for each attack family?",
            },
        ],
    }

    artifact = {
        "surface": "report",
        "manifest": manifest,
        "snapshot": {
            "version": 1,
            "generatedAt": generated_at,
            "status": "ready",
            "datasets": {
                "headline": headline,
                "kgw_key_means": kgw_means,
                "kgw_nominal_fpr": kgw_fprs,
                "key_effects": key_effect_rows,
            },
        },
        "sources": sources,
    }
    output = REPORT_DIR / "artifact.json"
    output.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    print(output.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
