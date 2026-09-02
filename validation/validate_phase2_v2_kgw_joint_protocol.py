#!/usr/bin/env python3
"""Validate the preregistered KGW joint-feasibility protocol and frozen manifests."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ai_watermarks_phase2.kgw_joint_protocol import (
    CONFIG_PATH,
    validate_manifests,
    validate_protocol,
)
from ai_watermarks_phase2.smoke import load_json


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    parser.add_argument("--require-manifests", action="store_true")
    args = parser.parse_args(argv)
    config = load_json(args.config)
    result = validate_protocol(config)
    if args.require_manifests:
        result["prompt_manifest_sha256"] = validate_manifests(config)
    result.update(
        {
            "status": "kgw_joint_feasibility_protocol_valid",
            "protocol_id": config["protocol_id"],
            "generation_authorized": False,
        }
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
