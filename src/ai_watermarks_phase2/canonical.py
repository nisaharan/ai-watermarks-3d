"""Author-canonical keyed primitives for the Phase 2 watermark variants.

The Transformers ports of KGW and SynthID-Text are not token-level compatible
with the watermark authors' reference implementations. The complete set of
differences is narrow and is enumerated here so that each declared variant is
reproducible from this file alone.

KGW SelfHash
    Both implementations compute the same anchored min-hash PRF,
    ``min(hash_key * hashint(ngram) * hashint(ngram[-1]))``. They differ in the
    seed of the global permutation table behind ``hashint``: the authors fix that
    seed at 2971215073 (``alternative_prf_schemes.py``), while Transformers
    derives it from ``hashing_key``.

    They also differ on the generation path. The authors' self-salt rejection
    sampling uses ``tail_rule="fixed_compute"`` and breaks *after* processing
    index 40, so it considers 41 candidates; Transformers loops ``range(40)`` and
    considers 40. This is observable whenever a tie at the top-k boundary lets a
    41st candidate through with a finite score, in which case the authors bias it
    by ``delta`` and Transformers does not. Detection is unaffected: the detector
    never runs rejection sampling.

SynthID-Text
    Both implementations accumulate the same linear congruential hash over the
    n-gram and the watermarking keys. They differ in two places. The reference
    seeds every hash with an initialisation vector derived from SHA-256 of the
    keys, where Transformers seeds with a literal one; and the reference derives
    g-values by iterating the hash and reading bit 30, where Transformers indexes
    a pre-computed random 0/1 sampling table.

Selecting a variant chooses generation and detection together: the returned
configuration objects build the matching processor on both paths.
"""

from __future__ import annotations

import hashlib
from typing import Any

from .native import require_ml_dependencies

KGW_AUTHOR_VARIANT = "kgw_author_selfhash_v1"
KGW_TRANSFORMERS_VARIANT = "kgw_transformers_selfhash_v5_16"
SYNTHID_DEEPMIND_VARIANT = "synthid_deepmind_hash_v1"
SYNTHID_TRANSFORMERS_VARIANT = "synthid_transformers_table_v5_16"

KGW_VARIANTS = (KGW_AUTHOR_VARIANT, KGW_TRANSFORMERS_VARIANT)
SYNTHID_VARIANTS = (SYNTHID_DEEPMIND_VARIANT, SYNTHID_TRANSFORMERS_VARIANT)

KGW_AUTHOR_TABLE_SEED = 2971215073
KGW_TABLE_SIZE = 1_000_003

SYNTHID_NUM_APPLY_HASH = 12
SYNTHID_GVALUE_BIT = 30

# The authors' "fixed_compute" tail rule breaks after this index, inclusive.
KGW_AUTHOR_REJECTION_TAIL_INDEX = 40

# Settings a variant accepts for schema compatibility but does not read. The
# canonical SynthID variant derives g-values by iterating the hash, so the
# sampling table is never consulted and changing these fields changes nothing.
INERT_SETTINGS: dict[str, tuple[str, ...]] = {
    KGW_AUTHOR_VARIANT: (),
    KGW_TRANSFORMERS_VARIANT: (),
    SYNTHID_DEEPMIND_VARIANT: ("sampling_table_seed", "sampling_table_size"),
    SYNTHID_TRANSFORMERS_VARIANT: (),
}

_CLASSES: dict[str, Any] | None = None


def author_kgw_fixed_table(device: Any) -> Any:
    """Build the authors' fixed permutation table used by ``hashint``."""

    torch, _ = require_ml_dependencies()
    generator = torch.Generator(device=device).manual_seed(KGW_AUTHOR_TABLE_SEED)
    return torch.randperm(KGW_TABLE_SIZE, generator=generator, device=device)


def apply_author_kgw_table(processor: Any) -> Any:
    """Replace a Transformers KGW processor's key-derived table with the authors'."""

    if processor.table_size != KGW_TABLE_SIZE:
        raise ValueError(
            f"Unexpected KGW table size {processor.table_size}; "
            f"the authors' hashint assumes {KGW_TABLE_SIZE}"
        )
    processor.fixed_table = author_kgw_fixed_table(processor.fixed_table.device)
    return processor


def synthid_hash_iv(keys: Any) -> int:
    """Derive the reference initialisation vector from the watermarking keys."""

    torch, _ = require_ml_dependencies()
    digest = hashlib.sha256(keys.detach().cpu().to(torch.long).numpy().tobytes()).digest()
    return int.from_bytes(digest, byteorder="big") % torch.iinfo(torch.int64).max


