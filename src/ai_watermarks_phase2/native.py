"""Optional Transformers-native watermark generation and scoring adapters."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class NativePositionTrace:
    """Auditable detector state for one token position."""

    position: int
    token_id: int
    context_token_ids: tuple[int, ...]
    eligible: bool
    exclusion_reason: str | None
    values: dict[str, float | int | bool | list[int] | None]


@dataclass(frozen=True)
class NativeScore:
    scheme: str
    statistic_name: str
    value: float
    eligible_positions: int
    auxiliary: dict[str, float | int | str | bool]
    position_traces: tuple[NativePositionTrace, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def require_ml_dependencies() -> tuple[Any, Any]:
    try:
        import torch
        import transformers
    except ImportError as exc:
        raise RuntimeError(
            "Phase 2 ML dependencies are missing. Run `uv sync --extra ml`."
        ) from exc
    return torch, transformers


class TransformersNativeRunner:
    """Generate and score KGW and SynthID-Text using Transformers implementations."""

    def __init__(self, model_id: str, revision: str, device: str = "cpu") -> None:
        torch, transformers = require_ml_dependencies()
        self.torch = torch
        self.transformers = transformers
        self.device = device
        self.model_id = model_id
        self.revision = revision
        self.tokenizer = transformers.AutoTokenizer.from_pretrained(
            model_id, revision=revision
        )
        self.tokenizer.padding_side = "left"
        self.model = transformers.AutoModelForCausalLM.from_pretrained(
            model_id, revision=revision
        ).to(device)
        self.model.eval()
        if self.tokenizer.pad_token_id is None:
            self.tokenizer.pad_token_id = self.tokenizer.eos_token_id

    def generate(
        self,
        prompt: str,
        *,
        seed: int,
        min_new_tokens: int,
        max_new_tokens: int,
        temperature: float,
        top_k: int,
        watermark_config: Any | None,
    ) -> tuple[list[int], list[int], str]:
        outputs = self.generate_batch(
            [prompt],
            seed=seed,
            min_new_tokens=min_new_tokens,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_k=top_k,
            watermark_config=watermark_config,
        )
        return outputs[0]

    def generate_batch(
        self,
        prompts: list[str],
        *,
        seed: int,
        min_new_tokens: int,
        max_new_tokens: int,
        temperature: float,
        top_k: int,
        watermark_config: Any | None,
    ) -> list[tuple[list[int], list[int], str]]:
        """Generate with the caller's watermarking configuration, or none at all.

        The configuration object selects the keyed primitive on the generation
        path, because `generate` builds its processor through the config's own
        `construct_processor`. Passing the same object to the scoring methods
        keeps generation and detection on one variant.
        """

        torch = self.torch
        encoded = self.tokenizer(prompts, padding=True, return_tensors="pt").to(
            self.device
        )
        prompt_width = encoded["input_ids"].shape[1]
        self.transformers.set_seed(seed)
        generation_args = {
            **encoded,
            "do_sample": True,
            "min_new_tokens": min_new_tokens,
            "max_new_tokens": max_new_tokens,
            "temperature": temperature,
            "top_k": top_k,
            "pad_token_id": self.tokenizer.pad_token_id,
        }
        if watermark_config is not None:
            generation_args["watermarking_config"] = watermark_config
        with torch.inference_mode():
            output = self.model.generate(**generation_args)
        rows: list[tuple[list[int], list[int], str]] = []
        for output_row in output:
            full_tokens = output_row.detach().cpu().tolist()
            continuation = full_tokens[prompt_width:]
            text = self.tokenizer.decode(continuation, skip_special_tokens=True)
            rows.append((full_tokens, continuation, text))
        return rows

    def score_kgw(
        self,
        full_tokens: list[int],
        *,
        first_generated_position: int,
        config: Any,
        variant: str,
        ignore_repeated_ngrams: bool,
    ) -> NativeScore:
        torch = self.torch
        detector = self.transformers.WatermarkDetector(
            model_config=self.model.config,
            device=self.device,
            watermarking_config=config,
            ignore_repeated_ngrams=ignore_repeated_ngrams,
        )
        # The detector builds a stock processor from the config's fields, which
        # discards any variant-specific keying. Rebuild it through the config so
        # detection uses the same primitive as generation.
        detector.processor = config.construct_processor(
            self.model.config.vocab_size, self.device
        )
        ids = torch.tensor(full_tokens, dtype=torch.long, device=self.device)
        is_selfhash = detector.processor.seeding_scheme == "selfhash"
        window_size = detector.processor.context_width + 1 - int(is_selfhash)
        seen: set[tuple[int, ...]] = set()
        hits = 0
        scored = 0
        traces: list[NativePositionTrace] = []
        for position in range(len(full_tokens)):
            if position < window_size - 1:
                traces.append(
                    NativePositionTrace(
                        position=position,
                        token_id=full_tokens[position],
                        context_token_ids=tuple(full_tokens[: position + 1]),
                        eligible=False,
                        exclusion_reason="insufficient_context",
                        values={"green_hit": None},
                    )
                )
                continue
            if position < first_generated_position:
                traces.append(
                    NativePositionTrace(
                        position=position,
                        token_id=full_tokens[position],
                        context_token_ids=tuple(
                            full_tokens[position - window_size + 1 : position + 1]
                        ),
                        eligible=False,
                        exclusion_reason="before_generated_boundary",
                        values={"green_hit": None},
                    )
                )
                continue
            ngram = tuple(full_tokens[position - window_size + 1 : position + 1])
            if ignore_repeated_ngrams and ngram in seen:
                traces.append(
                    NativePositionTrace(
                        position=position,
                        token_id=full_tokens[position],
                        context_token_ids=ngram,
                        eligible=False,
                        exclusion_reason="repeated_ngram",
                        values={"green_hit": None},
                    )
                )
                continue
            seen.add(ngram)
            prefix = ids[position - window_size + 1 : position + 1]
            if not is_selfhash:
                prefix = prefix[:-1]
            target = int(ids[position].item())
            green_hit = bool(detector._get_ngram_score(prefix, target))
            hits += int(green_hit)
            scored += 1
            traces.append(
                NativePositionTrace(
                    position=position,
                    token_id=target,
                    context_token_ids=ngram,
                    eligible=True,
                    exclusion_reason=None,
                    values={"green_hit": green_hit},
                )
            )
        gamma = float(detector.greenlist_ratio)
        z_score = (
            (hits - gamma * scored) / math.sqrt(scored * gamma * (1 - gamma))
            if scored
            else float("nan")
        )
        return NativeScore(
            scheme="kgw",
            statistic_name="z_score",
            value=z_score,
            eligible_positions=scored,
            auxiliary={
                "variant": variant,
                "green_tokens": hits,
                "green_fraction": hits / scored if scored else float("nan"),
                "greenlist_ratio": gamma,
                "ignore_repeated_ngrams": ignore_repeated_ngrams,
                "window_size": window_size,
            },
            position_traces=tuple(traces),
        )

    def score_synthid(
        self,
        full_tokens: list[int],
        *,
        first_generated_position: int,
        config: Any,
        variant: str,
    ) -> NativeScore:
        torch = self.torch
        processor = config.construct_processor(
            vocab_size=self.model.config.vocab_size, device=self.device
        )
        ids = torch.tensor([full_tokens], dtype=torch.long, device=self.device)
        g_values = processor.compute_g_values(ids)
        repetition_mask = processor.compute_context_repetition_mask(ids)
        eos_mask = processor.compute_eos_token_mask(
            ids, self.tokenizer.eos_token_id
        )[:, processor.ngram_len - 1 :]
        mask = repetition_mask * eos_mask
        token_positions = torch.arange(
            processor.ngram_len - 1, len(full_tokens), device=self.device
        )
        mask = mask * (token_positions[None, :] >= first_generated_position)
        eligible = int(mask.sum().item())
        depth = int(g_values.shape[-1])
        score = (
            float((g_values * mask.unsqueeze(-1)).sum().item() / (eligible * depth))
            if eligible
            else float("nan")
        )
        traces: list[NativePositionTrace] = []
        offset = processor.ngram_len - 1
        for position in range(len(full_tokens)):
            if position < offset:
                traces.append(
                    NativePositionTrace(
                        position=position,
                        token_id=full_tokens[position],
                        context_token_ids=tuple(full_tokens[: position + 1]),
                        eligible=False,
                        exclusion_reason="insufficient_context",
                        values={
                            "g_values": None,
                            "repetition_mask": None,
                            "eos_mask": None,
                        },
                    )
                )
                continue
            trace_index = position - offset
            repetition_allowed = bool(repetition_mask[0, trace_index].item())
            eos_allowed = bool(eos_mask[0, trace_index].item())
            generated = position >= first_generated_position
            is_eligible = repetition_allowed and eos_allowed and generated
            if not generated:
                exclusion_reason = "before_generated_boundary"
            elif not eos_allowed:
                exclusion_reason = "eos_or_after_eos"
            elif not repetition_allowed:
                exclusion_reason = "repeated_context"
            else:
                exclusion_reason = None
            traces.append(
                NativePositionTrace(
                    position=position,
                    token_id=full_tokens[position],
                    context_token_ids=tuple(
                        full_tokens[position - offset : position + 1]
                    ),
                    eligible=is_eligible,
                    exclusion_reason=exclusion_reason,
                    values={
                        "g_values": [
                            int(value)
                            for value in g_values[0, trace_index].detach().cpu().tolist()
                        ],
                        "repetition_mask": repetition_allowed,
                        "eos_mask": eos_allowed,
                    },
                )
            )
        return NativeScore(
            scheme="synthid",
            statistic_name="mean_g_value",
            value=score,
            eligible_positions=eligible,
            auxiliary={
                "variant": variant,
                "watermarking_depth": depth,
                "ngram_len": int(processor.ngram_len),
                "repeated_context_masking": True,
            },
            position_traces=tuple(traces),
        )
