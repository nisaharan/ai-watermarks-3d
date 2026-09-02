#!/usr/bin/env python3
"""Build the portable technical report for the failed Phase 2 confirmation gate."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = Path(__file__).resolve().parent


def load(relative: str):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def main() -> int:
    gate = load("results/phase2-confirmatory-null/confirmation-gate.json")
    diagnosis = load("results/phase2-confirmatory-null/failure-diagnosis.json")
    if gate["status"] != "confirmation_gate_failed":
        raise RuntimeError("Expected the frozen one-shot gate to be failed")
    if not gate["one_shot"] or gate["post_confirmation_retuning_authorized"]:
        raise RuntimeError("One-shot or no-retuning invariant is not preserved")
    if len(gate["cells"]) != 60 or any(item["samples"] != 5000 for item in gate["cells"]):
        raise RuntimeError("Gate cells are incomplete")
    failed = [item for item in gate["cells"] if not item["passed"]]
    if len(failed) != 18 or len(gate["failed_cells"]) != 18:
        raise RuntimeError("Failed-cell count does not reproduce")
    if diagnosis["status"] != "descriptive_failure_diagnosis_complete":
        raise RuntimeError("Failure diagnosis is not complete")
    if diagnosis["analysis_boundary"]["replacement_thresholds_produced"]:
        raise RuntimeError("Diagnosis must not produce replacement thresholds")

    generated_at = datetime.now(timezone.utc).isoformat()
    by_scheme = []
    for scheme in ("kgw", "synthid"):
        scheme_cells = [item for item in gate["cells"] if item["scheme"] == scheme]
        failed_cells = [item for item in scheme_cells if not item["passed"]]
        by_scheme.append(
            {
                "scheme": "KGW" if scheme == "kgw" else "SynthID",
                "passed": len(scheme_cells) - len(failed_cells),
                "failed": len(failed_cells),
                "total": len(scheme_cells),
            }
        )
    by_scheme_length = []
    for scheme in ("kgw", "synthid"):
        for length in (128, 256, 512):
            length_cells = [
                item
                for item in gate["cells"]
                if item["scheme"] == scheme and item["length"] == length
            ]
            failed_count = sum(not item["passed"] for item in length_cells)
            label = "KGW" if scheme == "kgw" else "SynthID"
            by_scheme_length.append(
                {
                    "condition": f"{label} {length}",
                    "scheme": label,
                    "length": length,
                    "failed": failed_count,
                    "passed": len(length_cells) - failed_count,
                    "total": len(length_cells),
                }
            )
    failed_rows = [
        {
            "scheme": "KGW" if item["scheme"] == "kgw" else "SynthID",
            "key": item["key_id"],
            "length": item["length"],
            "strict_exceedances": item["strict_exceedances"],
            "empirical_rate": item["empirical_rate"],
            "exact_upper_bound": item["exact_upper_bound"],
            "maximum_allowed": gate["acceptance"]["maximum_exceedances_per_5000"],
        }
        for item in failed
    ]
    max_cell = max(failed, key=lambda item: item["strict_exceedances"])
    headline = [
        {
            "passed_cells": 60 - len(failed),
            "failed_cells": len(failed),
            "kgw_failed": sum(item["scheme"] == "kgw" for item in failed),
            "synthid_failed": sum(item["scheme"] == "synthid" for item in failed),
            "maximum_observed_rate": max_cell["empirical_rate"],
            "maximum_upper_bound": max_cell["exact_upper_bound"],
        }
    ]
    scheme_split_means = []
    for item in diagnosis["by_scheme"]:
        label = "KGW" if item["scheme"] == "kgw" else "SynthID"
        for split in ("calibration", "confirmation"):
            scheme_split_means.append(
                {
                    "condition": f"{label} {split}",
                    "scheme": label,
                    "split": split,
                    "mean_exceedances": item[f"mean_{split}_exceedances"],
                    "maximum_allowed": gate["acceptance"]["maximum_exceedances_per_5000"],
                    "cells": item["cells"],
                    "failed_cells": item["failed_cells"],
                }
            )
    category_diagnostics = [
        {
            "category": item["category"],
            "calibration_score_rows": item["calibration_score_rows"],
            "calibration_rate": item["calibration_rate"],
            "confirmation_score_rows": item["confirmation_score_rows"],
            "confirmation_rate": item["confirmation_rate"],
            "rate_delta": item["rate_delta"],
        }
        for item in diagnosis["category_summary_across_failed_cell_score_rows"]
    ]
    power_scenarios = [
        {
            "sample_label": f"{item['samples_per_cell'] // 1000}k",
            "samples_per_cell": item["samples_per_cell"],
            "maximum_passing_exceedances": item["maximum_passing_exceedances"],
            "maximum_passing_empirical_rate": item["maximum_passing_empirical_rate"],
            "single_cell_95_rate": item[
                "maximum_true_fpr_for_95_percent_cell_pass_probability"
            ],
            "family_95_rate": item[
                "maximum_true_fpr_for_95_percent_family_pass_union_bound"
            ],
        }
        for item in diagnosis["fresh_study_power_scenarios"]
    ]

    sources = [
        {
            "id": "gate-artifact",
            "label": "Frozen one-shot confirmation gate",
            "path": "results/phase2-confirmatory-null/confirmation-gate.json",
            "query": {
                "description": "Load the immutable one-shot gate artifact; the report builder deterministically validates and reshapes its cells and failed_cells arrays into bounded report datasets.",
                "sql": "SELECT * FROM read_json_auto('results/phase2-confirmatory-null/confirmation-gate.json');",
                "language": "sql",
                "engine": "DuckDB",
                "executed_at": generated_at,
                "tables_used": ["results/phase2-confirmatory-null/confirmation-gate.json"],
                "filters": [
                    "all 60 primary confirmation cells",
                    "failed detail includes passed = false only",
                ],
                "metric_definitions": [
                    "A cell fails when its exact one-sided Clopper-Pearson upper bound exceeds 0.01.",
                    "Strict exceedances count scores strictly greater than the frozen operational threshold.",
                    "Empirical rate is strict exceedances divided by 5,000 confirmation observations.",
                ],
            },
        },
        {
            "id": "frozen-protocol",
            "label": "Frozen confirmatory-null protocol",
            "path": "configs/phase2-confirmatory-null.json",
        },
        {
            "id": "gate-evaluator",
            "label": "Threshold fitting and one-shot gate evaluator",
            "path": "src/ai_watermarks_phase2/calibration_gate.py",
        },
        {
            "id": "gate-tests",
            "label": "Automated acceptance-boundary tests",
            "path": "tests/test_confirmatory_null.py",
        },
        {
            "id": "failure-diagnosis",
            "label": "Descriptive calibration-confirmation failure diagnosis",
            "path": "results/phase2-confirmatory-null/failure-diagnosis.json",
            "query": {
                "description": "Load the reproducible descriptive diagnosis; the report builder selects its scheme, category and fresh-study power summaries without producing replacement thresholds.",
                "sql": "SELECT * FROM read_json_auto('results/phase2-confirmatory-null/failure-diagnosis.json');",
                "language": "sql",
                "engine": "DuckDB",
                "executed_at": generated_at,
                "tables_used": [
                    "results/phase2-confirmatory-null/failure-diagnosis.json",
                    "results/phase2-confirmatory-null/calibration/batches/*.json",
                    "results/phase2-confirmatory-null/confirmation/batches/*.json",
                ],
                "filters": [
                    "scores evaluated only at frozen operational thresholds",
                    "category summaries are descriptive only",
                    "power scenarios require genuinely fresh future splits",
                ],
                "metric_definitions": [
                    "Mean exceedances average the per-cell strict counts within each scheme and split.",
                    "Family 95% design rate is the largest true per-cell rate meeting a conservative union-bound probability that all 60 cells pass.",
                ],
            },
        },
    ]

    title = "Phase 2 Confirmatory Null Gate: Failed"
    cards = [
        {
            "id": "passed-cells",
            "dataset": "headline",
            "description": "Primary cells satisfying the frozen simultaneous confidence rule.",
            "sourceId": "gate-artifact",
            "metrics": [{"label": "Cells passed", "field": "passed_cells", "format": "number"}],
        },
        {
            "id": "failed-cells",
            "dataset": "headline",
            "description": "Any failure makes the global gate fail.",
            "sourceId": "gate-artifact",
            "metrics": [{"label": "Cells failed", "field": "failed_cells", "format": "number"}],
        },
        {
            "id": "kgw-failed",
            "dataset": "headline",
            "description": "Failed canonical KGW key-by-length cells out of 30.",
            "sourceId": "gate-artifact",
            "metrics": [{"label": "KGW cells failed", "field": "kgw_failed", "format": "number"}],
        },
        {
            "id": "synthid-failed",
            "dataset": "headline",
            "description": "Failed canonical SynthID key-by-length cells out of 30.",
            "sourceId": "gate-artifact",
            "metrics": [{"label": "SynthID cells failed", "field": "synthid_failed", "format": "number"}],
        },
        {
            "id": "max-rate",
            "dataset": "headline",
            "description": "Largest observed strict-exceedance rate among failed cells.",
            "sourceId": "gate-artifact",
            "metrics": [{"label": "Maximum observed rate", "field": "maximum_observed_rate", "format": "percent"}],
        },
        {
            "id": "max-upper",
            "dataset": "headline",
            "description": "Largest Bonferroni-controlled exact upper confidence bound.",
            "sourceId": "gate-artifact",
            "metrics": [{"label": "Maximum exact upper bound", "field": "maximum_upper_bound", "format": "percent"}],
        },
    ]
    tables = [
        {
            "id": "scheme-summary",
            "title": "Gate outcomes by scheme",
            "subtitle": "Each scheme contains ten keys at three paired prefix lengths.",
            "dataset": "scheme_summary",
            "sourceId": "gate-artifact",
            "defaultSort": {"field": "failed", "direction": "desc"},
            "density": "spacious",
            "layout": "full",
            "columns": [
                {"field": "scheme", "label": "Scheme", "type": "text"},
                {"field": "passed", "label": "Passed", "format": "number"},
                {"field": "failed", "label": "Failed", "format": "number"},
                {"field": "total", "label": "Total", "format": "number"},
            ],
        },
        {
            "id": "failed-detail",
            "title": "All 18 failed cells",
            "subtitle": "Exact confirmation outcomes; a maximum of 28 strict exceedances was allowed per 5,000 observations.",
            "dataset": "failed_cells",
            "sourceId": "gate-artifact",
            "defaultSort": {"field": "strict_exceedances", "direction": "desc"},
            "density": "dense",
            "layout": "full",
            "columns": [
                {"field": "scheme", "label": "Scheme", "type": "text"},
                {"field": "key", "label": "Key", "type": "text"},
                {"field": "length", "label": "Length", "format": "number"},
                {"field": "strict_exceedances", "label": "Exceedances", "format": "number"},
                {"field": "maximum_allowed", "label": "Maximum allowed", "format": "number"},
                {"field": "empirical_rate", "label": "Observed rate", "format": "percent"},
                {"field": "exact_upper_bound", "label": "Exact upper bound", "format": "percent"},
            ],
        },
        {
            "id": "category-diagnostics",
            "title": "Category rates across the 18 failed cells",
            "subtitle": "Paired score rows at frozen thresholds; descriptive only and not valid for category-specific retuning.",
            "dataset": "category_diagnostics",
            "sourceId": "failure-diagnosis",
            "defaultSort": {"field": "confirmation_rate", "direction": "desc"},
            "density": "dense",
            "layout": "full",
            "columns": [
                {"field": "category", "label": "Category", "type": "text"},
                {"field": "calibration_score_rows", "label": "Calibration score rows", "format": "number"},
                {"field": "calibration_rate", "label": "Calibration rate", "format": "percent"},
                {"field": "confirmation_score_rows", "label": "Confirmation score rows", "format": "number"},
                {"field": "confirmation_rate", "label": "Confirmation rate", "format": "percent"},
                {"field": "rate_delta", "label": "Rate delta", "format": "percent"},
            ],
        },
        {
            "id": "fresh-study-power",
            "title": "Fresh-study sample and margin scenarios",
            "subtitle": "Same 1% target, exact interval and 60-cell Bonferroni rule; these are planning scenarios, not an authorized run.",
            "dataset": "power_scenarios",
            "sourceId": "failure-diagnosis",
            "defaultSort": {"field": "samples_per_cell", "direction": "asc"},
            "density": "spacious",
            "layout": "full",
            "columns": [
                {"field": "samples_per_cell", "label": "Fresh observations per split", "format": "number"},
                {"field": "maximum_passing_exceedances", "label": "Maximum passing count", "format": "number"},
                {"field": "maximum_passing_empirical_rate", "label": "Maximum passing rate", "format": "percent"},
                {"field": "single_cell_95_rate", "label": "True rate for 95% cell pass", "format": "percent"},
                {"field": "family_95_rate", "label": "True rate for conservative 95% family pass", "format": "percent"},
            ],
        },
    ]
    charts = [
        {
            "id": "failures-by-scheme-length",
            "title": "Failed cells by scheme and prefix length",
            "subtitle": "Count failing the frozen simultaneous rule; ten keys were tested in each scheme-length condition.",
            "type": "bar",
            "dataset": "scheme_length_failures",
            "sourceId": "gate-artifact",
            "encodings": {
                "x": {"field": "condition", "type": "nominal", "label": "Scheme and prefix length"},
                "y": {"field": "failed", "type": "quantitative", "label": "Failed cells"},
            },
            "layout": "full",
        },
        {
            "id": "split-means-by-scheme",
            "title": "Mean strict exceedances by scheme and split",
            "subtitle": "Thirty cells per scheme; the frozen per-cell maximum was 28 exceedances out of 5,000.",
            "type": "bar",
            "dataset": "scheme_split_means",
            "sourceId": "failure-diagnosis",
            "encodings": {
                "x": {"field": "condition", "type": "nominal", "label": "Scheme and split"},
                "y": {"field": "mean_exceedances", "type": "quantitative", "label": "Mean exceedances per cell"},
            },
            "referenceLines": [{"value": 28, "label": "Maximum passing count"}],
            "layout": "full",
        },
        {
            "id": "fresh-family-margin",
            "title": "Conservative whole-family design margin by fresh sample size",
            "subtitle": "Largest true per-cell FPR compatible with at least 95% all-cell pass probability under a union-bound calculation.",
            "type": "bar",
            "dataset": "power_scenarios",
            "sourceId": "failure-diagnosis",
            "encodings": {
                "x": {"field": "sample_label", "type": "ordinal", "label": "Fresh observations per split"},
                "y": {"field": "family_95_rate", "type": "quantitative", "format": "percent", "label": "Design FPR"},
            },
            "layout": "full",
        },
    ]
    blocks = [
        {"id": "title", "type": "markdown", "layout": "full", "body": f"# {title}"},
        {
            "id": "technical-summary",
            "type": "markdown",
            "layout": "full",
            "sourceId": "gate-artifact",
            "body": "## Technical summary\n\n**Decision: stop.** The untouched 5,000-text confirmation split failed the predeclared simultaneous false-positive gate in 18 of 60 cells. The project cannot claim at-most-1% false-positive behavior across every tested scheme, key and length with 95% familywise confidence. Post-confirmation retuning, the watermarked-positive pilot and the attack corpus are prohibited under this protocol.",
        },
        {"id": "headline", "type": "metric-strip", "layout": "full", "cardIds": [card["id"] for card in cards]},
        {
            "id": "confidence-meaning",
            "type": "markdown",
            "layout": "full",
            "sourceId": "gate-artifact",
            "body": "## Failure means the guarantee was not established\n\nThe failed cells had observed exceedance rates from 0.58% to 0.96%, all below the 1% point target. They failed because their multiplicity-controlled exact upper confidence bounds exceeded 1%. The strongest supported conclusion is therefore that the strict simultaneous guarantee was not established—not that every failed cell's true rate is known to exceed 1%.",
        },
        {"id": "scheme-table", "type": "table", "layout": "full", "tableId": "scheme-summary"},
        {
            "id": "failed-pattern",
            "type": "markdown",
            "layout": "full",
            "sourceId": "gate-artifact",
            "body": "## Failure was concentrated in KGW but was not KGW-only\n\nKGW accounted for 14 failures and SynthID for four. The largest result was KGW key 03 at 512 tokens: 48 strict exceedances out of 5,000, an observed rate of 0.96% and an exact upper bound of 1.4761%. Exact cell values are retained below for audit; they must not be used to select keys or retune thresholds.",
        },
        {"id": "failure-chart", "type": "chart", "layout": "full", "chartId": "failures-by-scheme-length"},
        {"id": "detail-table", "type": "table", "layout": "full", "tableId": "failed-detail"},
        {
            "id": "scope-definitions",
            "type": "markdown",
            "layout": "full",
            "sourceId": "frozen-protocol",
            "body": "## Scope and decision rule\n\nThe study used 5,000 calibration and 5,000 disjoint confirmation prompts with unwatermarked SmolLM2-135M-Instruct generations. Canonical KGW SelfHash and SynthID-Text scores were evaluated under ten frozen keys at paired 128-, 256- and 512-token prefixes. A cell passed only when its exact one-sided Clopper-Pearson upper bound was at most 1% using Bonferroni-adjusted per-cell alpha 0.0008333333333333334. Strictly more than 28 threshold exceedances failed.",
        },
        {
            "id": "methodology",
            "type": "markdown",
            "layout": "full",
            "sourceId": "gate-evaluator",
            "body": "## One-shot methodology remained intact\n\nThe evaluator checked complete runs, protocol identity, threshold and protocol hashes, prompt-set disjointness, 60 complete cells and strict score-greater-than-threshold comparisons before writing the immutable gate artifact. KGW used key-specific length thresholds. SynthID used the frozen maximum of ten key-specific calibration candidates at each length and still gated every key separately.",
        },
        {
            "id": "margin-diagnosis",
            "type": "markdown",
            "layout": "full",
            "sourceId": "failure-diagnosis",
            "body": "## KGW failed mainly because calibration sat on the boundary\n\nTwenty-eight of 30 KGW calibration cells had exactly 28 exceedances, the maximum passing count. KGW averaged 27.9 exceedances in calibration and a slightly lower 27.7 in confirmation, yet 14 cells failed after ordinary cell-level fluctuation above the cutoff. At the fitted boundary rate of 0.56%, a new 5,000-sample cell has only about a 55.0% probability of passing. The design therefore had inadequate validation margin even without a broad upward KGW shift.",
        },
        {"id": "split-means-chart", "type": "chart", "layout": "full", "chartId": "split-means-by-scheme"},
        {
            "id": "category-warning",
            "type": "markdown",
            "layout": "full",
            "sourceId": "failure-diagnosis",
            "body": "## Classification tails require predeclared treatment in any new study\n\nClassification had the highest confirmation rate in 12 of the 18 failed cells. Across paired score rows from those failed cells, its rate was 1.22% in calibration and 1.40% in confirmation. Both splits contained the same 729 classification prompts, so this is not a mixture-weight change. The result remains descriptive: paired key and length scores are not independent, and categories were never primary gates.",
        },
        {"id": "category-table", "type": "table", "layout": "full", "tableId": "category-diagnostics"},
        {
            "id": "fresh-design",
            "type": "markdown",
            "layout": "full",
            "sourceId": "failure-diagnosis",
            "body": "## A fresh study needs both more information and a lower design rate\n\nLarger samples reduce the confidence penalty but cannot make a true 1% cell reliably prove it is at most 1%. Under the same rule, a conservative 95% whole-family design supports true per-cell rates near 0.30% at 5,000 fresh observations, 0.47% at 10,000, 0.60% at 20,000 and 0.74% at 50,000. These scenarios do not authorize generation; threshold sensitivity and compute cost must be resolved first.",
        },
        {"id": "fresh-margin-chart", "type": "chart", "layout": "full", "chartId": "fresh-family-margin"},
        {"id": "power-table", "type": "table", "layout": "full", "tableId": "fresh-study-power"},
        {
            "id": "limitations",
            "type": "markdown",
            "layout": "full",
            "sourceId": "gate-artifact",
            "body": "## Interpretation limits\n\nThis is a null-control result for one pinned small model, decoder policy, key schedule and three length bins. It does not overturn canonical implementation parity, measure watermark detection power, or test attacks. Category rates are diagnostic only. The confirmation split cannot be converted into tuning data without invalidating the one-shot design.",
        },
        {
            "id": "next-steps",
            "type": "markdown",
            "layout": "full",
            "body": "## Recommended next steps\n\n1. Preserve the protocol, thresholds, split artifacts and failed gate unchanged.\n2. Confirm whether the strict 60-cell at-most-1% claim remains scientifically necessary.\n3. If it remains, predeclare a lower design FPR, desired whole-family pass probability and category treatment.\n4. Assess the detection-sensitivity cost using development evidence only; confirmation remains report-only.\n5. Choose a fresh sample size and compute budget, then preregister an entirely new protocol.\n6. Do not run the positive pilot or attack corpus under the failed protocol.",
        },
        {
            "id": "further-questions",
            "type": "markdown",
            "layout": "full",
            "body": "## Further questions\n\n- Is the same 60-cell familywise guarantee still the scientifically necessary target?\n- How large must a new fresh null sample be to support that target with useful power?\n- Should a future protocol predeclare a different operating claim while keeping keys and variants explicit?\n- Which descriptive diagnostics can explain the calibration-to-confirmation shift without becoming tuning inputs?",
        },
    ]

    manifest = {
        "version": 1,
        "surface": "report",
        "title": title,
        "description": "Technical report for the frozen one-shot Phase 2 confirmatory-null decision.",
        "generatedAt": generated_at,
        "sources": sources,
        "cards": cards,
        "charts": charts,
        "tables": tables,
        "blocks": blocks,
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
                "scheme_summary": by_scheme,
                "scheme_length_failures": by_scheme_length,
                "failed_cells": failed_rows,
                "scheme_split_means": scheme_split_means,
                "category_diagnostics": category_diagnostics,
                "power_scenarios": power_scenarios,
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