def inert_settings(variant: str) -> tuple[str, ...]:
    """Name the configuration fields a variant accepts but never reads."""

    if variant not in INERT_SETTINGS:
        raise ValueError(f"Unknown variant {variant!r}")
    return INERT_SETTINGS[variant]


def canonical_classes() -> dict[str, Any]:
    """Build the canonical configuration and processor classes on first use."""

    global _CLASSES
    if _CLASSES is None:
        _CLASSES = _build_classes()
    return _CLASSES


def build_kgw_config(settings: dict[str, Any], variant: str) -> Any:
    """Build the KGW watermarking configuration for a declared variant."""

    _, transformers = require_ml_dependencies()
    if variant == KGW_TRANSFORMERS_VARIANT:
        return transformers.WatermarkingConfig(**settings)
    if variant == KGW_AUTHOR_VARIANT:
        return canonical_classes()["AuthorKGWWatermarkingConfig"](**settings)
    raise ValueError(f"Unknown KGW variant {variant!r}; expected one of {list(KGW_VARIANTS)}")


def build_synthid_config(settings: dict[str, Any], variant: str) -> Any:
    """Build the SynthID-Text watermarking configuration for a declared variant."""

    _, transformers = require_ml_dependencies()
    if variant == SYNTHID_TRANSFORMERS_VARIANT:
        return transformers.SynthIDTextWatermarkingConfig(**settings)
    if variant == SYNTHID_DEEPMIND_VARIANT:
        return canonical_classes()["DeepMindSynthIDWatermarkingConfig"](**settings)
    raise ValueError(
        f"Unknown SynthID variant {variant!r}; expected one of {list(SYNTHID_VARIANTS)}"
    )


def kgw_variant_of(config: Any) -> str:
    """Recover the declared variant from a KGW configuration object."""

    author = canonical_classes()["AuthorKGWWatermarkingConfig"]
    return KGW_AUTHOR_VARIANT if isinstance(config, author) else KGW_TRANSFORMERS_VARIANT


def synthid_variant_of(config: Any) -> str:
    """Recover the declared variant from a SynthID-Text configuration object."""

    deepmind = canonical_classes()["DeepMindSynthIDWatermarkingConfig"]
    return (
        SYNTHID_DEEPMIND_VARIANT
        if isinstance(config, deepmind)
        else SYNTHID_TRANSFORMERS_VARIANT
    )


