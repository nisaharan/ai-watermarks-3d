"""A6: score human-written text with the frozen KGW / SynthID detector keys.

Detector-only. No model weights are loaded and nothing is generated: the script
tokenizes human-written Databricks Dolly text with the pinned SmolLM2 tokenizer
and scores it with the same ten canonical KGW keys and ten SynthID key vectors
used for the model null (`configs/phase2-variance-pilot.json` key schedule).

Human text pool (both fields are human-written; prompts are never used):
    * ``response``  the human answer to each Dolly instruction
    * ``context``   the human-written reference passage, where present
Texts are de-duplicated after whitespace/case normalisation, must contain at
least 128 tokens, and are ranked by SHA-256 of a fixed seed so the selection is
deterministic. Each text is scored at every prefix length in {128, 256, 512}
that it can support, so cell sizes differ by length; the analysis reports n.

Output (same column layout as ``results/phase2-nominal-fpr/null-scores.csv``):
    results/phase2-human-null/human-scores.csv
    results/phase2-human-null/human-texts.csv
    results/phase2-human-null/run.json

Run on the Mac from the repository root (the detector code needs the ML extra):

    .venv/bin/python validation/score_phase2_human_null.py \
        --source /path/to/databricks-dolly-15k.jsonl --max-texts 5000

Omit --source to download the pinned revision with huggingface_hub.
Expected time: roughly the scoring half of the confirmatory run, i.e. well under
an hour for 5,000 texts on the M4 Pro.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ai_watermarks_phase2.native import require_ml_dependencies  # noqa: E402
from ai_watermarks_phase2.smoke import load_json  # noqa: E402
from ai_watermarks_phase2.variance_pilot import build_scorers  # noqa: E402

LENGTHS = (128, 256, 512)
SELECTION_SEED = "phase2-human-null-v1"
SCORE_FIELDS = [
    "prompt_id", "split", "category", "length", "scheme", "variant", "key_id",
    "statistic", "value", "eligible_positions", "green_tokens", "g_value_sum",
    "watermarking_depth",
]
TEXT_FIELDS = [
    "prompt_id", "split", "category", "source_row", "field", "n_tokens",
    "distinct_tokens", "repeated_4gram_fraction", "top20_token_share", "text_sha256",
]


def normalized(value: str) -> str:
    return " ".join(value.split()).casefold()


def text_stats(ids: list[int]) -> dict[str, Any]:
    n = len(ids)
    grams = [tuple(ids[i:i + 4]) for i in range(max(0, n - 3))]
    cnt = Counter(ids)
    return {
        "n_tokens": n,
        "distinct_tokens": len(cnt),
        "repeated_4gram_fraction": round(1 - len(set(grams)) / len(grams), 6) if grams else 0.0,
        "top20_token_share": round(sum(v for _, v in cnt.most_common(20)) / n, 6) if n else 0.0,
    }


def resolve_source(args: argparse.Namespace, protocol: dict[str, Any]) -> Path:
    if args.source:
        return args.source
    from huggingface_hub import hf_hub_download  # lazy: only needed without --source

    src = protocol["source"]
    return Path(hf_hub_download(repo_id=src["dataset"], filename=src["file"],
                                repo_type="dataset", revision=src["revision"]))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", type=Path, default=None)
    ap.add_argument("--protocol", type=Path, default=ROOT / "configs" / "phase2-confirmatory-null.json")
    ap.add_argument("--max-texts", type=int, default=5000)
    ap.add_argument("--output", type=Path, default=ROOT / "results" / "phase2-human-null")
    ap.add_argument("--device", default="cpu")
    args = ap.parse_args(argv)

    protocol = load_json(args.protocol)
    watermark_config = load_json(ROOT / protocol["watermark_config"])
    schedule_source = load_json(ROOT / protocol["key_schedule"]["source_config"])
    config = {"variants": watermark_config["variants"],
              "key_schedule": schedule_source["key_schedule"]}

    source_path = resolve_source(args, protocol)
    source_bytes = source_path.read_bytes()
    sha = hashlib.sha256(source_bytes).hexdigest()
    if sha != protocol["source"]["file_sha256"]:
        raise SystemExit(f"Dolly SHA-256 mismatch: {sha}")
    rows = [json.loads(line) for line in source_bytes.splitlines() if line.strip()]

    torch, transformers = require_ml_dependencies()
    model = protocol["model"]
    tokenizer = transformers.AutoTokenizer.from_pretrained(model["id"], revision=model["revision"])
    model_cfg = transformers.AutoConfig.from_pretrained(model["id"], revision=model["revision"])
    # build_scorers only needs vocab size, device and eos id: no weights are loaded
    stub_runner = SimpleNamespace(model=SimpleNamespace(config=model_cfg),
                                  device=args.device, tokenizer=tokenizer)
    kgw_scorers, synthid_scorers, _, _ = build_scorers(config, watermark_config, stub_runner)

    # candidate pool
    seen: set[str] = set()
    candidates: list[dict[str, Any]] = []
    for row_index, row in enumerate(rows):
        for field in ("response", "context"):
            text = str(row.get(field, "") or "").strip()
            if not text:
                continue
            key = normalized(text)
            if key in seen:
                continue
            seen.add(key)
            ids = tokenizer(text, add_special_tokens=False)["input_ids"]
            if len(ids) < LENGTHS[0]:
                continue
            rank = hashlib.sha256(f"{SELECTION_SEED}\0{row_index}\0{field}".encode()).hexdigest()
            candidates.append({"rank": rank, "source_row": row_index, "field": field,
                               "category": row.get("category", ""), "ids": ids,
                               "sha": hashlib.sha256(text.encode()).hexdigest()})
    candidates.sort(key=lambda c: c["rank"])
    selected = candidates[: args.max_texts]
    print(f"{len(candidates)} eligible human texts (>= {LENGTHS[0]} tokens); scoring {len(selected)}",
          file=sys.stderr)

    args.output.mkdir(parents=True, exist_ok=True)
    started = time.time()
    n_scores = 0
    with open(args.output / "human-scores.csv", "w", newline="") as fs, \
            open(args.output / "human-texts.csv", "w", newline="") as ft:
        ws = csv.DictWriter(fs, fieldnames=SCORE_FIELDS)
        wt = csv.DictWriter(ft, fieldnames=TEXT_FIELDS)
        ws.writeheader()
        wt.writeheader()
        for i, c in enumerate(selected):
            ids = c["ids"]
            lengths = [L for L in LENGTHS if L <= len(ids)]
            pid = f"human-{i:05d}"
            split = f"human_{c['field']}"
            wt.writerow({"prompt_id": pid, "split": split, "category": c["category"],
                         "source_row": c["source_row"], "field": c["field"],
                         **text_stats(ids), "text_sha256": c["sha"]})
            with torch.no_grad():
                per_scorer = [s.score_prefixes(ids[: lengths[-1]], lengths)
                              for s in (*kgw_scorers, *synthid_scorers)]
            for L in lengths:
                for res in per_scorer:
                    s = res[L]
                    ws.writerow({
                        "prompt_id": pid, "split": split, "category": c["category"],
                        "length": L, "scheme": s["scheme"], "variant": s["variant"],
                        "key_id": s["key_id"], "statistic": s["statistic_name"],
                        "value": s["value"], "eligible_positions": s.get("eligible_positions"),
                        "green_tokens": s.get("green_tokens"), "g_value_sum": s.get("g_value_sum"),
                        "watermarking_depth": s.get("watermarking_depth"),
                    })
                    n_scores += 1
            if (i + 1) % 200 == 0:
                el = time.time() - started
                print(f"  {i + 1}/{len(selected)}  {el / 60:.1f} min elapsed, "
                      f"~{el / (i + 1) * (len(selected) - i - 1) / 60:.1f} min left", file=sys.stderr)

    n_by_len = {L: sum(1 for c in selected if len(c["ids"]) >= L) for L in LENGTHS}
    run = {
        "schema_version": 1,
        "scope": "A6 human-text null: detector-only scoring of human-written Dolly text; not a generation run",
        "protocol": str(args.protocol.relative_to(ROOT)),
        "source": {**protocol["source"], "observed_sha256": sha},
        "tokenizer": model,
        "variants": config["variants"],
        "key_schedule_source": protocol["key_schedule"]["source_config"],
        "selection_seed": SELECTION_SEED,
        "fields": ["response", "context"],
        "eligible_candidates": len(candidates),
        "texts_scored": len(selected),
        "texts_by_min_length": n_by_len,
        "score_rows": n_scores,
        "elapsed_seconds": round(time.time() - started, 1),
    }
    (args.output / "run.json").write_text(json.dumps(run, indent=2))
    print(json.dumps(run, indent=2), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
