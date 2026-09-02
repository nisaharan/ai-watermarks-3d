#!/usr/bin/env python3
"""Build the portable technical report for the v2 positive-sensitivity screen."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = Path(__file__).resolve().parent


def load(relative: str):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def main() -> int:
    analysis = load("results/phase2-v2-positive-sensitivity/analysis.json")
    frontier = load("results/phase2-v2-positive-sensitivity/margin-frontier.json")
    run = load("results/phase2-v2-positive-sensitivity/run/run.json")
    config = load("configs/phase2-v2-positive-sensitivity.json")
    if analysis["status"] != "sensitivity_screen_failed":
        raise RuntimeError("Expected the predeclared screen to be failed")
    if len(analysis["cells"]) != 60 or len(analysis["failed_cells"]) != 5:
        raise RuntimeError("Sensitivity cells do not reproduce")
    if run["status"] != "positive_sensitivity_complete":
        raise RuntimeError("Positive run is incomplete")
    if run["completed_outputs"] != 1000 or run["completed_batches"] != 200:
        raise RuntimeError("Positive run count differs from the frozen design")
    if run["confirmation_scores_used"] is not False:
        raise RuntimeError("Confirmation separation is not preserved")
    if len(run["native_score_audits"]) != 60 or not all(
        row["exact"] for row in run["native_score_audits"]
    ):
        raise RuntimeError("Matched compact/native parity audits are incomplete")
    if frontier["lowest_grid_margin_meeting_both_development_criteria"] is not None:
        raise RuntimeError("Expected no tested margin to meet both criteria")

    generated_at = datetime.now(timezone.utc).isoformat()
    failed = analysis["failed_cells"]
    cells = analysis["cells"]
    headline = [
        {
            "passed_cells": 60 - len(failed),
            "failed_cells": len(failed),
            "minimum_rate": min(row["detection_rate"] for row in cells),
            "synthid_passed": sum(
                row["scheme"] == "synthid" and row["passed"] for row in cells
            ),
            "outputs": run["completed_outputs"],
        }
    ]
    failed_rows = [
        {
            "scheme": "KGW" if row["scheme"] == "kgw" else "SynthID",
            "key": row["key_id"],
            "length": row["length"],
            "detections": row["strict_detections"],
            "samples": 50,
            "detection_rate": row["detection_rate"],
            "required_rate": config["screen"]["minimum_detection_rate_per_cell"],
        }
        for row in failed
    ]
    kgw_rates = [
        {
            "key": row["key_id"].replace("kgw-", "KGW "),
            "key_id": row["key_id"],
            "length": str(row["length"]),
            "detection_rate": row["detection_rate"],
            "detections": row["strict_detections"],
            "samples": row["samples"],
            "required_rate": config["screen"]["minimum_detection_rate_per_cell"],
            "passed": row["passed"],
        }
        for row in cells
        if row["scheme"] == "kgw"
    ]
    summaries = [
        {
            "scheme": "KGW" if row["scheme"] == "kgw" else "SynthID",
            "length": row["length"],
            "minimum_rate": row["minimum_cell_rate"],
            "median_rate": row["median_cell_rate"],
            "maximum_rate": row["maximum_cell_rate"],
        }
        for row in analysis["scheme_length_summaries"]
    ]
    frontier_rows = [
        {
            "design_fpr": row["design_fpr"],
            "calibration_count": row[
                "calibration_maximum_strict_exceedances_at_n5000"
            ],
            "failed_positive_cells": row["failed_positive_screen_cells"],
            "minimum_positive_rate": row["minimum_positive_detection_rate"],
            "median_positive_rate": row["median_positive_detection_rate"],
            "conservative_family_power": row[
                "conservative_60_cell_confirmation_pass_power_if_true_rates_equal_design_fpr"
            ],
        }
        for row in frontier["scenarios"]
    ]

    sources = [
        {
            "id": "sensitivity-analysis",
            "label": "Completed positive-sensitivity screen",
            "path": "results/phase2-v2-positive-sensitivity/analysis.json",
            "query": {
                "description": "Load all 60 completed matched-key cells and apply the predeclared threshold and minimum-detection rule.",
                "sql": "SELECT * FROM read_json_auto('results/phase2-v2-positive-sensitivity/analysis.json');",
                "language": "sql",
                "engine": "DuckDB",
                "executed_at": generated_at,
                "tables_used": [
                    "results/phase2-v2-positive-sensitivity/analysis.json"
                ],
                "filters": [
                    "all 60 scheme x key x prefix-length cells",
                    "50 fresh watermarked outputs per cell",
                    "strict score > provisional threshold",
                ],
                "metric_definitions": [
                    "Detection rate is strict detections divided by 50 outputs in the named cell.",
                    "The development screen requires at least 40 detections out of 50 in every cell.",
                ],
            },
        },
        {
            "id": "margin-frontier",
            "label": "Post-screen margin-sensitivity frontier",
            "path": "results/phase2-v2-positive-sensitivity/margin-frontier.json",
            "query": {
                "description": "Recalculate calibration-only provisional thresholds over a fixed 0.5%-0.8% design-FPR grid and evaluate the completed positive outputs without loading v1 confirmation scores.",
                "sql": "SELECT * FROM read_json_auto('results/phase2-v2-positive-sensitivity/margin-frontier.json');",
                "language": "sql",
                "engine": "DuckDB",
                "executed_at": generated_at,
                "tables_used": [
                    "results/phase2-confirmatory-null/calibration/batches/*.json",
                    "results/phase2-v2-positive-sensitivity/run/batches/*.json",
                ],
                "filters": [
                    "v1 calibration scores only; v1 confirmation prohibited",
                    "design-FPR grid 0.5%-0.8%",
                    "20,000-observation confirmation planning with 156 maximum exceedances",
                ],
                "metric_definitions": [
                    "Conservative family pass power uses one minus 60 times the single-cell failure probability, floored at zero.",
                    "A margin meets both development criteria only if no positive cell fails and conservative family pass power is at least 95%.",
                ],
            },
        },
        {
            "id": "pilot-config",
            "label": "Predeclared positive-sensitivity protocol",
            "path": "configs/phase2-v2-positive-sensitivity.json",
        },
        {
            "id": "completed-run",
            "label": "Completed positive-sensitivity run metadata",
            "path": "results/phase2-v2-positive-sensitivity/run/run.json",
            "query": {
                "description": "Load terminal run metadata and verify complete output, batch, scheme-count and parity-audit totals.",
                "sql": "SELECT * FROM read_json_auto('results/phase2-v2-positive-sensitivity/run/run.json');",
                "language": "sql",
                "engine": "DuckDB",
                "executed_at": generated_at,
                "tables_used": [
                    "results/phase2-v2-positive-sensitivity/run/run.json",
                    "results/phase2-v2-positive-sensitivity/run/batches/*.json",
                ],
                "filters": ["terminal positive_sensitivity_complete run only"],
                "metric_definitions": [
                    "Completed outputs are the count of watermarked generations across all atomic batches."
                ],
            },
        },
        {
            "id": "analysis-code",
            "label": "Positive-sensitivity evaluator",
            "path": "validation/analyse_phase2_v2_positive_sensitivity.py",
        },
    ]
    cards = [
        {
            "id": "passed-cells",
            "dataset": "headline",
            "description": "Cells meeting the fixed 40-of-50 development screen.",
            "sourceId": "sensitivity-analysis",
            "metrics": [{"label": "Cells passed", "field": "passed_cells", "format": "number"}],
        },
        {
            "id": "failed-cells",
            "dataset": "headline",
            "description": "Any failed cell blocks the proposed 0.5% design.",
            "sourceId": "sensitivity-analysis",
            "metrics": [{"label": "Cells failed", "field": "failed_cells", "format": "number"}],
        },
        {
            "id": "minimum-rate",
            "dataset": "headline",
            "description": "Lowest matched-key detection rate among all 60 cells.",
            "sourceId": "sensitivity-analysis",
            "metrics": [{"label": "Minimum cell rate", "field": "minimum_rate", "format": "percent"}],
        },
        {
            "id": "synthid-passed",
            "dataset": "headline",
            "description": "SynthID cells passing across ten keys and three lengths.",
            "sourceId": "sensitivity-analysis",
            "metrics": [{"label": "SynthID cells passed", "field": "synthid_passed", "format": "number"}],
        },
        {
            "id": "outputs",
            "dataset": "headline",
            "description": "Fresh watermarked outputs generated in 200 atomic batches.",
            "sourceId": "completed-run",
            "metrics": [{"label": "Watermarked outputs", "field": "outputs", "format": "number"}],
        },
    ]
    charts = [
        {
            "id": "kgw-rate-by-key-length",
            "title": "KGW detection rate by matched key and prefix length",
            "subtitle": "Fifty fresh outputs per cell; the development screen requires at least 80% detection.",
            "type": "bar",
            "dataset": "kgw_rates",
            "sourceId": "sensitivity-analysis",
            "encodings": {
                "x": {"field": "key", "type": "nominal", "label": "Matched KGW key"},
                "y": {"field": "detection_rate", "type": "quantitative", "format": "percent", "label": "Detection rate"},
                "color": {"field": "length", "type": "nominal", "label": "Prefix length"},
            },
            "referenceLines": [{"value": 0.8, "label": "80% screen"}],
            "layout": "full",
        }
    ]
    tables = [
        {
            "id": "failed-detail",
            "title": "Five cells below the fixed sensitivity screen",
            "subtitle": "All failures were canonical KGW; four occurred at 128 tokens.",
            "dataset": "failed_cells",
            "sourceId": "sensitivity-analysis",
            "defaultSort": {"field": "detection_rate", "direction": "asc"},
            "density": "spacious",
            "layout": "full",
            "columns": [
                {"field": "scheme", "label": "Scheme", "type": "text"},
                {"field": "key", "label": "Key", "type": "text"},
                {"field": "length", "label": "Length", "format": "number"},
                {"field": "detections", "label": "Detections", "format": "number"},
                {"field": "samples", "label": "Samples", "format": "number"},
                {"field": "detection_rate", "label": "Detection rate", "format": "percent"},
                {"field": "required_rate", "label": "Required rate", "format": "percent"},
            ],
        },
        {
            "id": "scheme-length-summary",
            "title": "Detection-rate range by scheme and prefix length",
            "subtitle": "Minimum, median and maximum across ten explicitly named matched-key cells.",
            "dataset": "summaries",
            "sourceId": "sensitivity-analysis",
            "defaultSort": {"field": "minimum_rate", "direction": "asc"},
            "density": "spacious",
            "layout": "full",
            "columns": [
                {"field": "scheme", "label": "Scheme", "type": "text"},
                {"field": "length", "label": "Length", "format": "number"},
                {"field": "minimum_rate", "label": "Minimum", "format": "percent"},
                {"field": "median_rate", "label": "Median", "format": "percent"},
                {"field": "maximum_rate", "label": "Maximum", "format": "percent"},
            ],
        },
        {
            "id": "margin-frontier-table",
            "title": "False-positive margin versus positive sensitivity",
            "subtitle": "Post-screen planning grid; none of the tested margins met both criteria.",
            "dataset": "frontier",
            "sourceId": "margin-frontier",
            "defaultSort": {"field": "design_fpr", "direction": "asc"},
            "density": "dense",
            "layout": "full",
            "columns": [
                {"field": "design_fpr", "label": "Design FPR", "format": "percent"},
                {"field": "calibration_count", "label": "Calibration max count", "format": "number"},
                {"field": "failed_positive_cells", "label": "Failed positive cells", "format": "number"},
                {"field": "minimum_positive_rate", "label": "Minimum detection", "format": "percent"},
                {"field": "median_positive_rate", "label": "Median detection", "format": "percent"},
                {"field": "conservative_family_power", "label": "Conservative family power", "format": "percent"},
            ],
        },
    ]
    title = "Phase 2 Positive Sensitivity: 0.5% Margin Rejected"
    blocks = [
        {"id": "title", "type": "markdown", "layout": "full", "body": f"# {title}"},
        {
            "id": "technical-summary",
            "type": "markdown",
            "layout": "full",
            "sourceId": "sensitivity-analysis",
            "body": "## Technical summary\n\n**Decision: do not freeze or launch the proposed v2 null study.** The predeclared 0.5% design-margin sensitivity screen passed 55 of 60 cells and failed five canonical KGW cells. Four failures occurred at 128 tokens, including a 62% minimum detection rate. All 30 SynthID cells and all ten 512-token KGW cells passed. The result shows that the proposed conservative thresholds would leave inadequate short-text KGW baseline sensitivity.",
        },
        {"id": "headline", "type": "metric-strip", "layout": "full", "cardIds": [card["id"] for card in cards]},
        {
            "id": "failure-concentration",
            "type": "markdown",
            "layout": "full",
            "sourceId": "sensitivity-analysis",
            "body": "## The sensitivity loss is concentrated in short KGW outputs\n\nAll five failures were KGW: keys 03, 05, 07 and 08 at 128 tokens, plus key 08 at 256 tokens. KGW's minimum/median cell rates were 62%/82% at 128 tokens, 76%/92% at 256, and 86%/92% at 512. SynthID's minimum was 86% at 128 tokens and at least 96% at longer prefixes. This concentration makes the 128-token KGW condition—not SynthID or long-output scoring—the controlling design problem.",
        },
        {"id": "kgw-chart", "type": "chart", "layout": "full", "chartId": "kgw-rate-by-key-length"},
        {"id": "failed-table", "type": "table", "layout": "full", "tableId": "failed-detail"},
        {"id": "summary-table", "type": "table", "layout": "full", "tableId": "scheme-length-summary"},
        {
            "id": "margin-result",
            "type": "markdown",
            "layout": "full",
            "sourceId": "margin-frontier",
            "body": "## Relaxing only the design margin does not solve both requirements\n\nA post-screen planning grid tested calibration design FPRs from 0.5% to 0.8% using v1 calibration and the completed development positives only. At 0.6%, four positive cells still failed while conservative whole-family confirmation power remained about 96%. At 0.65%, three cells failed and family power fell to about 31%. At 0.8%, one cell still failed and the union-bound family-power floor was zero. No tested margin both cleared all positive cells and retained at least 95% conservative 60-cell confirmation power.",
        },
        {"id": "frontier-table", "type": "table", "layout": "full", "tableId": "margin-frontier-table"},
        {
            "id": "scope-definitions",
            "type": "markdown",
            "layout": "full",
            "sourceId": "pilot-config",
            "body": "## Scope and metric definitions\n\nThe pilot generated 50 fresh UltraChat outputs for each of 20 matched scheme/key conditions: ten canonical KGW keys and ten canonical SynthID keys. Each 512-token output supplied paired 128-, 256- and 512-token score prefixes, creating 60 cells with 50 observations each. A strict detection required score greater than its provisional threshold. The fixed screen required at least 40 detections out of 50 in every cell.",
        },
        {
            "id": "methodology",
            "type": "markdown",
            "layout": "full",
            "sourceId": "completed-run",
            "body": "## The development screen preserved separation and implementation parity\n\nProvisional thresholds were fitted from the completed v1 calibration split at a 0.5% design bound; the tool accepted no confirmation path and loaded no v1 confirmation score. The run completed 1,000 outputs in 200 atomic batches, evenly split between KGW and SynthID. Sixty first-output compact/native audits—one per cell—reconstructed exactly. These checks support the screen calculation but do not convert it into a confirmatory detection claim.",
        },
        {
            "id": "limitations",
            "type": "markdown",
            "layout": "full",
            "sourceId": "margin-frontier",
            "body": "## Limitations and uncertainty\n\nThis was a development screen with 50 observations per cell, not an estimate precise enough for publication-level detection claims. Its thresholds came from the Dolly-based v1 calibration and may differ from future UltraChat calibration thresholds. The margin frontier is post-screen and therefore exploratory; it cannot independently validate a newly selected margin. The pilot did not measure output quality, attack survival or alternative KGW watermark biases.",
        },
        {
            "id": "next-steps",
            "type": "markdown",
            "layout": "full",
            "body": "## Recommended next steps\n\n1. Keep the 1% false-positive claim, all ten keys, and the 128-token condition unchanged.\n2. Run a targeted development-only KGW generation-strength experiment on fresh prompts, testing stronger predeclared watermark bias values against the failed short-text keys.\n3. Measure both matched-key detection and basic output-quality guardrails; changing generation strength affects positives but does not relax the null false-positive target.\n4. Select a bias only from that development experiment, then validate it on another fresh all-key positive screen.\n5. Freeze the final v2 null protocol and approve the approximately 40-hour run only if the fresh sensitivity validation passes.\n6. Keep attacks closed until a future one-shot null confirmation passes all cells.",
        },
        {
            "id": "further-questions",
            "type": "markdown",
            "layout": "full",
            "body": "## Further questions\n\n- Which stronger KGW bias restores at least 80% matched-key detection at 128 tokens without unacceptable repetition or quality loss?\n- Should the quality guardrail be based on repetition, perplexity, or blinded human review before final protocol freeze?\n- Does the selected bias generalize across all ten keys on a fresh prompt set?\n- Will final UltraChat null calibration materially move the provisional short-text thresholds?",
        },
    ]

    manifest = {
        "version": 1,
        "surface": "report",
        "title": title,
        "description": "Technical report for the completed development-only v2 positive-sensitivity screen.",
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
                "failed_cells": failed_rows,
                "kgw_rates": kgw_rates,
                "summaries": summaries,
                "frontier": frontier_rows,
            },
        },
        "sources": sources,
    }
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    output = REPORT_DIR / "artifact.json"
    output.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    print(output.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
