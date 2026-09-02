"""Ten-prompt Phase 2 smoke runner for native keyed watermarks."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import canonical
from .attacks import delete_every, identity, insert_every, substitute_every, truncate
from .contexts import ContextRule, measure_context_survival
from .native import TransformersNativeRunner, require_ml_dependencies


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def git_commit() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False
    )
    return result.stdout.strip() if result.returncode == 0 else "unavailable"


def git_dirty() -> bool | None:
    result = subprocess.run(
        ["git", "status", "--porcelain"], capture_output=True, text=True, check=False
    )
    return bool(result.stdout) if result.returncode == 0 else None


def source_tree_sha256() -> str:
    """Fingerprint the committed inputs and local Phase 2 implementation."""

    paths = [
        Path("pyproject.toml"),
        Path("uv.lock"),
        Path("configs/phase2-smoke.json"),
        Path("data/phase2-smoke-prompts.json"),
        *sorted(Path("src/ai_watermarks_phase2").glob("*.py")),
        *sorted(Path("tests").glob("test_*.py")),
    ]
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def validate_configuration(config: dict[str, Any], prompts: list[dict[str, str]]) -> None:
    if not isinstance(config, dict):
        raise ValueError("Configuration root must be a JSON object")
    if not isinstance(prompts, list):
        raise ValueError("Prompt-set root must be a JSON array")
    required = {"model", "generation", "kgw", "synthid", "variants", "attacks", "provenance"}
    missing = required - config.keys()
    if missing:
        raise ValueError(f"Missing configuration sections: {sorted(missing)}")
    if any(not isinstance(config[section], dict) for section in required):
        raise ValueError("Every configuration section must be a JSON object")

    generation = config["generation"]
    min_tokens = _integer_setting(generation, "min_new_tokens", minimum=1)
    max_tokens = _integer_setting(generation, "max_new_tokens", minimum=1)
    if min_tokens > max_tokens:
        raise ValueError("generation.min_new_tokens must not exceed max_new_tokens")
    _integer_setting(generation, "base_seed", minimum=0)
    _integer_setting(generation, "top_k", minimum=1)
    _positive_number_setting(generation, "temperature")

    kgw = config["kgw"]
    _integer_setting(kgw, "context_width", minimum=1)
    greenlist_ratio = _number_setting(kgw, "greenlist_ratio")
    if not 0.0 < greenlist_ratio < 1.0:
        raise ValueError("kgw.greenlist_ratio must be strictly between zero and one")

    synthid = config["synthid"]
    _integer_setting(synthid, "ngram_len", minimum=2)
    keys = synthid.get("keys")
    if not isinstance(keys, list) or not keys or any(type(key) is not int for key in keys):
        raise ValueError("synthid.keys must be a non-empty list of integers")

    attacks = config["attacks"]
    _integer_setting(attacks, "interval", minimum=1)
    _integer_setting(attacks, "replacement_token", minimum=0)

    variants = config["variants"]
    if variants.get("kgw") not in canonical.KGW_VARIANTS:
        raise ValueError(
            f"variants.kgw must be one of {list(canonical.KGW_VARIANTS)}, "
            f"found {variants.get('kgw')!r}"
        )
    if variants.get("synthid") not in canonical.SYNTHID_VARIANTS:
        raise ValueError(
            f"variants.synthid must be one of {list(canonical.SYNTHID_VARIANTS)}, "
            f"found {variants.get('synthid')!r}"
        )
    if len(prompts) != 10:
        raise ValueError(f"The Phase 2 smoke set must contain exactly 10 prompts, found {len(prompts)}")
    if any(
        not isinstance(item, dict)
        or not isinstance(item.get("id"), str)
        or not item["id"].strip()
        or not isinstance(item.get("prompt"), str)
        or not item["prompt"].strip()
        for item in prompts
    ):
        raise ValueError("Every prompt must have non-empty string id and prompt fields")
    ids = [item["id"] for item in prompts]
    if len(set(ids)) != len(ids):
        raise ValueError("Prompt IDs must be unique")
    if config["provenance"].get("key_scope") != "public_test_fixture":
        raise ValueError("Committed keys are allowed only with key_scope=public_test_fixture")


def _integer_setting(settings: dict[str, Any], name: str, *, minimum: int) -> int:
    value = settings.get(name)
    if type(value) is not int or value < minimum:
        raise ValueError(f"{name} must be an integer greater than or equal to {minimum}")
    return value


def _number_setting(settings: dict[str, Any], name: str) -> float:
    value = settings.get(name)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be numeric")
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    return value


def _positive_number_setting(settings: dict[str, Any], name: str) -> float:
    value = _number_setting(settings, name)
    if value <= 0:
        raise ValueError(f"{name} must be positive")
    return value


def make_attacks(tokens: list[int], config: dict[str, Any]) -> list[Any]:
    replacement = int(config["replacement_token"])
    interval = int(config["interval"])
    return [
        identity(tokens),
        substitute_every(tokens, interval=interval, replacement_token=replacement),
        delete_every(tokens, interval=interval),
        insert_every(tokens, interval=interval, inserted_token=replacement),
        truncate(tokens, keep=max(1, len(tokens) // 2)),
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/phase2-smoke.json"))
    parser.add_argument("--prompts", type=Path, default=Path("data/phase2-smoke-prompts.json"))
    parser.add_argument("--output", type=Path, default=Path("results/phase2-smoke/run.json"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args(argv)

    if not 1 <= args.limit <= 10:
        parser.error("--limit must be between 1 and 10")

    config = load_json(args.config)
    prompts = load_json(args.prompts)
    validate_configuration(config, prompts)
    if args.dry_run:
        print(json.dumps({"status": "configuration_valid", "prompts": len(prompts)}, indent=2))
        return 0

    torch, transformers = require_ml_dependencies()
    runner = TransformersNativeRunner(
        model_id=config["model"]["id"],
        revision=config["model"]["revision"],
        device=config["model"]["device"],
    )
    kgw_variant = config["variants"]["kgw"]
    synthid_variant = config["variants"]["synthid"]
    kgw_config = canonical.build_kgw_config(config["kgw"], kgw_variant)
    synthid_config = canonical.build_synthid_config(config["synthid"], synthid_variant)
    watermark_configs = {
        "unwatermarked": None,
        "kgw": kgw_config,
        "synthid": synthid_config,
    }
    records: list[dict[str, Any]] = []
    selected_prompts = prompts[: args.limit]
    seed = int(config["generation"]["base_seed"])
    for scheme in ("unwatermarked", "kgw", "synthid"):
        generated_rows = runner.generate_batch(
            [item["prompt"] for item in selected_prompts],
            seed=seed,
            min_new_tokens=int(config["generation"]["min_new_tokens"]),
            max_new_tokens=int(config["generation"]["max_new_tokens"]),
            temperature=float(config["generation"]["temperature"]),
            top_k=int(config["generation"]["top_k"]),
            watermark_config=watermark_configs[scheme],
        )
        for prompt_index, (prompt_item, generated) in enumerate(
            zip(selected_prompts, generated_rows, strict=True)
        ):
            _full, continuation, text = generated
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
            context_rules = [
                ContextRule(
                    name="kgw_selfhash_no_repeat",
                    window_size=int(config["kgw"]["context_width"]),
                    deduplicate="window",
                ),
                ContextRule(
                    name="synthid_repeated_context_mask",
                    window_size=int(config["synthid"]["ngram_len"]),
                    deduplicate="context",
                ),
            ]
            attacks = make_attacks(continuation, config["attacks"])
            attack_measurements = []
            for attack in attacks:
                attacked_kgw_score = runner.score_kgw(
                    list(attack.tokens),
                    first_generated_position=0,
                    config=kgw_config,
                    variant=kgw_variant,
                    ignore_repeated_ngrams=True,
                )
                attacked_synthid_score = runner.score_synthid(
                    list(attack.tokens),
                    first_generated_position=0,
                    config=synthid_config,
                    variant=synthid_variant,
                )
                measurements = [
                    measure_context_survival(
                        continuation,
                        attack.tokens,
                        attack.candidate_to_original,
                        rule,
                    )
                    for rule in context_rules
                ]
                attack_measurements.append(
                    {
                        "attack": attack.name,
                        "parameters": attack.parameters,
                        "candidate_tokens": len(attack.tokens),
                        "native_scores": [
                            attacked_kgw_score.to_dict(),
                            attacked_synthid_score.to_dict(),
                        ],
                        "context_measurements": [
                            {
                                "rule": measurement.rule,
                                "effective_surviving": measurement.effective_surviving,
                                "original_eligible": measurement.original_eligible,
                                "candidate_eligible": measurement.candidate_eligible,
                                "survival_rate": measurement.survival_rate,
                            }
                            for measurement in measurements
                        ],
                    }
                )
            records.append(
                {
                    "prompt_id": prompt_item["id"],
                    "condition": scheme,
                    "seed": seed,
                    "batch_stream_index": prompt_index,
                    "prompt_sha256": sha256_text(prompt_item["prompt"]),
                    "output_sha256": sha256_text(text),
                    "generated_tokens": len(continuation),
                    "text": text,
                    "native_scores": [kgw_score.to_dict(), synthid_score.to_dict()],
                    "attacks": attack_measurements,
                }
            )

    result = {
        "schema_version": 2,
        "status": "smoke_complete",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "Validation only; not a benchmark result",
        "config": config,
        "variant_notes": {
            family: {
                "variant": variant,
                "inert_settings": list(canonical.inert_settings(variant)),
            }
            for family, variant in (("kgw", kgw_variant), ("synthid", synthid_variant))
        },
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "torch": torch.__version__,
            "transformers": transformers.__version__,
            "package_version": importlib.metadata.version("ai-watermarks-research"),
            "git_commit": git_commit(),
            "git_dirty": git_dirty(),
            "source_tree_sha256": source_tree_sha256(),
        },
        "records": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "records": len(records), "output": str(args.output)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
