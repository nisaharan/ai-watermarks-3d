# Phase 2 Multi-key Null-variance and Replication Report

Status: validated no-go for the attack corpus pending confirmatory calibration  
Updated: 30 August 2026

## Decision

Do not open the full attack corpus yet. Keep the canonical watermark code unchanged,
calibrate KGW conditionally on the detector key, model family and length bin, and
use held-out confirmation data before freezing thresholds. SynthID may retain a
pooled-across-tested-keys development calibration, but it also requires held-out
confirmation.

This is a calibration-policy failure, not an implementation-parity failure.

## Evidence completed

- Primary null pilot: 500 SmolLM2-135M-Instruct outputs, paired 128/256/512-token
  prefixes, ten KGW keys and ten SynthID key vectors; 30,000 validated score rows.
- Independent replication: 104 Qwen2.5-0.5B-Instruct outputs, balanced at 13 per
  Dolly task category, with the same paired lengths and frozen keys; 6,240
  validated score rows.
- Clean environment: the replication design tests and the Qwen generation/scoring
  run executed from a lockfile-derived `uv --isolated --frozen --extra ml`
  environment.
- Both runs passed completeness, category allocation, prefix-shape, score-cell
  uniqueness, finite-score, exact score-reconstruction and native-trace parity
  checks.

## Main findings

| Finding at 512 tokens | SmolLM2, n=500 | Qwen2.5, n=104 |
|---|---:|---:|
| KGW key-mean range | −1.978 to +2.273 z | −0.690 to +2.146 z |
| KGW nominal 1% FPR range by key | 0.2% to 47.0% | 1.0% to 41.3% |
| KGW pooled empirical 1% cutoff: per-key FPR range | 0.0% to 7.2% | 0.0% to 4.8% |
| SynthID key-mean range | 0.49862 to 0.50067 | 0.49875 to 0.50054 |
| SynthID pooled empirical 1% cutoff: per-key FPR range | 0.2% to 1.8% | 0.0% to 1.9% |

KGW key offsets increase with evaluated sequence length in both model families.
The standard-normal KGW threshold therefore does not control false-positive risk
for an individual key, and pooling keys still leaves material per-key distortion.
SynthID remains tightly centred and materially more key-stable.

The ten key scores on each text are paired observations, not independent null
texts. The pooled cutoffs above are development diagnostics and must not be
treated as confirmatory thresholds.

## Precision and power decision

For a primary 1% FPR with an approximate 30% relative 95% half-width, plan two
disjoint sets of 5,000 independent null texts per primary cell: one calibration
set and one untouched confirmation set. A primary 0.1%
FPR would require roughly 43,000 null texts per cell and is not the current
priority. The 500-sample development cell has only five expected 1% exceedances;
its Wilson 95% interval is approximately 0.43% to 2.32%.

The 104-prompt replication exceeds the n=88 planning benchmark for 80% power to
detect a standardized mean shift of 0.3, but it is not sized to estimate a 1% tail.
Attack-condition power remains provisional until repeated watermarked-positive
and attacked-positive variances are observed.

## Ordered next steps

1. Freeze disjoint 5,000-prompt calibration and 5,000-prompt confirmation manifests.
2. Generate the 10,000 primary-model null outputs; score every frozen KGW key and
   the pooled SynthID key schedule at 128/256/512.
3. Freeze detector-key × model × length-bin KGW thresholds on the calibration
   split, then verify realised FPR on the untouched confirmation split.
4. If calibration and confirmation gates pass, run a small repeated positive
   variance pilot and finalise attack-condition sample sizes.
5. Only then open the full attack corpus.

## Reproducible artifacts

- Executed notebook: `notebooks/phase2-variance-pilot.ipynb`
- Primary result and analysis: `results/phase2-variance-pilot/`
- Independent result and analysis: `results/phase2-variance-replication/`
- Frozen primary design: `configs/phase2-variance-pilot.json`
- Frozen replication design: `configs/phase2-variance-replication.json`
- Analysis program: `validation/analyse_phase2_variance.py`

Machine-generated result directories are ignored by Git; the frozen configs,
manifests, analysis code, notebook and this report preserve the audit path.
