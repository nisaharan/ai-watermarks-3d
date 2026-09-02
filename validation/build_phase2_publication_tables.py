#!/usr/bin/env python3
"""Build manuscript-ready Markdown tables from reviewed Phase 2 artifacts."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper/phase2-publication-tables.md"


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def datasets(relative: str) -> dict[str, list[dict]]:
    artifact = load(relative)
    if artifact.get("surface") != "report":
        raise RuntimeError(f"Expected report artifact: {relative}")
    return artifact["snapshot"]["datasets"]


def pct(value: float, digits: int = 1) -> str:
    return f"{100 * value:.{digits}f}%"


def main() -> int:
    validation = datasets("reports/phase2-validation/artifact.json")
    gate = datasets("reports/phase2-confirmation-gate/artifact.json")
    sensitivity = datasets("reports/phase2-positive-sensitivity/artifact.json")
    bias = load("results/phase2-v2-kgw-bias-development-v3/analysis.json")
    closure = load("results/phase2-v2-kgw-joint-feasibility/study-closure.json")

    headline = validation["headline"][0]
    gate_headline = gate["headline"][0]
    sensitivity_headline = sensitivity["headline"][0]
    if gate_headline["passed_cells"] + gate_headline["failed_cells"] != 60:
        raise RuntimeError("Confirmation headline does not reconcile to 60 cells")
    if bias.get("status") != "kgw_bias_development_failed" or bias.get("selected_bias") is not None:
        raise RuntimeError("Bias-development terminal result is not preserved")
    if closure["partial_stage_a_disposition"]["outcome_evaluated"]:
        raise RuntimeError("Partial Stage A must remain excluded")

    lines = [
        "# Phase 2 publication tables",
        "",
        "Generated deterministically from reviewed artifacts. The partial joint-KGW Stage A run is excluded.",
        "",
        "## Table 1. Study sequence and evidential role",
        "",
        "| Stage | Sample | Role | Outcome |",
        "|---|---:|---|---|",
        f"| SmolLM2 multi-key null pilot | {headline['primary_null_prompts']} outputs | Development | Maximum nominal 1% KGW cell FPR at 512 tokens: {pct(headline['primary_max_nominal_1pct_fpr'])} |",
        f"| Qwen2.5 replication | {headline['replication_null_prompts']} outputs | Independent targeted replication | Maximum nominal 1% KGW cell FPR at 512 tokens: {pct(headline['replication_max_nominal_1pct_fpr'])} |",
        "| Confirmatory calibration | 5,000 outputs | Threshold fitting only | Thresholds frozen once |",
        "| Confirmatory confirmation | 5,000 disjoint outputs | One-shot validation | 42/60 cells passed; global gate failed |",
        f"| Positive-sensitivity screen | {sensitivity_headline['outputs']} outputs | Development | {sensitivity_headline['passed_cells']}/60 cells passed |",
        "| KGW bias brackets | 1,400 outputs | Development | No tested bias passed all detection and quality guardrails |",
        f"| Joint-KGW Stage A | {closure['partial_stage_a_disposition']['durable_outputs']}/{closure['partial_stage_a_disposition']['target_outputs']} outputs | Abandoned unevaluated run | No outcome claim |",
        "",
        "## Table 2. One-shot confirmation outcome by scheme",
        "",
        "| Scheme | Passed | Failed | Total |",
        "|---|---:|---:|---:|",
    ]
    for row in gate["scheme_summary"]:
        lines.append(f"| {row['scheme']} | {row['passed']} | {row['failed']} | {row['total']} |")

    lines.extend([
        "",
        "## Table 3. Failed confirmation cells by scheme and prefix length",
        "",
        "| Scheme | Prefix length | Passed | Failed | Total |",
        "|---|---:|---:|---:|---:|",
    ])
    for row in gate["scheme_length_failures"]:
        lines.append(f"| {row['scheme']} | {row['length']} | {row['passed']} | {row['failed']} | {row['total']} |")

    lines.extend([
        "",
        "## Table 4. Calibration versus confirmation exceedance counts",
        "",
        "| Scheme | Split | Mean exceedances per cell | Maximum passing count |",
        "|---|---|---:|---:|",
    ])
    for row in gate["scheme_split_means"]:
        lines.append(f"| {row['scheme']} | {row['split'].title()} | {row['mean_exceedances']:.2f} | {row['maximum_allowed']} |")

    lines.extend([
        "",
        "## Table 5. Positive-sensitivity screen by scheme and length",
        "",
        "| Scheme | Prefix length | Minimum | Median | Maximum |",
        "|---|---:|---:|---:|---:|",
    ])
    for row in sensitivity["summaries"]:
        lines.append(
            f"| {row['scheme']} | {row['length']} | {pct(row['minimum_rate'])} | "
            f"{pct(row['median_rate'])} | {pct(row['maximum_rate'])} |"
        )

    lines.extend([
        "",
        "## Interpretation notes",
        "",
        f"- The largest observed failed-cell confirmation rate was {pct(gate_headline['maximum_observed_rate'], 2)}; the largest simultaneous exact upper bound was {pct(gate_headline['maximum_upper_bound'], 2)}.",
        "- A failed simultaneous confidence cell does not establish that its true false-positive rate exceeds 1%.",
        "- Pilot maxima must always be reported with the named model, key, prefix length, nominal threshold, and development status.",
        "- Development sensitivity and bias screens are not independent confirmation.",
        "- The partial joint-KGW Stage A scores were not analysed and must not appear in a results table or figure.",
        "",
        "## Machine-readable sources",
        "",
        "- `reports/phase2-validation/artifact.json`",
        "- `reports/phase2-confirmation-gate/artifact.json`",
        "- `reports/phase2-positive-sensitivity/artifact.json`",
        "- `results/phase2-v2-kgw-bias-development-v3/analysis.json`",
        "- `results/phase2-v2-kgw-joint-feasibility/study-closure.json`",
        "",
    ])
    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"status": "publication_tables_built", "output": str(OUTPUT.relative_to(ROOT)), "tables": 5}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
