"""Run Stage A or B of the preregistered KGW joint-parameter feasibility study."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import platform
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from . import canonical
from .compact_scoring import CompactKGWScorer
from .confirmatory_null import atomic_json
from .kgw_joint_protocol import (
    CONFIG_PATH,
    candidate_grid,
    validate_authorization,
    validate_manifests,
    validate_protocol,
)
from .native import TransformersNativeRunner, require_ml_dependencies
from .positive_sensitivity import audit_score
from .smoke import git_commit, git_dirty, load_json, sha256_text
from .variance_pilot import file_sha256


RESULT_ROOT = Path("results/phase2-v2-kgw-joint-feasibility")
EMPTY_REJECTION_COUNTS: defaultdict[tuple[float, float, int], int] = defaultdict(int)


def install_instrumented_empty_index_safeguard() -> None:
    """Install the validated long-index no-op and count empty rejection events."""
    torch, _ = require_ml_dependencies()
    processor_class = canonical.canonical_classes()["AuthorKGWLogitsProcessor"]

    def score_rejection_sampling(self: Any, input_seq: Any, scores: Any) -> Any:
        _, greedy_predictions = scores.sort(dim=-1, descending=True)
        final_greenlist = []
        for index, candidate in enumerate(greedy_predictions):
            greenlist_ids = self._get_greenlist_ids(
                torch.cat([input_seq, candidate[None]], dim=-1)
            )
            if candidate in greenlist_ids:
                final_greenlist.append(candidate)
            if index == canonical.KGW_AUTHOR_REJECTION_TAIL_INDEX:
                break
        if final_greenlist:
            return torch.stack(final_greenlist).to(
                device=input_seq.device, dtype=torch.long
            )
        EMPTY_REJECTION_COUNTS[
            (
                float(self.greenlist_ratio),
                float(self.bias),
                int(self.hashing_key),
            )
        ] += 1
        return torch.empty(0, device=input_seq.device, dtype=torch.long)

    processor_class._score_rejection_sampling = score_rejection_sampling


def source_sha256() -> str:
    digest = hashlib.sha256()
    for path in (
        Path("uv.lock"),
        Path("src/ai_watermarks_phase2/canonical.py"),
        Path("src/ai_watermarks_phase2/compact_scoring.py"),
        Path("src/ai_watermarks_phase2/native.py"),
        Path("src/ai_watermarks_phase2/kgw_joint_protocol.py"),
        Path(__file__),
    ):
        digest.update(path.as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def batch_paths(output_dir: Path) -> list[Path]:
    return sorted((output_dir / "batches").glob("batch-*.json"))


def iter_records(output_dir: Path) -> Iterator[dict[str, Any]]:
    for path in batch_paths(output_dir):
        batch = load_json(path)
        if not isinstance(batch.get("records"), list):
            raise ValueError(f"Malformed batch: {path}")
        yield from batch["records"]


def run_digest(output_dir: Path) -> str:
    metadata = load_json(output_dir / "run.json")
    stable = {
        key: metadata[key]
        for key in (
            "schema_version",
            "status",
            "protocol_id",
            "stage",
            "completed_batches",
            "completed_outputs",
            "input_sha256",
        )
    }
    digest = hashlib.sha256(json.dumps(stable, sort_keys=True).encode())
    for path in batch_paths(output_dir):
        digest.update(path.name.encode())
        digest.update(bytes.fromhex(file_sha256(path)))
    return digest.hexdigest()


def stage_candidates(
    config: dict[str, Any], stage: str, selection_path: Path | None
) -> list[tuple[float | None, float | None]]:
    if stage == "stage_a":
        return [(None, None), *candidate_grid(config)]
    if selection_path is None:
        raise ValueError("Stage B requires a frozen Stage-A selection artifact")
    selection = load_json(selection_path)
    if selection.get("status") != "kgw_joint_stage_a_candidate_selected":
        raise ValueError("Stage-A selection is absent or did not select a candidate")
    if selection.get("protocol_id") != config["protocol_id"]:
        raise ValueError("Stage-A selection and protocol differ")
    candidate = selection.get("selected_candidate")
    if not isinstance(candidate, dict):
        raise ValueError("Stage-A selection has no candidate")
    pair = (float(candidate["gamma"]), float(candidate["delta"]))
    if pair not in candidate_grid(config):
        raise ValueError("Stage-A selection is outside the frozen candidate family")
    return [(None, None), pair]


def batch_plan(
    key_indices: list[int],
    candidates: list[tuple[float | None, float | None]],
    prompts: int,
    batch_size: int,
) -> list[dict[str, Any]]:
    if prompts < 1 or batch_size < 1 or prompts % batch_size:
        raise ValueError("prompts must be a positive multiple of batch_size")
    return [
        {
            "key_index": key_index,
            "key_id": f"kgw-{key_index:02d}",
            "condition": "unwatermarked_control" if gamma is None else "watermarked",
            "gamma": gamma,
            "delta": delta,
            "prompt_start": prompt_start,
        }
        for key_index in key_indices
        for gamma, delta in candidates
        for prompt_start in range(0, prompts, batch_size)
    ]


def paired_batch_seed(
    base_seed: int,
    key_indices: list[int],
    key_index: int,
    prompt_start: int,
    batch_size: int,
    prompts: int,
) -> int:
    key_position = key_indices.index(key_index)
    return base_seed + key_position * (prompts // batch_size) + prompt_start // batch_size


def build_conditions(
    config: dict[str, Any],
    candidates: list[tuple[float | None, float | None]],
    key_indices: list[int],
    runner: TransformersNativeRunner,
) -> dict[tuple[int, float, float], dict[str, Any]]:
    watermark = load_json(Path(config["watermark_config"]))
    if watermark["variants"]["kgw"] != canonical.KGW_AUTHOR_VARIANT:
        raise ValueError("Joint feasibility requires author-canonical KGW")
    schedule = load_json(Path(config["key_schedule"]["source_config"]))["key_schedule"]
    keys = [int(value) for value in schedule["kgw"]]
    conditions: dict[tuple[int, float, float], dict[str, Any]] = {}
    shared_table = None
    for key_index in key_indices:
        for gamma, delta in candidates:
            if gamma is None or delta is None:
                continue
            settings = dict(
                watermark["kgw"],
                hashing_key=keys[key_index],
                greenlist_ratio=float(gamma),
                bias=float(delta),
            )
            generation_config = canonical.build_kgw_config(
                settings, canonical.KGW_AUTHOR_VARIANT
            )
            processor = generation_config.construct_processor(
                runner.model.config.vocab_size, runner.device
            )
            if shared_table is None:
                shared_table = processor.fixed_table
            else:
                processor.fixed_table = shared_table
            conditions[(key_index, float(gamma), float(delta))] = {
                "scheme": "kgw",
                "key_id": f"kgw-{key_index:02d}",
                "key_index": key_index,
                "gamma": float(gamma),
                "delta": float(delta),
                "variant": canonical.KGW_AUTHOR_VARIANT,
                "generation_config": generation_config,
                "scorer": CompactKGWScorer(
                    processor=processor,
                    variant=canonical.KGW_AUTHOR_VARIANT,
                    key_id=f"kgw-{key_index:02d}",
                    hashing_key=keys[key_index],
                    greenlist_ratio=float(gamma),
                ),
                "counter_key": (float(gamma), float(delta), keys[key_index]),
            }
    return conditions


def validate_thresholds(config: dict[str, Any]) -> dict[tuple[float, str, int], float]:
    path = Path(config["development_null_thresholds"]["artifact"])
    artifact = load_json(path)
    if artifact.get("status") != "kgw_joint_development_thresholds_frozen":
        raise ValueError("Gamma-specific development thresholds are not frozen")
    if artifact.get("protocol_id") != config["protocol_id"]:
        raise ValueError("Threshold artifact and protocol differ")
    if artifact.get("separation", {}).get("confirmation_scores_loaded") is not False:
        raise ValueError("Threshold artifact does not prove confirmation separation")
    lookup = {
        (float(row["gamma"]), row["key_id"], int(row["length"])): float(
            row["threshold"]
        )
        for row in artifact["operational_thresholds"]
    }
    if len(lookup) != int(config["development_null_thresholds"]["primary_cells"]):
        raise ValueError("Threshold artifact does not contain all 90 cells")
    return lookup


def validate_existing(
    output_dir: Path,
    plan: list[dict[str, Any]],
    prompts: list[dict[str, Any]],
    batch_size: int,
    input_sha256: dict[str, str],
    generation: dict[str, Any],
) -> tuple[int, list[dict[str, Any]], Counter[str], int]:
    paths = batch_paths(output_dir)
    if [path.name for path in paths] != [
        f"batch-{index:06d}.json" for index in range(len(paths))
    ]:
        raise ValueError("Existing stage batches are not contiguous")
    audits: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    noops = 0
    keys = [int(value) for value in generation["target_key_indices"]]
    prompts_per_condition = int(
        generation.get("prompts_per_key_candidate", generation.get("prompts_per_key"))
    )
    for index, path in enumerate(paths):
        batch, expected = load_json(path), plan[index]
        if batch.get("batch_index") != index or batch.get("input_sha256") != input_sha256:
            raise ValueError(f"Batch identity mismatch: {path}")
        for field in ("key_id", "condition", "gamma", "delta", "prompt_start"):
            if batch.get(field) != expected[field]:
                raise ValueError(f"Batch plan mismatch: {path}/{field}")
        expected_seed = paired_batch_seed(
            int(generation["base_seed"]),
            keys,
            int(expected["key_index"]),
            int(expected["prompt_start"]),
            batch_size,
            prompts_per_condition,
        )
        if batch.get("batch_seed") != expected_seed:
            raise ValueError(f"Paired seed mismatch: {path}")
        records = batch.get("records")
        if not isinstance(records, list) or len(records) != batch_size:
            raise ValueError(f"Incomplete batch: {path}")
        expected_ids = [
            row["id"]
            for row in prompts[
                expected["prompt_start"] : expected["prompt_start"] + batch_size
            ]
        ]
        if [row["prompt_id"] for row in records] != expected_ids:
            raise ValueError(f"Prompt order mismatch: {path}")
        audits.extend(batch.get("native_score_audits", []))
        label = (
            f"{expected['key_id']}/control"
            if expected["condition"] == "unwatermarked_control"
            else f"{expected['key_id']}/gamma-{expected['gamma']}/delta-{expected['delta']}"
        )
        counts.update([label] * len(records))
        noops += int(batch.get("empty_rejection_noop_events", 0))
    return len(paths), audits, counts, noops


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    parser.add_argument("--stage", choices=("stage_a", "stage_b"), required=True)
    parser.add_argument("--authorization", type=Path)
    parser.add_argument("--selection", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--limit-batches", type=int)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    config = load_json(args.config)
    validate_protocol(config)
    manifest_hashes = validate_manifests(config)
    stage = args.stage
    stage_generation = config["generation"][stage]
    selection_path = args.selection or (
        Path(config["stage_a_selection_rule"]["selection_artifact"])
        if stage == "stage_b"
        else None
    )
    candidates = stage_candidates(config, stage, selection_path)
    keys = [int(value) for value in stage_generation["target_key_indices"]]
    prompts_per_condition = int(
        stage_generation.get(
            "prompts_per_key_candidate", stage_generation.get("prompts_per_key")
        )
    )
    batch_size = int(config["generation"]["batch_size"])
    plan = batch_plan(keys, candidates, prompts_per_condition, batch_size)
    target_batches = len(plan)
    limit = target_batches if args.limit_batches is None else int(args.limit_batches)
    if not 1 <= limit <= target_batches:
        parser.error(f"--limit-batches must be in [1, {target_batches}]")
    output_dir = args.output_dir or RESULT_ROOT / stage.replace("_", "-") / "run"
    manifest_path = Path(config["prompt_manifests"][stage])
    thresholds_path = Path(config["development_null_thresholds"]["artifact"])

    if args.dry_run:
        print(
            json.dumps(
                {
                    "status": "configuration_valid_generation_unauthorized",
                    "protocol_id": config["protocol_id"],
                    "stage": stage,
                    "keys": keys,
                    "candidates": [
                        {"condition": "control"}
                        if gamma is None
                        else {"gamma": gamma, "delta": delta}
                        for gamma, delta in candidates
                    ],
                    "prompts_per_condition": prompts_per_condition,
                    "target_batches": target_batches,
                    "selected_batches": limit,
                    "target_outputs": target_batches * batch_size,
                    "thresholds_exist": thresholds_path.exists(),
                    "prompt_manifest_sha256": manifest_hashes[stage],
                    "generation_authorized": False,
                },
                indent=2,
            )
        )
        return 0
    if args.authorization is None:
        parser.error("generation requires --authorization")
    validate_authorization(args.config, args.authorization)
    validate_thresholds(config)

    manifest = load_json(manifest_path)
    prompts = manifest["records"]
    input_sha256 = {
        "protocol_config": file_sha256(args.config),
        "authorization": file_sha256(args.authorization),
        "prompt_manifest": file_sha256(manifest_path),
        "watermark_config": file_sha256(Path(config["watermark_config"])),
        "key_schedule_source": file_sha256(Path(config["key_schedule"]["source_config"])),
        "development_thresholds": file_sha256(thresholds_path),
        "runner_source": source_sha256(),
    }
    if stage == "stage_b" and selection_path is not None:
        input_sha256["stage_a_selection"] = file_sha256(selection_path)

    completed, audits, counts, noops = validate_existing(
        output_dir, plan, prompts, batch_size, input_sha256, stage_generation
    )
    if completed >= limit:
        print(json.dumps({"status": "already_complete", "batches": completed}, indent=2))
        return 0

    install_instrumented_empty_index_safeguard()
    runner = TransformersNativeRunner(
        model_id=config["model"]["id"],
        revision=config["model"]["revision"],
        device=config["model"]["device"],
    )
    conditions = build_conditions(config, candidates, keys, runner)
    lengths = [int(value) for value in stage_generation["paired_prefix_lengths"]]
    torch, transformers = require_ml_dependencies()
    for batch_index in range(completed, limit):
        spec = plan[batch_index]
        start = int(spec["prompt_start"])
        prompt_batch = prompts[start : start + batch_size]
        batch_seed = paired_batch_seed(
            int(stage_generation["base_seed"]),
            keys,
            int(spec["key_index"]),
            start,
            batch_size,
            prompts_per_condition,
        )
        condition = None
        counter_before = 0
        if spec["condition"] == "watermarked":
            condition = conditions[
                (int(spec["key_index"]), float(spec["gamma"]), float(spec["delta"]))
            ]
            counter_before = EMPTY_REJECTION_COUNTS[condition["counter_key"]]
        generated_rows = runner.generate_batch(
            [row["prompt"] for row in prompt_batch],
            seed=batch_seed,
            min_new_tokens=int(stage_generation["generated_tokens"]),
            max_new_tokens=int(stage_generation["generated_tokens"]),
            temperature=float(config["generation"]["temperature"]),
            top_k=int(config["generation"]["top_k"]),
            watermark_config=(condition["generation_config"] if condition else None),
        )
        batch_noops = (
            EMPTY_REJECTION_COUNTS[condition["counter_key"]] - counter_before
            if condition
            else 0
        )
        batch_records: list[dict[str, Any]] = []
        batch_audits: list[dict[str, Any]] = []
        for stream_index, (prompt, generated) in enumerate(
            zip(prompt_batch, generated_rows, strict=True)
        ):
            _, continuation, text_value = generated
            if len(continuation) != int(stage_generation["generated_tokens"]):
                raise RuntimeError(f"Unexpected generated length: {prompt['id']}")
            prefix_results = []
            if condition:
                scores = condition["scorer"].score_prefixes(continuation, lengths)
                for length in lengths:
                    score = scores[length]
                    if not math.isfinite(float(score["value"])) or int(
                        score["eligible_positions"]
                    ) <= 0:
                        raise RuntimeError(f"Invalid compact score: {prompt['id']}")
                    prefix_results.append({"length": length, "score": score})
                if start == 0 and stream_index == 0:
                    batch_audits.extend(
                        audit_score(runner, condition, continuation, row["length"], row["score"])
                        for row in prefix_results
                    )
            batch_records.append(
                {
                    "prompt_id": prompt["id"],
                    "source_shard": prompt["source_shard"],
                    "source_row": prompt["source_row"],
                    "source_prompt_id": prompt["source_prompt_id"],
                    "prompt_sha256": prompt["prompt_sha256"],
                    "condition": spec["condition"],
                    "scheme": "kgw" if condition else None,
                    "key_id": spec["key_id"],
                    "gamma": spec["gamma"],
                    "delta": spec["delta"],
                    "variant": condition["variant"] if condition else None,
                    "batch_seed": batch_seed,
                    "batch_stream_index": stream_index,
                    "generated_tokens": len(continuation),
                    "token_ids": continuation,
                    "decoded_character_count": len(text_value),
                    "decoded_empty": not bool(text_value.strip()),
                    "decoded_character_count_by_prefix": {
                        str(length): len(
                            runner.tokenizer.decode(
                                continuation[:length], skip_special_tokens=True
                            )
                        )
                        for length in lengths
                    },
                    "decoded_empty_by_prefix": {
                        str(length): not bool(
                            runner.tokenizer.decode(
                                continuation[:length], skip_special_tokens=True
                            ).strip()
                        )
                        for length in lengths
                    },
                    "output_sha256": sha256_text(text_value),
                    "text": text_value,
                    "prefix_results": prefix_results,
                }
            )
        atomic_json(
            output_dir / "batches" / f"batch-{batch_index:06d}.json",
            {
                "schema_version": 1,
                "protocol_id": config["protocol_id"],
                "stage": stage,
                "batch_index": batch_index,
                "key_id": spec["key_id"],
                "condition": spec["condition"],
                "gamma": spec["gamma"],
                "delta": spec["delta"],
                "prompt_start": start,
                "batch_seed": batch_seed,
                "empty_rejection_noop_events": batch_noops,
                "input_sha256": input_sha256,
                "native_score_audits": batch_audits,
                "records": batch_records,
            },
        )
        audits.extend(batch_audits)
        label = (
            f"{spec['key_id']}/control"
            if condition is None
            else f"{spec['key_id']}/gamma-{spec['gamma']}/delta-{spec['delta']}"
        )
        counts.update([label] * batch_size)
        noops += batch_noops
        completed = batch_index + 1
        complete = completed == target_batches
        metadata = {
            "schema_version": 1,
            "status": (
                f"kgw_joint_{stage}_complete" if complete else f"kgw_joint_{stage}_partial"
            ),
            "protocol_id": config["protocol_id"],
            "stage": stage,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "completed_batches": completed,
            "target_batches": target_batches,
            "completed_outputs": completed * batch_size,
            "target_outputs": target_batches * batch_size,
            "input_sha256": input_sha256,
            "condition_output_counts": dict(sorted(counts.items())),
            "empty_rejection_noop_events": noops,
            "native_score_audits": audits,
            "confirmation_scores_used": False,
            "environment": {
                "python": platform.python_version(),
                "platform": platform.platform(),
                "torch": torch.__version__,
                "transformers": transformers.__version__,
                "package_version": importlib.metadata.version("ai-watermarks-research"),
                "git_commit": git_commit(),
                "git_dirty": git_dirty(),
            },
        }
        atomic_json(output_dir / "run.json", metadata)
        print(
            f"checkpoint batch {completed}/{target_batches} outputs {completed * batch_size}/{target_batches * batch_size}",
            flush=True,
        )
    print(
        json.dumps(
            {
                "status": metadata["status"],
                "batches": completed,
                "outputs": completed * batch_size,
                "output_dir": str(output_dir),
                "run_digest": run_digest(output_dir),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
