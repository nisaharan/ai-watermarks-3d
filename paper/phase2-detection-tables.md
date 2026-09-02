# Detection-rate trade-off of per-key calibration (generated)

Source: `validation/analyse_phase2_detection_tradeoff.py`. Watermarked outputs
are the 1,000-output development positive screen, which shares the model, the
watermark configuration and the key schedule with the confirmatory null, so the
frozen thresholds apply unchanged. Thresholds were fitted on unwatermarked text
only. Detection rate is the fraction of watermarked outputs scoring above the
threshold under their own key, n = 50 per cell, with exact two-sided 95%
Clopper-Pearson intervals. Development scale, not a confirmatory detection claim.


## 128 tokens

| Key | Nominal z | Calibrated z | FPR nominal | FPR calibrated | TPR nominal | TPR calibrated [95% CI] |
|---|---:|---:|---:|---:|---:|---:|
| kgw-00 | 2.33 | 3.86 | 6.23% | 0.54% | 100% | 92% [81, 98] |
| kgw-01 | 2.33 | 2.43 | 0.75% | 0.56% | 92% | 90% [78, 97] |
| kgw-02 | 2.33 | 2.74 | 0.99% | 0.28% | 98% | 94% [83, 99] |
| kgw-03 | 2.33 | 1.93 | 0.32% | 0.64% | 78% | 86% [73, 94] |
| kgw-04 | 2.33 | 2.44 | 0.66% | 0.48% | 90% | 88% [76, 95] |
| kgw-05 | 2.33 | 3.70 | 4.80% | 0.68% | 94% | 88% [76, 95] |
| kgw-06 | 2.33 | 2.97 | 2.18% | 0.64% | 96% | 88% [76, 95] |
| kgw-07 | 2.33 | 4.85 | 19.08% | 0.46% | 96% | 86% [73, 94] |
| kgw-08 | 2.33 | 4.31 | 7.28% | 0.54% | 96% | 76% [62, 87] |
| kgw-09 | 2.33 | 3.78 | 6.44% | 0.58% | 98% | 90% [78, 97] |

## 256 tokens

| Key | Nominal z | Calibrated z | FPR nominal | FPR calibrated | TPR nominal | TPR calibrated [95% CI] |
|---|---:|---:|---:|---:|---:|---:|
| kgw-00 | 2.33 | 4.36 | 8.87% | 0.54% | 100% | 100% [93, 100] |
| kgw-01 | 2.33 | 2.65 | 0.70% | 0.34% | 94% | 94% [83, 99] |
| kgw-02 | 2.33 | 3.06 | 1.19% | 0.34% | 100% | 98% [89, 100] |
| kgw-03 | 2.33 | 1.75 | 0.26% | 0.68% | 92% | 98% [89, 100] |
| kgw-04 | 2.33 | 2.54 | 0.80% | 0.70% | 96% | 94% [83, 99] |
| kgw-05 | 2.33 | 4.14 | 7.17% | 0.68% | 96% | 96% [86, 100] |
| kgw-06 | 2.33 | 3.10 | 2.78% | 0.74% | 100% | 96% [86, 100] |
| kgw-07 | 2.33 | 5.66 | 33.02% | 0.32% | 98% | 94% [83, 99] |
| kgw-08 | 2.33 | 4.93 | 9.65% | 0.60% | 100% | 90% [78, 97] |
| kgw-09 | 2.33 | 4.27 | 9.30% | 0.62% | 98% | 94% [83, 99] |

## 512 tokens

| Key | Nominal z | Calibrated z | FPR nominal | FPR calibrated | TPR nominal | TPR calibrated [95% CI] |
|---|---:|---:|---:|---:|---:|---:|
| kgw-00 | 2.33 | 5.02 | 12.49% | 0.52% | 100% | 100% [93, 100] |
| kgw-01 | 2.33 | 2.71 | 0.80% | 0.38% | 100% | 100% [93, 100] |
| kgw-02 | 2.33 | 3.06 | 1.28% | 0.48% | 100% | 100% [93, 100] |
| kgw-03 | 2.33 | 1.49 | 0.27% | 0.96% | 96% | 98% [89, 100] |
| kgw-04 | 2.33 | 3.25 | 0.88% | 0.24% | 98% | 94% [83, 99] |
| kgw-05 | 2.33 | 4.87 | 10.19% | 0.68% | 98% | 96% [86, 100] |
| kgw-06 | 2.33 | 3.32 | 3.69% | 0.78% | 100% | 100% [93, 100] |
| kgw-07 | 2.33 | 6.40 | 48.36% | 0.54% | 98% | 96% [86, 100] |
| kgw-08 | 2.33 | 5.62 | 12.74% | 0.48% | 100% | 92% [81, 98] |
| kgw-09 | 2.33 | 4.80 | 13.66% | 0.60% | 98% | 94% [83, 99] |
