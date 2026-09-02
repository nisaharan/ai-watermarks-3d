#!/usr/bin/env python3
"""Freeze fingerprints for the preregistered KGW joint-feasibility study."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from ai_watermarks_phase2.kgw_joint_protocol import (
    CONFIG_PATH,
    validate_manifests,
    validate_protocol,
)
from ai_watermarks_phase2.smoke import load_json
from ai_watermarks_phase2.variance_pilot import file_sha256, write_result


IMPLEMENTATION_PATHS = (
    Path("src/ai_watermarks_phase2/kgw_joint_protocol.py"),
    Path("src/ai_watermarks_phase2/kgw_joint_null.py"),
    Path("src/ai_watermarks_phase2/kgw_joint_stage.py"),
    Path("validation/prepare_phase2_v2_kgw_joint_prompts.py"),
    Path("validation/validate_phase2_v2_kgw_joint_protocol.py"),
    Path("validation/fit_phase2_v2_kgw_joint_thresholds.py"),
    Path("validation/analyse_phase2_v2_kgw_joint_stage_a.py"),
    Path("validation/analyse_phase2_v2_kgw_joint_stage_b.py"),
    Path("validation/prepare_phase2_v2_kgw_blinded_review.py"),
    Path("validation/collate_phase2_v2_kgw_blinded_review.py"),
    Path("validation/freeze_phase2_v2_kgw_joint_protocol.py"),
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    config = load_json(args.config)
    validation = validate_protocol(config)
    manifest_hashes = validate_manifests(config)
    output = args.output or Path(config["separation"]["protocol_freeze_artifact"])
    if output.exists():
        raise FileExistsError(f"Refusing to replace protocol freeze: {output}")
    study_paths = (
        args.config,
        Path(config["decision_source"]),
        Path("docs/research-transformation/phase-2/kgw-joint-parameter-feasibility-protocol.md"),
        Path(config["source_config"]),
        Path(config["watermark_config"]),
        *(Path(path) for path in config["prompt_manifests"].values()),
        *IMPLEMENTATION_PATHS,
    )
    missing = [str(path) for path in study_paths if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Cannot freeze missing protocol inputs: {missing}")
    fingerprints = {str(path): file_sha256(path) for path in study_paths}
    artifact = {
        "schema_version": 1,
        "status": "kgw_joint_feasibility_protocol_frozen_pending_compute_approval",
        "protocol_id": config["protocol_id"],
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "generation_authorized": False,
        "confirmation_scores_loaded": False,
        "attacks_authorized": False,
        "compute_caps": {
            "cpu_wall_clock_cap_hours": config["compute_budget"]["cpu_wall_clock_cap_hours"],
            "storage_cap_gb": config["compute_budget"]["storage_cap_gb"],
        },
        "protocol_validation": validation,
        "prompt_manifest_sha256": manifest_hashes,
        "fingerprints": fingerprints,
        "next_required_action": "Obtain explicit user approval and create the separate authorization artifact; do not generate before approval.",
    }
    write_result(output, artifact)
    print(
        json.dumps(
            {
                "status": artifact["status"],
                "output": str(output),
                "output_sha256": file_sha256(output),
                "fingerprints": len(fingerprints),
                "generation_authorized": False,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
