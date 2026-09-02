"""Compact, reusable native scorers for multi-key variance experiments."""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Any, Sequence


@dataclass
class CompactKGWScorer:
    processor: Any
    variant: str
    key_id: str
    hashing_key: int
    greenlist_ratio: float
    ignore_repeated_ngrams: bool = True

    def score(self, tokens: Sequence[int]) -> dict[str, Any]:
        return self.score_prefixes(tokens, [len(tokens)])[len(tokens)]

    def score_prefixes(
        self, tokens: Sequence[int], lengths: Sequence[int]
    ) -> dict[int, dict[str, Any]]:
        torch = _torch()
        requested = sorted(set(int(length) for length in lengths))
        if not requested or requested[0] < 1 or requested[-1] > len(tokens):
            raise ValueError("prefix lengths must fall within the token sequence")
        is_selfhash = self.processor.seeding_scheme == "selfhash"
        window_size = self.processor.context_width + 1 - int(is_selfhash)
        seen: set[tuple[int, ...]] = set()
        hits = 0
        eligible = 0
        digest = hashlib.sha256()
        results: dict[int, dict[str, Any]] = {}
        for position in range(requested[-1]):
            if position < window_size - 1:
                if position + 1 in requested:
                    results[position + 1] = self._result(
                        eligible, hits, digest.hexdigest()
                    )
                continue
            ngram = tuple(tokens[position - window_size + 1 : position + 1])
            if not (self.ignore_repeated_ngrams and ngram in seen):
                seen.add(ngram)
                prefix = torch.tensor(
                    ngram, dtype=torch.long, device=self.processor.fixed_table.device
                )
                if not is_selfhash:
                    prefix = prefix[:-1]
                target = int(tokens[position])
                green_hit = bool(target in self.processor._get_greenlist_ids(prefix))
                hits += int(green_hit)
                eligible += 1
                digest.update(position.to_bytes(4, "big"))
                digest.update(bytes((int(green_hit),)))
            if position + 1 in requested:
                results[position + 1] = self._result(
                    eligible, hits, digest.copy().hexdigest()
                )
        return results

    def _result(self, eligible: int, hits: int, trace_sha256: str) -> dict[str, Any]:
        gamma = self.greenlist_ratio
        value = (
            (hits - gamma * eligible) / math.sqrt(eligible * gamma * (1.0 - gamma))
            if eligible
            else float("nan")
        )
        return {
            "scheme": "kgw",
            "variant": self.variant,
            "key_id": self.key_id,
            "hashing_key": self.hashing_key,
            "statistic_name": "z_score",
            "value": value,
            "eligible_positions": eligible,
            "green_tokens": hits,
            "green_fraction": hits / eligible if eligible else float("nan"),
            "greenlist_ratio": gamma,
            "trace_sha256": trace_sha256,
        }


@dataclass
class CompactSynthIDScorer:
    processor: Any
    variant: str
    key_id: str
    keys: tuple[int, ...]
    eos_token_id: int

    def score(self, tokens: Sequence[int]) -> dict[str, Any]:
        return self.score_prefixes(tokens, [len(tokens)])[len(tokens)]

    def score_prefixes(
        self, tokens: Sequence[int], lengths: Sequence[int]
    ) -> dict[int, dict[str, Any]]:
        torch = _torch()
        requested = sorted(set(int(length) for length in lengths))
        if (
            not requested
            or requested[0] < self.processor.ngram_len
            or requested[-1] > len(tokens)
        ):
            raise ValueError("prefix lengths must contain a complete n-gram")
        ids = torch.tensor([tokens], dtype=torch.long, device=self.processor.device)
        g_values = self.processor.compute_g_values(ids)
        repetition_mask = self.processor.compute_context_repetition_mask(ids)
        eos_mask = self.processor.compute_eos_token_mask(ids, self.eos_token_id)[
            :, self.processor.ngram_len - 1 :
        ]
        full_mask = repetition_mask * eos_mask
        depth = int(g_values.shape[-1])
        results: dict[int, dict[str, Any]] = {}
        for length in requested:
            positions = length - self.processor.ngram_len + 1
            mask = full_mask[:, :positions]
            prefix_g_values = g_values[:, :positions]
            eligible = int(mask.sum().item())
            g_sum = int((prefix_g_values * mask.unsqueeze(-1)).sum().item())
            digest = hashlib.sha256()
            digest.update(mask.detach().cpu().to(torch.uint8).numpy().tobytes())
            digest.update(
                prefix_g_values.detach().cpu().to(torch.uint8).numpy().tobytes()
            )
            results[length] = self._result(
                eligible, depth, g_sum, digest.hexdigest()
            )
        return results

    def _result(
        self, eligible: int, depth: int, g_sum: int, trace_sha256: str
    ) -> dict[str, Any]:
        value = g_sum / (eligible * depth) if eligible else float("nan")
        return {
            "scheme": "synthid",
            "variant": self.variant,
            "key_id": self.key_id,
            "keys": list(self.keys),
            "statistic_name": "mean_g_value",
            "value": value,
            "eligible_positions": eligible,
            "watermarking_depth": depth,
            "g_value_sum": g_sum,
            "trace_sha256": trace_sha256,
        }


def _torch() -> Any:
    from .native import require_ml_dependencies

    torch, _ = require_ml_dependencies()
    return torch
