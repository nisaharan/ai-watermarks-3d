#!/usr/bin/env python3
"""Compare Phase 2 detector traces with pinned author-maintained implementations."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import statistics
import sys
import types
import urllib.request
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def fetch_sources(manifest: dict[str, Any], cache: Path, offline: bool) -> None:
    cache.mkdir(parents=True, exist_ok=True)
    for family in ("kgw", "synthid"):
        family_dir = cache / family
        family_dir.mkdir(exist_ok=True)
        for filename, source in manifest[family]["files"].items():
            path = family_dir / filename
            if not path.exists():
                if offline:
                    raise FileNotFoundError(f"Missing offline reference source: {path}")
                with urllib.request.urlopen(source["url"], timeout=60) as response:
                    path.write_bytes(response.read())
            observed = hashlib.sha256(path.read_bytes()).hexdigest()
            if observed != source["sha256"]:
                raise ValueError(
                    f"Reference hash mismatch for {path}: {observed} != {source['sha256']}"
                )


def load_module(name: str, path: Path) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load reference module {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_kgw_reference(cache: Path) -> types.ModuleType:
    """Load the authors' processor, stubbing only what its imports demand.

    The reference file imports optional dependencies that the token-scoring path
    never calls. They are stubbed for the duration of the import and then removed,
    because leaving a crippled `scipy` in `sys.modules` would silently break any
    later statistical code in the same process.
    """

    # Load Transformers before installing the stubs, so its own imports are real.
    import transformers  # noqa: F401

    load_module("alternative_prf_schemes", cache / "kgw" / "alternative_prf_schemes.py")

    normalizers = types.ModuleType("normalizers")
    normalizers.normalization_strategy_lookup = {}
    scipy = types.ModuleType("scipy")
    scipy.__path__ = []
    scipy_stats = types.ModuleType("scipy.stats")
    scipy.stats = scipy_stats
    stubs = {"normalizers": normalizers, "scipy": scipy, "scipy.stats": scipy_stats}

    # Never displace a real installation; only fill genuine gaps.
    installed = [name for name in stubs if name not in sys.modules]
    for name in installed:
        sys.modules[name] = stubs[name]
    try:
        return load_module(
            "phase2_official_kgw", cache / "kgw" / "extended_watermark_processor.py"
        )
    finally:
        # The imported module keeps its own references, so dropping the stubs here
        # leaves it working while restoring the process to a clean state.
        for name in installed:
            sys.modules.pop(name, None)


def load_synthid_reference(cache: Path) -> types.ModuleType:
    package = types.ModuleType("synthid_text")
    package.__path__ = []
    sys.modules["synthid_text"] = package
    hashing = load_module(
        "synthid_text.hashing_function", cache / "synthid" / "hashing_function.py"
    )
    package.hashing_function = hashing
    logits = load_module(
        "synthid_text.logits_processing", cache / "synthid" / "logits_processing.py"
    )
    package.logits_processing = logits
    return logits


# Run files written before variant labelling carry no `variants` block. They
# predate the canonical adapters, so they are by definition the stock variants.
LEGACY_VARIANTS = {
    "kgw": "kgw_transformers_selfhash_v5_16",
    "synthid": "synthid_transformers_table_v5_16",
}

EXPECTED_EXACT = {
    "kgw_author_selfhash_v1": True,
    "kgw_transformers_selfhash_v5_16": False,
    "synthid_deepmind_hash_v1": True,
    "synthid_transformers_table_v5_16": False,
}


def score_for(record: dict[str, Any], scheme: str) -> dict[str, Any]:
    return next(score for score in record["native_scores"] if score["scheme"] == scheme)


def record_tokens(record: dict[str, Any]) -> list[int]:
    return [int(row["token_id"]) for row in score_for(record, "kgw")["position_traces"]]


def compare_kgw(
    records: list[dict[str, Any]],
    module: types.ModuleType,
    tokenizer: Any,
    config: dict[str, Any],
    variant: str,
) -> dict[str, Any]:
    import torch

    detector = module.WatermarkDetector(
        vocab=list(range(tokenizer.vocab_size)),
        gamma=float(config["greenlist_ratio"]),
        delta=float(config["bias"]),
        seeding_scheme="selfhash",
        select_green_tokens=True,
        device=torch.device("cpu"),
        tokenizer=tokenizer,
        normalizers=[],
        ignore_repeated_ngrams=True,
    )
    agreements = 0
    comparisons = 0
    exact_records = 0
    z_differences: list[float] = []
    for record in records:
        local = score_for(record, "kgw")
        local_rows = [row for row in local["position_traces"] if row["eligible"]]
        official_hits = [
            bool(detector._get_ngram_score_cached(tuple(row["context_token_ids"]), int(row["token_id"])))
            for row in local_rows
        ]
        local_hits = [bool(row["values"]["green_hit"]) for row in local_rows]
        matches = sum(a == b for a, b in zip(local_hits, official_hits, strict=True))
        agreements += matches
        comparisons += len(local_hits)
        exact_records += int(matches == len(local_hits))
        official_count = sum(official_hits)
        total = len(official_hits)
        gamma = float(config["greenlist_ratio"])
        official_z = (official_count - gamma * total) / math.sqrt(
            total * gamma * (1 - gamma)
        )
        z_differences.append(abs(float(local["value"]) - official_z))
    agreement = agreements / comparisons
    exact = agreement == 1.0 and exact_records == len(records)
    expected_exact = EXPECTED_EXACT[variant]
    return {
        "variant": variant,
        "expected_exact": expected_exact,
        "exact": exact,
        "passed": exact == expected_exact,
        "records": len(records),
        "exact_records": exact_records,
        "eligible_token_comparisons": comparisons,
        "green_hit_agreement": agreement,
        "mean_absolute_z_difference": statistics.fmean(z_differences),
        "maximum_absolute_z_difference": max(z_differences),
        "reference_variant": "authors' selfhash defaults: anchored_minhash_prf, width 4, key 15485863",
        "local_variant": variant,
    }


def compare_synthid(
    records: list[dict[str, Any]],
    module: types.ModuleType,
    tokenizer: Any,
    config: dict[str, Any],
    variant: str,
) -> dict[str, Any]:
    import torch

    processor = module.SynthIDLogitsProcessor(
        ngram_len=int(config["ngram_len"]),
        keys=config["keys"],
        context_history_size=int(config["context_history_size"]),
        temperature=0.8,
        top_k=40,
        device=torch.device("cpu"),
        skip_first_ngram_calls=bool(config["skip_first_ngram_calls"]),
    )
    g_matches = 0
    g_comparisons = 0
    exact_g_records = 0
    repetition_matches = 0
    repetition_comparisons = 0
    eos_matches = 0
    eos_comparisons = 0
    mean_differences: list[float] = []
    offset = int(config["ngram_len"]) - 1
    for record in records:
        tokens = record_tokens(record)
        ids = torch.tensor([tokens], dtype=torch.long)
        official_g = processor.compute_g_values(ids)[0].tolist()
        official_repetition = processor.compute_context_repetition_mask(ids)[0].tolist()
        official_eos = processor.compute_eos_token_mask(ids, tokenizer.eos_token_id)[0, offset:].tolist()
        local = score_for(record, "synthid")
        rows = local["position_traces"][offset:]
        local_g = [row["values"]["g_values"] for row in rows]
        flat_local = [int(value) for row in local_g for value in row]
        flat_official = [int(value) for row in official_g for value in row]
        matches = sum(a == b for a, b in zip(flat_local, flat_official, strict=True))
        g_matches += matches
        g_comparisons += len(flat_local)
        exact_g_records += int(matches == len(flat_local))
        local_repetition = [bool(row["values"]["repetition_mask"]) for row in rows]
        local_eos = [bool(row["values"]["eos_mask"]) for row in rows]
        repetition_matches += sum(
            a == bool(b) for a, b in zip(local_repetition, official_repetition, strict=True)
        )
        repetition_comparisons += len(local_repetition)
        eos_matches += sum(a == bool(b) for a, b in zip(local_eos, official_eos, strict=True))
        eos_comparisons += len(local_eos)
        # The local score excludes prompt positions; mirror that here so the
        # score difference reflects g-values alone.
        within_generated = [
            row["exclusion_reason"] != "before_generated_boundary" for row in rows
        ]
        official_mask = [
            bool(a) and bool(b) and c
            for a, b, c in zip(official_repetition, official_eos, within_generated, strict=True)
        ]
        eligible_official = [row for row, keep in zip(official_g, official_mask, strict=True) if keep]
        official_mean = sum(sum(row) for row in eligible_official) / (
            len(eligible_official) * len(config["keys"])
        )
        mean_differences.append(abs(float(local["value"]) - official_mean))
    g_agreement = g_matches / g_comparisons
    repetition_agreement = repetition_matches / repetition_comparisons
    eos_agreement = eos_matches / eos_comparisons
    exact = g_agreement == 1.0 and repetition_agreement == 1.0 and eos_agreement == 1.0
    expected_exact = EXPECTED_EXACT[variant]
    return {
        "variant": variant,
        "expected_exact": expected_exact,
        "exact": exact,
        "passed": exact == expected_exact,
        "records": len(records),
        "exact_g_value_records": exact_g_records,
        "g_value_bit_comparisons": g_comparisons,
        "g_value_agreement": g_agreement,
        "repetition_mask_agreement": repetition_agreement,
        "eos_mask_agreement": eos_agreement,
        "mean_absolute_score_difference": statistics.fmean(mean_differences),
        "maximum_absolute_score_difference": max(mean_differences),
        "reference_variant": "DeepMind SHA-IV and iterative-hash g-values",
        "local_variant": variant,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke-result", type=Path, default=Path("results/phase2-smoke/run.json"))
    parser.add_argument("--manifest", type=Path, default=Path("configs/phase2-reference-sources.json"))
    parser.add_argument("--source-cache", type=Path, default=Path(".cache/phase2-references"))
    parser.add_argument("--output", type=Path, default=Path("results/phase2-reference/crosscheck.json"))
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()

    manifest = load_json(args.manifest)
    smoke = load_json(args.smoke_result)
    fetch_sources(manifest, args.source_cache, args.offline)
    kgw_module = load_kgw_reference(args.source_cache)
    synthid_module = load_synthid_reference(args.source_cache)

    from transformers import AutoTokenizer

    model = smoke["config"]["model"]
    tokenizer = AutoTokenizer.from_pretrained(model["id"], revision=model["revision"])
    variants = smoke["config"].get("variants", LEGACY_VARIANTS)
    unknown = {
        family: name
        for family, name in variants.items()
        if name not in EXPECTED_EXACT
    }
    if unknown:
        raise ValueError(
            f"Run file declares unknown variants {unknown}; "
            f"expected names from {sorted(EXPECTED_EXACT)}"
        )
    kgw = compare_kgw(
        smoke["records"], kgw_module, tokenizer, smoke["config"]["kgw"], variants["kgw"]
    )
    synthid = compare_synthid(
        smoke["records"],
        synthid_module,
        tokenizer,
        smoke["config"]["synthid"],
        variants["synthid"],
    )
    report = {
        "schema_version": 1,
        "scope": "Independent implementation parity diagnostic; not a benchmark result",
        "gate": "each family must match its declared variant's expected parity",
        "passed": kgw["passed"] and synthid["passed"],
        "source_manifest": manifest,
        "smoke_source_tree_sha256": smoke["environment"]["source_tree_sha256"],
        "variants_declared_by_run": "variants" in smoke["config"],
        "kgw": kgw,
        "synthid": synthid,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
