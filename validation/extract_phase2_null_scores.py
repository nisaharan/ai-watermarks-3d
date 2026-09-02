"""Extract compact null detector scores from the Phase 2 confirmatory-null batches.

Reads every calibration and confirmation batch under
``results/phase2-confirmatory-null/`` and writes two CSV files under
``results/phase2-nominal-fpr/``:

* ``null-scores.csv``   one row per (output, prefix length, scheme, key)
* ``null-texts.csv``    one row per output with repetition statistics

Nothing is fitted here. Both splits are unwatermarked null text scored at fixed
detector keys, so they are pooled for nominal-threshold analysis; the ``split``
column is kept so any analysis can separate them again.

Standard library only. Run from the repository root:

    python validation/extract_phase2_null_scores.py [--limit N]
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "results", "phase2-confirmatory-null")
OUT = os.path.join(ROOT, "results", "phase2-nominal-fpr")

SCORE_FIELDS = [
    "prompt_id", "split", "category", "length", "scheme", "variant", "key_id",
    "statistic", "value", "eligible_positions", "green_tokens", "g_value_sum",
    "watermarking_depth",
]
TEXT_FIELDS = [
    "prompt_id", "split", "category", "generated_tokens", "n_tokens",
    "distinct_tokens", "distinct_bigrams", "repeated_4gram_fraction",
    "top20_token_share", "newline_fraction", "max_run_length",
]


def text_stats(ids: list[int]) -> dict:
    n = len(ids)
    grams = [tuple(ids[i:i + 4]) for i in range(max(0, n - 3))]
    rep4 = 1.0 - len(set(grams)) / len(grams) if grams else 0.0
    cnt = Counter(ids)
    top20 = sum(v for _, v in cnt.most_common(20)) / n if n else 0.0
    bigrams = {tuple(ids[i:i + 2]) for i in range(max(0, n - 1))}
    # longest run of an identical token
    best = run = 1
    for a, b in zip(ids, ids[1:]):
        run = run + 1 if a == b else 1
        best = max(best, run)
    return {
        "n_tokens": n,
        "distinct_tokens": len(cnt),
        "distinct_bigrams": len(bigrams),
        "repeated_4gram_fraction": round(rep4, 6),
        "top20_token_share": round(top20, 6),
        "newline_fraction": round(cnt.get(198, 0) / n, 6) if n else 0.0,
        "max_run_length": best,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="batches per split (debug)")
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)

    n_scores = n_texts = 0
    with open(os.path.join(OUT, "null-scores.csv"), "w", newline="") as fs, \
            open(os.path.join(OUT, "null-texts.csv"), "w", newline="") as ft:
        ws = csv.DictWriter(fs, fieldnames=SCORE_FIELDS)
        wt = csv.DictWriter(ft, fieldnames=TEXT_FIELDS)
        ws.writeheader()
        wt.writeheader()
        for split in ("calibration", "confirmation"):
            files = sorted(glob.glob(os.path.join(SRC, split, "batches", "batch-*.json")))
            if args.limit:
                files = files[: args.limit]
            for f in files:
                with open(f) as fh:
                    batch = json.load(fh)
                for rec in batch["records"]:
                    ids = rec["token_ids"]
                    if isinstance(ids, str):
                        ids = json.loads(ids)
                    base = {"prompt_id": rec["prompt_id"], "split": split,
                            "category": rec["category"]}
                    wt.writerow({**base, "generated_tokens": rec["generated_tokens"],
                                 **text_stats(ids)})
                    n_texts += 1
                    for pr in rec["prefix_results"]:
                        for s in pr["scores"]:
                            ws.writerow({
                                **base,
                                "length": pr["length"],
                                "scheme": s["scheme"],
                                "variant": s["variant"],
                                "key_id": s["key_id"],
                                "statistic": s["statistic_name"],
                                "value": s["value"],
                                "eligible_positions": s.get("eligible_positions"),
                                "green_tokens": s.get("green_tokens"),
                                "g_value_sum": s.get("g_value_sum"),
                                "watermarking_depth": s.get("watermarking_depth"),
                            })
                            n_scores += 1
            print(f"{split}: {len(files)} batches", file=sys.stderr)
    print(f"wrote {n_texts} texts, {n_scores} score rows to {OUT}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