def _build_classes() -> dict[str, Any]:
    torch, transformers = require_ml_dependencies()
    from transformers.generation.logits_process import (
        SynthIDTextWatermarkLogitsProcessor,
        SynthIDTextWatermarkState,
    )

    class AuthorKGWLogitsProcessor(transformers.WatermarkLogitsProcessor):
        """KGW processor reproducing the authors' self-salt rejection sampling."""

        def _score_rejection_sampling(self, input_seq: Any, scores: Any) -> Any:
            _, greedy_predictions = scores.sort(dim=-1, descending=True)
            final_greenlist = []
            for index, candidate in enumerate(greedy_predictions):
                greenlist_ids = self._get_greenlist_ids(
                    torch.cat([input_seq, candidate[None]], dim=-1)
                )
                if candidate in greenlist_ids:
                    final_greenlist.append(candidate)
                if index == KGW_AUTHOR_REJECTION_TAIL_INDEX:
                    break
            return torch.tensor(final_greenlist, device=input_seq.device)

    class AuthorKGWWatermarkingConfig(transformers.WatermarkingConfig):
        """KGW configuration matching the authors' repository on both paths."""

        def construct_processor(self, vocab_size: int, device: Any) -> Any:
            processor = AuthorKGWLogitsProcessor(
                vocab_size=vocab_size,
                device=device,
                greenlist_ratio=self.greenlist_ratio,
                bias=self.bias,
                hashing_key=self.hashing_key,
                seeding_scheme=self.seeding_scheme,
                context_width=self.context_width,
            )
            return apply_author_kgw_table(processor)

    class DeepMindSynthIDLogitsProcessor(SynthIDTextWatermarkLogitsProcessor):
        """SynthID-Text processor using the reference IV and iterative-hash g-values."""

        def __init__(self, **kwargs: Any) -> None:
            super().__init__(**kwargs)
            self.hash_iv = synthid_hash_iv(self.keys)

        def _seed_hash(self, batch_size: int) -> Any:
            return torch.full(
                (batch_size,), self.hash_iv, dtype=torch.long, device=self.device
            )

        def compute_ngram_keys(self, ngrams: Any) -> Any:
            if len(ngrams.shape) != 3:
                raise ValueError(
                    "Ngrams should be of shape (batch_size, num_ngrams, ngram_len),"
                    f" but is {ngrams.shape}"
                )
            if ngrams.shape[2] != self.ngram_len:
                raise ValueError(
                    "Ngrams should be of shape (batch_size, num_ngrams, ngram_len),"
                    f" where ngram_len is {self.ngram_len}, but is {ngrams.shape}"
                )
            batch_size, _, _ = ngrams.shape
            hash_result = torch.vmap(self.accumulate_hash, in_dims=(None, 1), out_dims=1)(
                self._seed_hash(batch_size), ngrams
            )
            keys = self.keys[None, None, :, None]
            return torch.vmap(self.accumulate_hash, in_dims=(None, 2), out_dims=2)(
                hash_result, keys
            )

        def _compute_keys(self, n_minus_1_grams: Any, indices: Any) -> tuple[Any, Any]:
            batch_size, _ = n_minus_1_grams.shape
            hash_result_with_just_context = self.accumulate_hash(
                self._seed_hash(batch_size), n_minus_1_grams
            )
            hash_result = torch.vmap(self.accumulate_hash, in_dims=(None, 1), out_dims=1)(
                hash_result_with_just_context, indices[:, :, None]
            )
            keys = self.keys[None, None, :, None]
            hash_result = torch.vmap(self.accumulate_hash, in_dims=(None, 2), out_dims=2)(
                hash_result, keys
            )
            return hash_result, hash_result_with_just_context

        def compute_context_repetition_mask(self, input_ids: Any) -> Any:
            self._check_input_ids_shape(input_ids)
            batch_size, _ = input_ids.shape
            state = SynthIDTextWatermarkState(
                batch_size=batch_size,
                ngram_len=self.ngram_len,
                context_history_size=self.context_history_size,
                device=self.device,
            )
            contexts = input_ids[:, :-1].unfold(dimension=1, size=self.ngram_len - 1, step=1)
            _, num_contexts, _ = contexts.shape
            are_repeated_contexts = []
            for index in range(num_contexts):
                context = contexts[:, index, :]
                context_hash = self.accumulate_hash(self._seed_hash(batch_size), context)[:, None]
                is_repeated_context = (state.context_history == context_hash).any(
                    dim=1, keepdim=True
                )
                are_repeated_contexts.append(is_repeated_context)
                state.context_history = torch.concat(
                    (context_hash, state.context_history), dim=1
                )[:, :-1]
            return torch.logical_not(torch.concat(are_repeated_contexts, dim=1))

        def sample_g_values(self, ngram_keys: Any) -> Any:
            """Derive g-values by iterating the hash, as the reference does."""

            shift = 64 // SYNTHID_NUM_APPLY_HASH
            increment = torch.ones(1, dtype=torch.long, device=ngram_keys.device)
            for _ in range(SYNTHID_NUM_APPLY_HASH):
                ngram_keys = self.accumulate_hash(ngram_keys, increment) >> shift
            return (ngram_keys >> SYNTHID_GVALUE_BIT) % 2

    class DeepMindSynthIDWatermarkingConfig(transformers.SynthIDTextWatermarkingConfig):
        """SynthID-Text configuration that builds the reference-hashing processor."""

        def construct_processor(self, vocab_size: int, device: Any) -> Any:
            return DeepMindSynthIDLogitsProcessor(
                ngram_len=self.ngram_len,
                keys=self.keys,
                sampling_table_size=self.sampling_table_size,
                sampling_table_seed=self.sampling_table_seed,
                context_history_size=self.context_history_size,
                device=device,
                skip_first_ngram_calls=self.skip_first_ngram_calls,
                debug_mode=self.debug_mode,
            )

    return {
        "AuthorKGWLogitsProcessor": AuthorKGWLogitsProcessor,
        "AuthorKGWWatermarkingConfig": AuthorKGWWatermarkingConfig,
        "DeepMindSynthIDLogitsProcessor": DeepMindSynthIDLogitsProcessor,
        "DeepMindSynthIDWatermarkingConfig": DeepMindSynthIDWatermarkingConfig,
    }
