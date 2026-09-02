"""Validation and planning helpers for the final KGW joint-parameter study."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from .calibration_gate import clopper_pearson_upper, maximum_passing_exceedances
from .key_schedule import SCHEDULE_SEED, derive_schedule
from .smoke import load_json
from .variance_pilot import file_sha256


PROTOCOL_ID = "phase2-v2-kgw-joint-feasibility-v1"
CONFIG_PATH = Path("configs/phase2-v2-kgw-joint-feasibility.json")
EXPECTED_GAMMAS = (0.25, 0.50, 0.70)
EXPECTED_DELTAS = (2.0, 2.5, 3.0, 4.0)
EXPECTED_STAGE_A_KEYS = (3, 5, 7, 8)
EXPECTED_STAGE_B_KEYS = tuple(range(10))


def candidate_grid(config: dict[str, Any]) -> list[tuple[float, float]]:
    family = config["parameter_family"]
    gammas = [float(value) for value in family["greenlist_ratios"]]
    deltas = [float(value) for value in family["biases"]]
    return [(gamma, delta) for gamma in gammas for delta in deltas]


def binomial_upper_tail(samples: int, successes: int, probability: float) -> float:
    """Return P[X >= successes] for X ~ Binomial(samples, probability)."""
    if not 0 <= successes <= samples:
        raise ValueError("successes must lie in [0, samples]")
    if not 0.0 <= probability <= 1.0:
        raise ValueError("probability must lie in [0, 1]")
    return sum(
        math.comb(samples, value)
        * probability**value
        * (1.0 - probability) ** (samples - value)
        for value in range(successes, samples + 1)
    )


def clopper_pearson_lower(successes: int, samples: int, alpha: float) -> float:
    """Exact one-sided lower binomial confidence limit."""
    if successes == 0:
        return 0.0
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must lie in (0, 1)")
    lower, upper = 0.0, 1.0
    for _ in range(100):
        midpoint = (lower + upper) / 2.0
        if binomial_upper_tail(samples, successes, midpoint) < alpha:
            lower = midpoint
        else:
            upper = midpoint
    return (lower + upper) / 2.0


def expected_plan(config: dict[str, Any]) -> dict[str, int]:
    generation = config["generation"]
    stage_a = generation["stage_a"]
    stage_b = generation["stage_b"]
    candidates = len(candidate_grid(config))
    a_prompts = int(stage_a["prompts_per_key_candidate"])
    a_keys = len(stage_a["target_key_indices"])
    b_prompts = int(stage_b["prompts_per_key"])
    b_keys = len(stage_b["target_key_indices"])
    return {
        "candidate_count": candidates,
        "development_null_outputs": int(generation["development_null"]["outputs"]),
        "stage_a_watermarked_outputs": candidates * a_keys * a_prompts,
        "stage_a_control_outputs": a_keys * a_prompts,
        "stage_a_total_outputs": (candidates + 1) * a_keys * a_prompts,
        "stage_b_candidate_outputs": b_keys * b_prompts,
        "stage_b_control_outputs": b_keys * b_prompts,
        "stage_b_total_outputs": 2 * b_keys * b_prompts,
    }


def validate_protocol(config: dict[str, Any]) -> dict[str, Any]:
    if config.get("protocol_id") != PROTOCOL_ID:
        raise ValueError("Unexpected KGW joint-feasibility protocol ID")
    if config.get("status") != "preregistered_pending_compute_approval":
        raise ValueError("Protocol is not in its preregistered pending-approval state")
    if tuple(float(value) for value in config["parameter_family"]["greenlist_ratios"]) != EXPECTED_GAMMAS:
        raise ValueError("Gamma grid differs from the approved decision")
    if tuple(float(value) for value in config["parameter_family"]["biases"]) != EXPECTED_DELTAS:
        raise ValueError("Delta grid differs from the approved decision")
    if len(candidate_grid(config)) != int(config["parameter_family"]["candidate_count"]):
        raise ValueError("Candidate count differs from the Cartesian grid")
    if config["variant"]["id"] != "kgw_author_selfhash_v1":
        raise ValueError("The study requires the author-canonical KGW variant")
    if int(config["variant"]["context_width"]) != 4:
        raise ValueError("Canonical SelfHash context width must remain four")

    generation = config["generation"]
    if int(generation["batch_size"]) != 5:
        raise ValueError("Atomic batch size must remain five")
    if tuple(int(value) for value in generation["stage_a"]["target_key_indices"]) != EXPECTED_STAGE_A_KEYS:
        raise ValueError("Stage-A weak-key set differs from the decision")
    if tuple(int(value) for value in generation["stage_b"]["target_key_indices"]) != EXPECTED_STAGE_B_KEYS:
        raise ValueError("Stage-B key set must contain all ten frozen keys")
    for role in ("development_null", "stage_a", "stage_b"):
        role_generation = generation[role]
        lengths = [int(value) for value in role_generation["paired_prefix_lengths"]]
        if lengths != sorted(set(lengths)) or lengths[-1] != int(role_generation["generated_tokens"]):
            raise ValueError(f"Invalid paired prefix lengths for {role}")

    plan = expected_plan(config)
    declared = generation["stage_a"]
    if plan["stage_a_watermarked_outputs"] != int(declared["watermarked_outputs"]):
        raise ValueError("Stage-A watermarked output total differs")
    if plan["stage_a_control_outputs"] != int(declared["unwatermarked_control_outputs"]):
        raise ValueError("Stage-A control output total differs")
    if plan["stage_a_total_outputs"] != int(declared["total_outputs"]):
        raise ValueError("Stage-A total output count differs")
    declared_b = generation["stage_b"]
    if plan["stage_b_candidate_outputs"] != int(declared_b["selected_candidate_outputs"]):
        raise ValueError("Stage-B candidate output total differs")
    if plan["stage_b_control_outputs"] != int(declared_b["unwatermarked_control_outputs"]):
        raise ValueError("Stage-B control output total differs")
    if plan["stage_b_total_outputs"] != int(declared_b["total_outputs"]):
        raise ValueError("Stage-B total output count differs")

    thresholds = config["development_null_thresholds"]
    samples = int(thresholds["samples"])
    cells = int(thresholds["primary_cells"])
    familywise_alpha = 1.0 - float(thresholds["familywise_confidence"])
    allowed = maximum_passing_exceedances(
        samples=samples,
        target_fpr=float(thresholds["design_fpr"]),
        familywise_alpha=familywise_alpha,
        cells=cells,
    )
    if cells != len(EXPECTED_GAMMAS) * 10 * 3:
        raise ValueError("Development-null family must contain 90 cells")
    if allowed != int(thresholds["maximum_strict_exceedances"]):
        raise ValueError("Exact-binomial maximum differs from the config")
    per_cell_alpha = familywise_alpha / cells
    if not math.isclose(per_cell_alpha, float(thresholds["per_cell_alpha"]), rel_tol=0.0, abs_tol=1e-16):
        raise ValueError("Per-cell alpha differs from the Bonferroni allocation")

    detection = config["detection_guardrail"]
    if int(detection["samples_per_cell"]) != 100 or int(detection["minimum_detections_per_cell"]) != 80:
        raise ValueError("Detection screen must remain 80 of 100 per cell")
    if not math.isclose(float(detection["minimum_detection_rate_per_cell"]), 0.8):
        raise ValueError("Detection-rate target must remain 0.8")
    if float(config["compute_budget"]["cpu_wall_clock_cap_hours"]) != 24.0:
        raise ValueError("CPU compute cap differs from the approved planning envelope")
    if float(config["compute_budget"]["storage_cap_gb"]) != 0.5:
        raise ValueError("Storage cap differs from the approved planning envelope")
    if int(config["compute_budget"]["manual_review_max_pair_ratings"]) != 1300:
        raise ValueError("Manual-review cap must cover Stage A and conditional Stage B")
    if config["separation"]["study_generation_authorized"] is not False:
        raise ValueError("Generation cannot be authorized inside the preregistration")
    if config["separation"].get("protocol_freeze_artifact") != (
        "results/phase2-v2-kgw-joint-feasibility/protocol-freeze.json"
    ):
        raise ValueError("Protocol freeze path differs from the bounded study")

    schedule_source = load_json(Path(config["key_schedule"]["source_config"]))
    schedule = schedule_source["key_schedule"]
    if config["key_schedule"]["seed"] != SCHEDULE_SEED or schedule.get("seed") != SCHEDULE_SEED:
        raise ValueError("Key schedule seed differs")
    if schedule["kgw"] != derive_schedule(10)["kgw"]:
        raise ValueError("KGW key schedule differs from its frozen derivation")

    return {
        **plan,
        "development_null_primary_cells": cells,
        "development_null_maximum_strict_exceedances": allowed,
        "development_null_upper_bound_at_maximum": clopper_pearson_upper(
            allowed, samples, per_cell_alpha
        ),
        "development_null_upper_bound_at_next": clopper_pearson_upper(
            allowed + 1, samples, per_cell_alpha
        ),
        "detection_lower_bound_at_gate": clopper_pearson_lower(80, 100, 0.05),
    }


def manifest_prompt_hashes(path: Path, expected_status: str, expected_records: int) -> set[str]:
    manifest = load_json(path)
    if manifest.get("status") != expected_status:
        raise ValueError(f"Unexpected prompt-manifest status: {path}")
    if manifest.get("protocol_id") != PROTOCOL_ID:
        raise ValueError(f"Prompt manifest has wrong protocol: {path}")
    records = manifest.get("records")
    if not isinstance(records, list) or len(records) != expected_records:
        raise ValueError(f"Prompt manifest has wrong record count: {path}")
    hashes = {str(row["prompt_sha256"]) for row in records}
    if len(hashes) != expected_records:
        raise ValueError(f"Prompt manifest contains duplicate hashes: {path}")
    return hashes


def validate_manifests(config: dict[str, Any]) -> dict[str, str]:
    paths = {role: Path(path) for role, path in config["prompt_manifests"].items()}
    counts = config["prompt_selection"]["roles"]
    hashes = {
        role: manifest_prompt_hashes(
            path,
            f"kgw_joint_{role}_prompt_manifest_frozen",
            int(counts[role]),
        )
        for role, path in paths.items()
    }
    for left, right in (("development_null", "stage_a"), ("development_null", "stage_b"), ("stage_a", "stage_b")):
        if hashes[left] & hashes[right]:
            raise ValueError(f"Prompt overlap between {left} and {right}")
    return {role: file_sha256(path) for role, path in paths.items()}


def validate_authorization(config_path: Path, authorization_path: Path) -> dict[str, Any]:
    config = load_json(config_path)
    validate_protocol(config)
    authorization = load_json(authorization_path)
    if authorization.get("status") != "kgw_joint_feasibility_generation_approved":
        raise ValueError("Generation authorization is absent or unapproved")
    if authorization.get("protocol_id") != PROTOCOL_ID:
        raise ValueError("Authorization protocol ID differs")
    if authorization.get("protocol_config_sha256") != file_sha256(config_path):
        raise ValueError("Authorization does not match the frozen protocol config")
    freeze_path = Path(config["separation"]["protocol_freeze_artifact"])
    if not freeze_path.exists():
        raise ValueError("The protocol fingerprint freeze does not exist")
    if authorization.get("protocol_freeze_sha256") != file_sha256(freeze_path):
        raise ValueError("Authorization does not match the protocol fingerprint freeze")
    if not str(authorization.get("approved_by", "")).strip():
        raise ValueError("Authorization does not identify the approver")
    if not str(authorization.get("approved_at", "")).strip():
        raise ValueError("Authorization does not record the approval time")
    if authorization.get("approved_scope") != "development_null_stage_a_and_conditional_stage_b_only":
        raise ValueError("Authorization scope differs from the bounded study")
    if float(authorization.get("cpu_wall_clock_cap_hours", -1)) != float(config["compute_budget"]["cpu_wall_clock_cap_hours"]):
        raise ValueError("Authorization CPU cap differs from the protocol")
    if float(authorization.get("storage_cap_gb", -1)) != float(config["compute_budget"]["storage_cap_gb"]):
        raise ValueError("Authorization storage cap differs from the protocol")
    return authorization
