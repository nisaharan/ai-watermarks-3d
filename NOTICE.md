# Third-party material

Everything this repository borrows, and under what terms. Model weights and
datasets are not redistributed here; the revisions below are pinned so they can
be retrieved deterministically.

## Datasets

**databricks-dolly-15k** — Databricks, Inc. (2023), [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/).
Revision `bdd27f4d94b9c1f951818a7da7fd7aeea5dbff1a`, file SHA-256
`2df9083338b4abd6bceb5635764dab5d833b393b55759dffb0959b6fcbf794ec`.

Used two ways. Its instructions are the prompts for every unwatermarked
generation run. Its human-written `response` and `context` fields are the
human-text null in Section 4.4 of the paper. Share-alike is why this
repository's prose and derived tables are CC BY-SA 4.0 rather than MIT; see
`LICENSE-DOCS`. The prompt manifests under `data/` and the per-text tables under
`results/` are derived from this dataset. They carry row identifiers, token
statistics and a SHA-256 per text; they do not reproduce the text itself.

**UltraChat 200k** — MIT. Used only in a superseded development run that
supports no claim in the paper. Its provenance audit is retained at
`data/phase2-ultrachat-source-audit.json`.

## Models

Neither checkpoint is redistributed. Both are pinned by revision in the configs.

**HuggingFaceTB/SmolLM2-135M-Instruct** — Apache-2.0. Revision
`12fd25f77366fa6b3b4b768ec3050bf629380bac`. The primary null corpus.

**Qwen/Qwen2.5-0.5B-Instruct** — Apache-2.0. The independent replication.

## Reference implementations

The canonical adapters in `src/ai_watermarks_phase2/` reproduce two maintained
references exactly, and are validated against them for keyed token assignment,
aggregate score reconstruction and step-by-step generation. The schemes and
their reference code are the work of their authors, not of this project:

**KGW green-list watermarking and its SelfHash variant** — Kirchenbauer et al.,
*A Watermark for Large Language Models* (2023) and *On the Reliability of
Watermarks for Large Language Models* (2024).

**SynthID-Text** — Dathathri et al., *Scalable watermarking for identifying
large language model outputs*, Nature (2024). Apache-2.0 as distributed in the
DeepMind and Hugging Face Transformers implementations.

Where the maintained implementations differ from each other, the variants are
kept as separately named conditions and their scores are never pooled. The
remaining SynthID top-k boundary-tie difference is recorded as a decoder-policy
difference in `results/phase2-reference/`.

## Software

Built on PyTorch, Hugging Face Transformers, NumPy, SciPy, pandas and
Matplotlib, each under its own licence. Exact versions are pinned in `uv.lock`.
