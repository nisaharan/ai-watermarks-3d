# Technical Execution Plan

## 1. Target repository architecture

```text
src/ai_watermarks/
  watermarks/
  generation/
  attacks/
  detectors/
  metrics/
  evaluation/
  reporting/
configs/
  generation/
  watermarks/
  attacks/
  evaluation/
data/
  README.md
  raw/
  interim/
  processed/
experiments/
notebooks/
tests/
docs/
figures/
paper/
```

Large or restricted datasets and model artifacts should not be committed directly.
The repository should instead store manifests, checksums, licenses, and retrieval or
generation instructions.

## 2. Pipeline design

The research pipeline should be configuration-driven:

```text
prompts and human controls
        -> matched generation
        -> watermark validation
        -> automated attacks
        -> context and quality measurement
        -> watermark and detector scoring
        -> statistical analysis
        -> tables, figures, and reports
```

Each artifact must retain identifiers linking it to:

- dataset and split;
- prompt or source document;
- model and revision;
- watermark scheme and keyed configuration;
- decoding parameters;
- attack configuration and seed;
- detector and metric versions;
- code commit and environment lock.

Secrets and watermark keys must be stored outside tracked files. Public releases
should include safe evaluation keys only when the release design permits it.

## 3. Configuration and experiment control

- Use human-readable YAML or TOML configurations.
- Give every run a unique immutable identifier.
- Save the fully resolved configuration with every result.
- Separate development and frozen evaluation configurations.
- Make random seeds explicit at every stochastic stage.
- Record failures and exclusions rather than silently dropping rows.

## 4. Testing strategy

### Unit tests

- Tokenization and context extraction.
- Watermark generation and detection arithmetic.
- Context-survival calculation at different context widths.
- Candidate-length handling.
- Attack transformations and invariants.
- Metric edge cases and serialization.

### Property and statistical tests

- Null-score distribution.
- Padding, truncation, and replacement behaviour.
- Detection strengthening with additional genuinely watermarked evidence.
- Detection weakening under controlled context destruction.
- Repeated-run determinism.

### Integration tests

- A small end-to-end experiment using lightweight models.
- Configuration validation.
- Dataset manifest verification.
- Figure and table regeneration from stored results.

## 5. Reproducibility standards

- Pin dependencies and model revisions.
- Provide CPU-friendly smoke tests and documented GPU experiments.
- Record hardware, runtime, and approximate cost.
- Use cached immutable intermediate artifacts where licensing allows.
- Produce machine-readable results before creating narrative tables.
- Generate paper tables and figures directly from validated result files.

## 6. Data contracts

Every experimental row should minimally contain:

```text
sample_id
source_id
split
register
topic
human_or_machine
model_id
decoding_config_id
watermark_scheme
watermark_config_id
attack_family
attack_config_id
seed
source_length
candidate_length
surviving_context_count
watermark_score
detector_scores
quality_scores
exclusion_status
```

The exact schema should be versioned before large-scale generation begins.

## 7. Quality controls

- Linting, formatting, type checking, and continuous integration.
- Code review for all detector and metric implementations.
- Independent verification of the watermark statistic.
- Checksums for datasets and final result tables.
- Automated detection of missing, duplicate, or inconsistent experimental rows.
- A release checklist covering code, data, documentation, figures, and claims.

## 8. Minimum reproducible release

An external researcher should be able to:

1. install the package;
2. run a lightweight keyed generation experiment;
3. apply at least two attacks;
4. measure context survival and watermark detection;
5. reproduce one primary figure;
6. verify the configuration and provenance of every output.
