# Human-text null tables (generated; v1 plan Table 2)

Source: `validation/analyse_phase2_human_null.py`. Human rows: de-duplicated
Databricks Dolly `response` and `context` fields (human-written), scored with the
same ten frozen canonical KGW SelfHash keys as the model null; each text is scored
at every prefix length it supports, so n falls with length. Model rows: 10,000
unwatermarked SmolLM2-135M-Instruct outputs. FPR is the empirical rate at the
nominal one-sided 1% threshold (z > 2.326) with exact two-sided 95% Clopper-Pearson
intervals; p_k is the pooled null green-token rate for the key (gamma = 0.25).


## 128 tokens (human n = 5,000; model n = 10,000)

| Key | Human FPR | Model FPR | Human p_k | Model p_k |
|---|---:|---:|---:|---:|
| kgw-00 | 2.64% [2.21, 3.12] | 6.23% [5.76, 6.72] | 0.255 | 0.266 |
| kgw-01 | 0.66% [0.45, 0.93] | 0.75% [0.59, 0.94] | 0.237 | 0.228 |
| kgw-02 | 0.90% [0.66, 1.20] | 0.99% [0.81, 1.20] | 0.237 | 0.230 |
| kgw-03 | 0.48% [0.31, 0.71] | 0.32% [0.22, 0.45] | 0.217 | 0.206 |
| kgw-04 | 0.20% [0.10, 0.37] | 0.66% [0.51, 0.84] | 0.219 | 0.218 |
| kgw-05 | 3.56% [3.06, 4.11] | 4.80% [4.39, 5.24] | 0.261 | 0.261 |
| kgw-06 | 1.42% [1.11, 1.79] | 2.18% [1.90, 2.49] | 0.245 | 0.248 |
| kgw-07 | 9.42% [8.62, 10.26] | 19.08% [18.31, 19.86] | 0.282 | 0.301 |
| kgw-08 | 6.22% [5.57, 6.93] | 7.28% [6.78, 7.81] | 0.269 | 0.269 |
| kgw-09 | 2.88% [2.43, 3.38] | 6.44% [5.97, 6.94] | 0.259 | 0.268 |

## 256 tokens (human n = 1,951; model n = 10,000)

| Key | Human FPR | Model FPR | Human p_k | Model p_k |
|---|---:|---:|---:|---:|
| kgw-00 | 2.72% [2.04, 3.54] | 8.87% [8.32, 9.44] | 0.252 | 0.265 |
| kgw-01 | 0.46% [0.21, 0.87] | 0.70% [0.55, 0.88] | 0.237 | 0.228 |
| kgw-02 | 0.92% [0.55, 1.45] | 1.19% [0.99, 1.42] | 0.238 | 0.230 |
| kgw-03 | 0.87% [0.51, 1.39] | 0.26% [0.17, 0.38] | 0.217 | 0.206 |
| kgw-04 | 0.15% [0.03, 0.45] | 0.80% [0.63, 0.99] | 0.219 | 0.218 |
| kgw-05 | 5.43% [4.47, 6.53] | 7.17% [6.67, 7.69] | 0.261 | 0.260 |
| kgw-06 | 0.97% [0.59, 1.52] | 2.78% [2.47, 3.12] | 0.245 | 0.248 |
| kgw-07 | 16.40% [14.78, 18.12] | 33.02% [32.10, 33.95] | 0.282 | 0.302 |
| kgw-08 | 9.23% [7.98, 10.60] | 9.65% [9.08, 10.25] | 0.269 | 0.268 |
| kgw-09 | 4.77% [3.86, 5.81] | 9.30% [8.74, 9.89] | 0.258 | 0.267 |

## 512 tokens (human n = 554; model n = 10,000)

| Key | Human FPR | Model FPR | Human p_k | Model p_k |
|---|---:|---:|---:|---:|
| kgw-00 | 2.71% [1.52, 4.43] | 12.49% [11.85, 13.15] | 0.248 | 0.265 |
| kgw-01 | 0.54% [0.11, 1.57] | 0.80% [0.63, 0.99] | 0.235 | 0.227 |
| kgw-02 | 1.44% [0.63, 2.83] | 1.28% [1.07, 1.52] | 0.238 | 0.229 |
| kgw-03 | 1.26% [0.51, 2.59] | 0.27% [0.18, 0.39] | 0.216 | 0.205 |
| kgw-04 | 0.72% [0.20, 1.84] | 0.88% [0.71, 1.08] | 0.219 | 0.218 |
| kgw-05 | 7.22% [5.21, 9.70] | 10.19% [9.60, 10.80] | 0.261 | 0.261 |
| kgw-06 | 1.81% [0.87, 3.29] | 3.69% [3.33, 4.08] | 0.244 | 0.249 |
| kgw-07 | 25.45% [21.87, 29.29] | 48.36% [47.38, 49.34] | 0.280 | 0.302 |
| kgw-08 | 14.62% [11.78, 17.84] | 12.74% [12.09, 13.41] | 0.268 | 0.267 |
| kgw-09 | 6.86% [4.90, 9.29] | 13.66% [12.99, 14.35] | 0.257 | 0.268 |

Key-level agreement at 512 tokens: Spearman rho = +0.94 (p = 5.5e-05), Pearson r = +0.96 over ten keys. Worst key on human text: kgw-07; on model text: kgw-07.
