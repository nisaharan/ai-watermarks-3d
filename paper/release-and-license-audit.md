# Phase 2 release and licence audit

Audit date: 2 September 2026  
Status: paper/tables/figures releasable after editorial review; raw-data release requires a bounded attribution check

This is an engineering publication audit, not legal advice.

## Verified source terms

| Material | Pinned source | Recorded licence | Intended release treatment |
|---|---|---|---|
| Repository software | Local `LICENSE` | MIT | Release source and validation scripts with existing copyright/licence |
| Repository prose | Local `LICENSE-DOCS` | CC BY-SA 4.0 | Keep attribution and share-alike notice; verify compatibility with the target venue's publication agreement |
| KGW reference code | `jwkirchenbauer/lm-watermarking` @ `8292251…` | Apache-2.0 | Do not vendor; cite repository and retain pinned file hashes |
| SynthID-Text reference code | `google-deepmind/synthid-text` @ `addb4a1…` | Apache-2.0 software; CC BY 4.0 other materials | Do not vendor; cite repository and maintained paper |
| SmolLM2-135M-Instruct | `HuggingFaceTB/SmolLM2-135M-Instruct` @ `12fd25f…` | Apache-2.0 | Do not redistribute weights; provide model ID and immutable revision |
| Qwen2.5-0.5B-Instruct | `Qwen/Qwen2.5-0.5B-Instruct` @ `7ae5576…` | Apache-2.0 | Do not redistribute weights; provide model ID and immutable revision |
| Databricks Dolly 15k | `databricks/databricks-dolly-15k` @ `bdd27f4…` | CC BY-SA 3.0 | Prefer row IDs, hashes, selection code, and retrieval instructions; include Databricks/Wikipedia attribution if prompts are redistributed |
| UltraChat 200k | `HuggingFaceH4/ultrachat_200k` @ `8049631…` | MIT | Provide source/revision and selection manifests; disclose model-generated-dialogue provenance |

Licence labels were checked against the pinned/local records and current official
repository or model-card pages. `NOTICE.md` now records the Phase 2 dependencies.

## Safe first release

Release immediately after claim review:

- manuscript, deterministic tables, static figures, and figure captions;
- source code, tests, frozen configurations, key schedule definition, and hashes;
- compact aggregate artifacts used by the publication reports;
- prompt row identifiers, normalized prompt hashes, selection rules, and retrieval
  instructions;
- parity fixtures and compact/native audit outputs that contain no restricted raw
  source text;
- a machine-readable inventory of included files and SHA-256 values.

## Hold pending one bounded review

- Raw Dolly prompts or excerpts: confirm CC BY-SA 3.0 attribution and share-alike
  placement in the release package.
- Raw UltraChat prompts: confirm that the dataset-card MIT notice accompanies any
  redistributed subset and disclose synthetic provenance.
- Full generated continuations: inspect for memorized personal, copyrighted, or
  unsafe content before public release.
- Model weights and cached datasets: exclude; require deterministic retrieval from
  the pinned upstream sources.
- The partial joint-KGW Stage A batches: preserve privately for audit and do not
  publish with the result package because they are unevaluated and unnecessary for
  reproducing any reported claim.

## Remaining release blockers

1. Select the target venue and check whether its publication agreement is
   compatible with the repository's CC BY-SA 4.0 documentation licence.
2. Create a bounded public-artifact manifest that excludes caches, weights, raw
   partial Stage A batches, and source texts not cleared for redistribution.
3. Add citation metadata for SmolLM2, Qwen2.5, Dolly, UltraChat, KGW, SynthID-Text,
   and the software libraries used for exact intervals and generation.
4. Inspect a sample of generated text before any raw-output release.
5. Add an ethics/responsible-use statement: detector output is not proof of
   authorship, misconduct, truth, or intent.

