#!/usr/bin/env python3
"""Compare the generation path of the canonical adapters with the pinned references.

The token-level cross-check in `phase2_reference_crosscheck.py` gates the keyed
*detection* primitives: green lists, g-values and eligibility masks. This script
gates the other half, generation, by feeding both implementations the same context
and the same model scores at every step and comparing what each one produces.

Both arms are driven along one shared token path. Letting each arm sample its own
continuation would not isolate the processor: once the paths diverge the two are
scoring different contexts, and `torch.multinomial` consumes its generator
differently for a full-vocabulary vector than for a top-k vector, so the sequences
would diverge even under identical distributions.

KGW is compared on the biased score vector, which differs only by a fixed bias on
a boolean mask and must therefore agree exactly.

SynthID is compared on the sampling distribution restricted to the reference's
top-k set. Here the two pipelines do not always see the same candidate set: the
Transformers stack filters with `TopKLogitsWarper`, which masks `scores <
threshold` and therefore keeps ties at the boundary, while the reference processor
runs its own `torch.topk(k)` internally and takes exactly k. When a tie lets extra
candidates through, the two arms normalise over different sets and the
distributions differ for that reason alone, not because the tournament differs.

The gate is therefore taken on the steps where both arms see the same candidate
set, which is the question about the watermark. Steps with a boundary tie are
counted and reported separately as a decoder difference, with their magnitude, so
the deviation is quantified rather than hidden.
"""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Any

from phase2_reference_crosscheck import (
    fetch_sources,
    load_json,
    load_kgw_reference,
    load_synthid_reference,
)

PROBABILITY_TOLERANCE = 1e-5

# A canonical variant must reproduce the reference; a secondary variant must not
# silently start matching it. The gate checks each against its own expectation.
EXPECTED_EXACT = {
    "kgw_author_selfhash_v1": True,
    "kgw_transformers_selfhash_v5_16": False,
    "synthid_deepmind_hash_v1": True,
    "synthid_transformers_table_v5_16": False,
}


def top_k_filter(scores: Any, top_k: int) -> Any:
    """Mask all but the top-k scores, keeping ties at the boundary as Transformers does."""

    import torch

    if top_k <= 0 or top_k >= scores.shape[-1]:
        return scores
    threshold = torch.topk(scores, top_k, dim=-1).values[..., -1, None]
    return scores.masked_fill(scores < threshold, float("-inf"))


def compare_kgw(
    model: Any,
    tokenizer: Any,
    module: Any,
    prompts: list[str],
    config: dict[str, Any],
    generation: dict[str, Any],
    variant: str,
    steps: int,
) -> dict[str, Any]:
    import torch

    from ai_watermarks_phase2 import canonical

    vocab_size = model.config.vocab_size
    temperature = float(generation["temperature"])
    top_k = int(generation["top_k"])
    canonical_processor = canonical.build_kgw_config(config, variant).construct_processor(
        vocab_size, torch.device("cpu")
    )
    # The authors' processor creates its generator lazily from the input device.
    reference_processor = module.WatermarkLogitsProcessor(
        vocab=list(range(vocab_size)),
        gamma=float(config["greenlist_ratio"]),
        delta=float(config["bias"]),
        seeding_scheme="selfhash",
        select_green_tokens=True,
    )

    exact_steps = 0
    total_steps = 0
    differences: list[float] = []
    for index, prompt in enumerate(prompts):
        ids = tokenizer(prompt, return_tensors="pt")["input_ids"]
        torch.manual_seed(int(generation["base_seed"]) + index)
        for _ in range(steps):
            with torch.inference_mode():
                logits = model(ids).logits[:, -1, :].float()
            scores = top_k_filter(logits / temperature, top_k)
            mine = canonical_processor(ids, scores.clone())
            theirs = reference_processor(ids, scores.clone())
            finite = torch.isfinite(mine) | torch.isfinite(theirs)
            gap = (mine.masked_fill(~finite, 0.0) - theirs.masked_fill(~finite, 0.0)).abs()
            largest = float(gap.max().item())
            differences.append(largest)
            exact_steps += int(largest == 0.0)
            total_steps += 1
            probabilities = torch.nn.functional.softmax(mine, dim=-1)
            ids = torch.cat([ids, torch.multinomial(probabilities, num_samples=1)], dim=-1)

    exact = exact_steps == total_steps
    expected_exact = EXPECTED_EXACT[variant]
    return {
        "variant": variant,
        "comparison": "biased score vector over the full vocabulary",
        "expected_exact": expected_exact,
        "exact": exact,
        "prompts": len(prompts),
        "scored_steps": total_steps,
        "exact_steps": exact_steps,
        "step_agreement": exact_steps / total_steps,
        "mean_absolute_score_difference": statistics.fmean(differences),
        "maximum_absolute_score_difference": max(differences),
        "passed": exact == expected_exact,
    }


