"""Versioned KGW-bias runner with an empty-index dtype safeguard."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import Any

from . import canonical
from . import kgw_bias_development as base
from .native import require_ml_dependencies
from .variance_pilot import file_sha256


BASE_SOURCE_SHA256 = base.source_sha256


def install_empty_index_safeguard() -> None:
    """Make the author loop's empty result a valid integer no-op index."""
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
            return torch.stack(final_greenlist).to(device=input_seq.device, dtype=torch.long)
        return torch.empty(0, device=input_seq.device, dtype=torch.long)

    processor_class._score_rejection_sampling = score_rejection_sampling


def combined_source_sha256() -> str:
    digest = hashlib.sha256()
    digest.update(bytes.fromhex(BASE_SOURCE_SHA256()))
    digest.update(bytes.fromhex(file_sha256(Path(__file__))))
    return digest.hexdigest()


def main(argv: list[str] | None = None) -> int:
    install_empty_index_safeguard()
    base.source_sha256 = combined_source_sha256
    arguments = list(sys.argv[1:] if argv is None else argv)
    if "--config" not in arguments:
        arguments.extend(["--config", "configs/phase2-v2-kgw-bias-development-v2.json"])
    if "--output-dir" not in arguments:
        arguments.extend(["--output-dir", "results/phase2-v2-kgw-bias-development-v2/run"])
    return base.main(arguments)


if __name__ == "__main__":
    raise SystemExit(main())
