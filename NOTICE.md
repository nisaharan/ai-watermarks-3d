# Third-party material

Everything this repository borrows, and under what terms.

## Vendored code

**`vendor/watermarks_remover/text_unicode.py`**
Copyright (c) 2026 watermarks-remover contributors — MIT.
Source: [guillaumemeyer/watermarks-remover](https://github.com/guillaumemeyer/watermarks-remover),
`service/scripts/text_unicode.py`, unmodified.
Full licence text: `vendor/watermarks_remover/LICENSE`.

This is Layer A of that project — the deterministic Unicode strip. It is
vendored verbatim rather than reimplemented so that Part 10 of the analysis is
testing the actual tool and not my paraphrase of it. The Layer B prompts from
`service/scripts/rewrite_text.py` are quoted in Part 10 for the same reason.

## Text under CC BY-SA 4.0

**`example/human_wikipedia.txt`**
An extract from the opening section of the English Wikipedia article
[Sydney Opera House](https://en.wikipedia.org/wiki/Sydney_Opera_House),
by Wikipedia contributors, licensed
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
Retrieved August 2026. Reproduced here as the human-written half of a matched
pair; it is quoted, measured and displayed but not modified.

**`Wikipedia:Signs of AI writing`**
The Tier 3 catalogue implemented in `surface_tells.py` follows the categories
and example phrases in
[Wikipedia:Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing),
by Wikipedia contributors, CC BY-SA 4.0. The regexes are my own; the taxonomy
and its category names are theirs.

Because this repository's prose is derived from CC BY-SA material, that prose is
CC BY-SA 4.0 too. See `LICENSE-DOCS`.

## Cited, not included

**Wayne Pan, *How to Remove Claude Watermarks From Content You Own*** (12 Aug 2026).
Referenced throughout `AI-Watermarks-3D.md` as a source. The article itself is
the author's copyright and is deliberately **not** redistributed here — it is
listed in `.gitignore`. Read it at the author's own publication.

**Kirchenbauer, Geiping, Wen, Katz, Miers & Goldstein**, *A Watermark for Large
Language Models*, ICML 2023. The green-list/red-list scheme and z-score detector
reproduced in Part 2 and modelled in Part 10. No code taken; the arithmetic is
implemented from the paper's description.

**GPT-2 (`gpt2-large`)**, OpenAI, via
[Hugging Face Transformers](https://huggingface.co/openai-community/gpt2-large) —
used as the reference model for per-word surprisal in `measure_texts.py`. Model
weights are downloaded at runtime, not vendored.

## Text written for this repository

**`example/ai_generated.txt`** and everything under `example/removal/` were
generated or rewritten for this project and carry no third-party claim. Their
provenance is documented in Parts 8 and 10 — in particular, the four Layer B
rewrites were produced by prompting a language model with the upstream tool's
verbatim prompts, and are not the output of the upstream tool's own pipeline.