def compare_synthid(
    model: Any,
    tokenizer: Any,
    module: Any,
    prompts: list[str],
    config: dict[str, Any],
    generation: dict[str, Any],
    variant: str,
    steps: int,
) -> dict[str, Any]:
    import torch

    from ai_watermarks_phase2 import canonical

    vocab_size = model.config.vocab_size
    temperature = float(generation["temperature"])
    top_k = int(generation["top_k"])
    canonical_processor = canonical.build_synthid_config(config, variant).construct_processor(
        vocab_size, torch.device("cpu")
    )
    reference_processor = module.SynthIDLogitsProcessor(
        ngram_len=int(config["ngram_len"]),
        keys=config["keys"],
        context_history_size=int(config["context_history_size"]),
        temperature=temperature,
        top_k=top_k,
        device=torch.device("cpu"),
    )

    matched_within_tolerance = 0
    matched_steps = 0
    tied_steps = 0
    matched_differences: list[float] = []
    tied_differences: list[float] = []
    for index, prompt in enumerate(prompts):
        ids = tokenizer(prompt, return_tensors="pt")["input_ids"]
        canonical_processor.state = None
        reference_processor.state = None
        torch.manual_seed(int(generation["base_seed"]) + index)
        for _ in range(steps):
            with torch.inference_mode():
                logits = model(ids).logits[:, -1, :].float()
            scores = top_k_filter(logits / temperature, top_k)
            mine = canonical_processor(ids, scores.clone())
            updated, indices, _ = reference_processor.watermarked_call(ids, logits.clone())

            mine_probabilities = torch.nn.functional.softmax(mine, dim=-1)
            reference_probabilities = torch.nn.functional.softmax(updated, dim=-1)
            gap = float(
                (torch.gather(mine_probabilities, 1, indices) - reference_probabilities)
                .abs()
                .max()
                .item()
            )
            # A boundary tie leaves more than top_k finite candidates, so the two
            # arms are normalising over different sets at this step.
            candidates = int(torch.isfinite(scores).sum().item())
            if candidates == top_k:
                matched_differences.append(gap)
                matched_within_tolerance += int(gap <= PROBABILITY_TOLERANCE)
                matched_steps += 1
            else:
                tied_differences.append(gap)
                tied_steps += 1
            ids = torch.cat(
                [ids, torch.multinomial(mine_probabilities, num_samples=1)], dim=-1
            )

    exact = matched_steps > 0 and matched_within_tolerance == matched_steps
    expected_exact = EXPECTED_EXACT[variant]
    return {
        "variant": variant,
        "comparison": "sampling distribution over the reference's top-k set",
        "expected_exact": expected_exact,
        "exact": exact,
        "tolerance": PROBABILITY_TOLERANCE,
        "prompts": len(prompts),
        "scored_steps": matched_steps + tied_steps,
        "matched_candidate_set": {
            "steps": matched_steps,
            "steps_within_tolerance": matched_within_tolerance,
            "step_agreement": matched_within_tolerance / matched_steps if matched_steps else None,
            "mean_absolute_probability_difference": (
                statistics.fmean(matched_differences) if matched_differences else None
            ),
            "maximum_absolute_probability_difference": (
                max(matched_differences) if matched_differences else None
            ),
        },
        "top_k_boundary_tie": {
            "steps": tied_steps,
            "cause": (
                "TopKLogitsWarper keeps ties at the boundary; the reference takes exactly k"
            ),
            "effect": "decoder candidate sets differ at these steps, not the tournament",
            "mean_absolute_probability_difference": (
                statistics.fmean(tied_differences) if tied_differences else None
            ),
            "maximum_absolute_probability_difference": (
                max(tied_differences) if tied_differences else None
            ),
        },
        "passed": exact == expected_exact,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/phase2-smoke.json"))
    parser.add_argument("--prompts", type=Path, default=Path("data/phase2-smoke-prompts.json"))
    parser.add_argument("--manifest", type=Path, default=Path("configs/phase2-reference-sources.json"))
    parser.add_argument("--source-cache", type=Path, default=Path(".cache/phase2-references"))
    parser.add_argument(
        "--output", type=Path, default=Path("results/phase2-reference/generation-parity.json")
    )
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--steps", type=int, default=24)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()

    config = load_json(args.config)
    prompts = [item["prompt"] for item in load_json(args.prompts)[: args.limit]]
    manifest = load_json(args.manifest)
    fetch_sources(manifest, args.source_cache, args.offline)
    kgw_module = load_kgw_reference(args.source_cache)
    synthid_module = load_synthid_reference(args.source_cache)

    from transformers import AutoModelForCausalLM, AutoTokenizer

    model_settings = config["model"]
    tokenizer = AutoTokenizer.from_pretrained(
        model_settings["id"], revision=model_settings["revision"]
    )
    model = AutoModelForCausalLM.from_pretrained(
        model_settings["id"], revision=model_settings["revision"]
    )
    model.eval()

    variants = config.get("variants", {
        "kgw": "kgw_transformers_selfhash_v5_16",
        "synthid": "synthid_transformers_table_v5_16",
    })
    unknown = {f: n for f, n in variants.items() if n not in EXPECTED_EXACT}
    if unknown:
        raise ValueError(f"Configuration declares unknown variants {unknown}")
    kgw = compare_kgw(
        model, tokenizer, kgw_module, prompts, config["kgw"],
        config["generation"], variants["kgw"], args.steps,
    )
    synthid = compare_synthid(
        model, tokenizer, synthid_module, prompts, config["synthid"],
        config["generation"], variants["synthid"], args.steps,
    )
    report = {
        "schema_version": 1,
        "scope": "Generation-path parity diagnostic; not a benchmark result",
        "gate": (
            "each family must show the parity its declared variant expects, on "
            "every step where both arms see the same candidate set"
        ),
        "passed": kgw["passed"] and synthid["passed"],
        "source_manifest": manifest,
        "sampling": {
            "prompts": len(prompts),
            "steps_per_prompt": args.steps,
            "temperature": config["generation"]["temperature"],
            "top_k": config["generation"]["top_k"],
            "shared_token_path": True,
        },
        "kgw": kgw,
        "synthid": synthid,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
