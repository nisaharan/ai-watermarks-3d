# Phase 2 publication tables

Generated deterministically from reviewed artifacts. The partial joint-KGW Stage A run is excluded.

## Table 1. Study sequence and evidential role

| Stage | Sample | Role | Outcome |
|---|---:|---|---|
| SmolLM2 multi-key null pilot | 500 outputs | Development | Maximum nominal 1% KGW cell FPR at 512 tokens: 47.0% |
| Qwen2.5 replication | 104 outputs | Independent targeted replication | Maximum nominal 1% KGW cell FPR at 512 tokens: 41.3% |
| Confirmatory calibration | 5,000 outputs | Threshold fitting only | Thresholds frozen once |
| Confirmatory confirmation | 5,000 disjoint outputs | One-shot validation | 42/60 cells passed; global gate failed |
| Positive-sensitivity screen | 1000 outputs | Development | 55/60 cells passed |
| KGW bias brackets | 1,400 outputs | Development | No tested bias passed all detection and quality guardrails |
| Joint-KGW Stage A | 1935/5200 outputs | Abandoned unevaluated run | No outcome claim |

## Table 2. One-shot confirmation outcome by scheme

| Scheme | Passed | Failed | Total |
|---|---:|---:|---:|
| KGW | 16 | 14 | 30 |
| SynthID | 26 | 4 | 30 |

## Table 3. Failed confirmation cells by scheme and prefix length

| Scheme | Prefix length | Passed | Failed | Total |
|---|---:|---:|---:|---:|
| KGW | 128 | 6 | 4 | 10 |
| KGW | 256 | 4 | 6 | 10 |
| KGW | 512 | 6 | 4 | 10 |
| SynthID | 128 | 9 | 1 | 10 |
| SynthID | 256 | 9 | 1 | 10 |
| SynthID | 512 | 8 | 2 | 10 |

## Table 4. Calibration versus confirmation exceedance counts

| Scheme | Split | Mean exceedances per cell | Maximum passing count |
|---|---|---:|---:|
| KGW | Calibration | 27.90 | 28 |
| KGW | Confirmation | 27.70 | 28 |
| SynthID | Calibration | 18.17 | 28 |
| SynthID | Confirmation | 18.90 | 28 |

## Table 5. Positive-sensitivity screen by scheme and length

| Scheme | Prefix length | Minimum | Median | Maximum |
|---|---:|---:|---:|---:|
| KGW | 128 | 62.0% | 82.0% | 86.0% |
| KGW | 256 | 76.0% | 92.0% | 96.0% |
| KGW | 512 | 86.0% | 92.0% | 100.0% |
| SynthID | 128 | 86.0% | 95.0% | 98.0% |
| SynthID | 256 | 96.0% | 98.0% | 100.0% |
| SynthID | 512 | 96.0% | 99.0% | 100.0% |

## Interpretation notes

- The largest observed failed-cell confirmation rate was 0.96%; the largest simultaneous exact upper bound was 1.48%.
- A failed simultaneous confidence cell does not establish that its true false-positive rate exceeds 1%.
- Pilot maxima must always be reported with the named model, key, prefix length, nominal threshold, and development status.
- Development sensitivity and bias screens are not independent confirmation.
- The partial joint-KGW Stage A scores were not analysed and must not appear in a results table or figure.

## Machine-readable sources

- `reports/phase2-validation/artifact.json`
- `reports/phase2-confirmation-gate/artifact.json`
- `reports/phase2-positive-sensitivity/artifact.json`
- `results/phase2-v2-kgw-bias-development-v3/analysis.json`
- `results/phase2-v2-kgw-joint-feasibility/study-closure.json`
