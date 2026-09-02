#!/usr/bin/env python3
"""Reproduce the high-impact Phase 0 validation findings.

This script is read-only. It evaluates the repository's existing estimator and a
length-corrected projection derived from the same assumptions. Neither value is a
measured watermark score because the source text has no documented keyed watermark.
"""

import json
import math
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

import analyse_removal as current  # noqa: E402


def length_corrected_projection(survival, original_contexts, candidate_tokens):
    """Expected excess z under the repository's hypothetical watermark model.

    If k original watermark-bearing contexts survive in a candidate of length n,
    their expected excess green hits are (p_marked - gamma) * k. The null standard
    deviation is sqrt(n * gamma * (1 - gamma)).

    `survival` remains the current set-based word-bigram proxy. Scaling it to a
    position count repairs the length dependence only; it does not make the proxy a
    keyed detector or remove chance/topic-overlap contamination.
    """
    surviving_contexts = survival * original_contexts
    denominator = math.sqrt(
        candidate_tokens * current.GAMMA * (1 - current.GAMMA)
    )
    return (
        (current.P_MARKED - current.GAMMA)
        * surviving_contexts
        / denominator
    )


def load_texts():
    return {
        name: (BASE / path).read_text(encoding="utf-8").strip()
        for name, path, _label in current.VARIANTS
    }


def variant_rows(texts):
    original_contexts = max(len(current.tokens(texts["ai"])) - 1, 0)
    rows = []
    for name, _path, _label in current.VARIANTS:
        candidate_n = len(current.tokens(texts[name]))
        survival = current.bigram_survival(texts["ai"], texts[name])
        rows.append(
            {
                "variant": name,
                "candidate_tokens": candidate_n,
                "bigram_survival_proxy": survival,
                "current_modelled_z": current.modelled_z(survival, candidate_n),
                "length_corrected_projection": length_corrected_projection(
                    survival, original_contexts, candidate_n
                ),
            }
        )
    return rows


def padding_rows(texts):
    original_contexts = max(len(current.tokens(texts["ai"])) - 1, 0)
    filler = " ".join(["Completely unrelated filler sentence."] * 30)
    rows = []
    for blocks in (0, 1, 3):
        candidate = texts["ai"] + ((" " + filler) * blocks)
        candidate_n = len(current.tokens(candidate))
        survival = current.bigram_survival(texts["ai"], candidate)
        rows.append(
            {
                "filler_blocks": blocks,
                "candidate_tokens": candidate_n,
                "bigram_survival_proxy": survival,
                "current_modelled_z": current.modelled_z(survival, candidate_n),
                "length_corrected_projection": length_corrected_projection(
                    survival, original_contexts, candidate_n
                ),
            }
        )
    return rows


def metric_pipeline_differences():
    profiles = json.loads((BASE / "example/profiles.json").read_text())
    removal = json.loads(
        (BASE / "example/removal/analysis.json").read_text()
    )["variants"]
    rows = []
    for name in ("human", "ai"):
        rows.append(
            {
                "sample": name,
                "profiles_n_words": profiles[name]["n_words"],
                "removal_n_words": removal[name]["n_words"],
                "profiles_ttr": profiles[name]["ttr"],
                "removal_ttr": removal[name]["ttr"],
            }
        )
    return rows


def main():
    texts = load_texts()
    payload = {
        "scope": "Phase 0 validation of the existing exploratory estimator",
        "warning": (
            "All z-like values are hypothetical projections, not measured watermark "
            "scores. No keyed watermark is documented for example/ai_generated.txt."
        ),
        "layer_a_byte_identical": texts["ai"].encode() == texts["layerA"].encode(),
        "variants": variant_rows(texts),
        "padding_test": padding_rows(texts),
        "metric_pipeline_differences": metric_pipeline_differences(),
    }
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
