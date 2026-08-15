#!/usr/bin/env python3
"""Measure what guillaumemeyer/watermarks-remover actually does to the AI text.

Variants measured, all against the same source text (`example/ai_generated.txt`):

  human       the Wikipedia article — the reference for "what human looks like"
  ai          the untouched AI text
  layerA      the tool's deterministic Unicode strip, run verbatim from the
              vendored `vendor/watermarks_remover/text_unicode.py`
  paraphrase     Layer B at --strength paraphrase
  humanize       Layer B at --strength humanize
  backtranslate  Layer B at --strength backtranslate, English -> French -> English
                 (French is the repo's default --lang). The pivot text is kept
                 alongside as ai_backtranslate_fr_pivot.txt.
  structural     Layer B at --strength structural: outline the claims, then write
                 the document from the outline. The outline is kept alongside as
                 ai_structural_outline.txt.

Layer B ships no model: `rewrite_text.py` emits a prompt and you supply the
rewriter. The two rewrites here were produced by running the repo's verbatim
prompts, so they are *a* result of the tool's method, not *the* result — a
different rewriter gives different numbers. Stated again in the output.

Needs torch + transformers for the surprisal columns. Everything else is
model-free; pass --no-surprisal to skip them.

Writes example/removal/analysis.json.
"""
import argparse
import json
import math
import os
import re
import statistics
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE, "vendor/watermarks_remover"))

from surface_tells import scan, paragraph_shape, CATEGORIES   # noqa: E402

VARIANTS = [
    ("human",      "example/human_wikipedia.txt",       "reference: the Wikipedia article"),
    ("ai",         "example/ai_generated.txt",          "untouched AI text"),
    ("layerA",     "example/removal/ai_layerA.txt",     "Layer A — Unicode strip"),
    ("paraphrase", "example/removal/ai_paraphrase.txt", "Layer B — paraphrase"),
    ("humanize",   "example/removal/ai_humanize.txt",   "Layer B — humanize"),
    ("backtranslate", "example/removal/ai_backtranslate.txt",
     "Layer B — backtranslate (French pivot)"),
    ("structural", "example/removal/ai_structural.txt",  "Layer B — structural"),
]

# The published green-list numbers this project uses throughout (Part 2).
GAMMA = 0.5          # green-list fraction
P_MARKED = 0.72      # green rate of watermarked text
Z_THRESHOLD = 4.0    # "chance cannot explain this"


# ------------------------------------------------------------------ helpers
def tokens(text):
    """Word tokens, lowercased — the repo's own tokenisation in rewrite_text.py."""
    return re.findall(r"[A-Za-z0-9]+", text.lower())


def bigrams(toks):
    return set(zip(toks, toks[1:]))


def lexical_divergence(original, candidate):
    """Bigram Jaccard distance — copied from the repo's `_lexical_divergence`,
    which is the score it uses to pick between rewrite candidates.
    0.0 identical, 1.0 fully different."""
    a, b = tokens(original), tokens(candidate)
    if not a and not b:
        return 0.0
    if not a or not b:
        return 1.0
    ba, bb = bigrams(a), bigrams(b)
    union = ba | bb
    return 0.0 if not union else 1.0 - len(ba & bb) / len(union)


def bigram_survival(original, candidate):
    """Fraction of the ORIGINAL text's bigrams still present in the candidate.

    This, not Jaccard, is the quantity the watermark cares about. A token only
    carries green-list evidence while the token before it is unchanged, because
    the preceding token is what seeds that position's green list. Added text
    dilutes the score but does not destroy evidence, so recall is the right
    measure here and Jaccard (which penalises additions) is not.
    """
    ba = bigrams(tokens(original))
    if not ba:
        return 1.0
    return len(ba & bigrams(tokens(candidate))) / len(ba)


def modelled_z(survival, n_tokens):
    """[Modelled, not measured] Detection z-score after editing.

    Surviving bigrams keep the watermarked green rate; destroyed ones fall back
    to chance, so p = P_MARKED·s + γ·(1−s) and z = (p−γ)·√n / √(γ(1−γ)).
    We do not hold the vendor's key, so this can never be a measurement — it is
    the published scheme's arithmetic applied to a measured survival rate.
    """
    p = P_MARKED * survival + GAMMA * (1 - survival)
    return (p - GAMMA) * math.sqrt(n_tokens) / math.sqrt(GAMMA * (1 - GAMMA))


def fact_vocabulary(text):
    """Numbers and proper nouns in the reference text.

    A crude but automatic stand-in for the "preserve all facts, numbers, names"
    clause in the tool's own prompts. Sentence-initial capitals are skipped when
    *building* the vocabulary, since every sentence has one and most are
    ordinary words.
    """
    out = set(re.findall(r"\b\d[\d,]*\b", text))
    for sent in sentences(text):
        for w in re.findall(r"\b[A-Z][A-Za-zøéèü'-]+\b", sent)[1:]:
            out.add(w)
    return out


def facts_retained(vocab, candidate):
    """Which reference facts appear anywhere in the candidate.

    Presence is checked at any sentence position — a rewrite that moves "UNESCO"
    to the front of a sentence has not lost it, and scoring the candidate with
    the sentence-initial rule above would wrongly say it had.
    """
    kept = {w for w in vocab if re.search(rf"\b{re.escape(w)}\b", candidate)}
    return kept, sorted(vocab - kept)


def sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]


def model_free_stats(text):
    sents = sentences(text)
    slen = [len(s.split()) for s in sents]
    toks = tokens(text)
    puncts = set(re.findall(r"[,;:—–()\-\"'?!]", text))
    found = scan(text)
    return {
        "n_words": len(text.split()),
        "n_sents": len(sents),
        "sent_lens": slen,
        "sent_mean": statistics.mean(slen),
        "sent_sd": statistics.pstdev(slen),
        "sent_cv": statistics.pstdev(slen) / statistics.mean(slen),
        "sent_max": max(slen),
        "ttr": len(set(toks)) / len(toks),
        "punct_variety": len(puncts),
        "paragraph_shape": paragraph_shape(text),
        "tells_total": sum(len(v) for v in found.values()),
        "tells_by_cat": {c: len(found[c]) for c in CATEGORIES},
        "tell_phrases": {c: [h[1] for h in found[c]] for c in CATEGORIES if found[c]},
    }


# --------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-surprisal", action="store_true",
                    help="skip the GPT-2 columns (no torch needed)")
    args = ap.parse_args()

    texts = {name: open(os.path.join(BASE, path), encoding="utf-8").read().strip()
             for name, path, _ in VARIANTS}
    ref = texts["ai"]
    ref_vocab = fact_vocabulary(ref)

    dest = os.path.join(BASE, "example/removal/analysis.json")
    prev = {}
    if os.path.exists(dest):
        prev = json.load(open(dest)).get("variants", {})

    word_surprisal = None
    if not args.no_surprisal:
        from measure_texts import word_surprisal

    out = {"note": "Layer B rewrites follow the repo's verbatim prompts but were "
                   "produced by a different rewriter than the repo would invoke; "
                   "z-scores are modelled from the published scheme, not measured.",
           "params": {"gamma": GAMMA, "p_marked": P_MARKED, "z_threshold": Z_THRESHOLD},
           "variants": {}}

    for name, _path, label in VARIANTS:
        t = texts[name]
        rec = {"label": label, "chars": len(t)}
        rec.update(model_free_stats(t))

        rec["identical_to_ai"] = (t == ref)
        kept, lost = facts_retained(ref_vocab, t)
        rec["facts_retained"] = len(kept) / len(ref_vocab)
        rec["facts_lost"] = lost
        rec["divergence_jaccard"] = lexical_divergence(ref, t)
        s = bigram_survival(ref, t)
        rec["bigram_survival"] = s
        rec["modelled_z"] = modelled_z(s, len(tokens(t)))
        rec["modelled_z_detected"] = rec["modelled_z"] >= Z_THRESHOLD

        if word_surprisal is not None:
            bits = [b for _, b in word_surprisal(t)]
            rec["mean_bits"] = statistics.mean(bits)
            rec["sd_bits"] = statistics.pstdev(bits)
            rec["median_bits"] = statistics.median(bits)
        else:
            # --no-surprisal must not silently delete columns a previous run
            # measured — GIF 12 reads them, and rerunning costs a GPT-2 load.
            for k in ("mean_bits", "sd_bits", "median_bits"):
                if k in prev.get(name, {}):
                    rec[k] = prev[name][k]

        out["variants"][name] = rec

    os.makedirs(os.path.dirname(dest), exist_ok=True)
    json.dump(out, open(dest, "w"), indent=1)

    hdr = (f"{'variant':11s} {'words':>5s} {'sents':>5s} {'CV':>5s} {'TTR':>6s} "
           f"{'tells':>5s} {'paras':>14s} {'diverg':>7s} {'surv':>6s} {'z':>6s} "
           f"{'facts':>6s} {'bits':>6s} {'sd':>5s}")
    print(hdr)
    print("-" * len(hdr))
    for name, _p, _l in VARIANTS:
        r = out["variants"][name]
        print(f"{name:11s} {r['n_words']:5d} {r['n_sents']:5d} {r['sent_cv']:5.2f} "
              f"{r['ttr']:6.3f} {r['tells_total']:5d} "
              f"{str(r['paragraph_shape']):>14s} "
              f"{r['divergence_jaccard']:7.3f} {r['bigram_survival']:6.3f} "
              f"{r['modelled_z']:6.2f} {r['facts_retained']:6.1%} "
              + (f"{r['mean_bits']:6.2f} {r['sd_bits']:5.2f}" if "mean_bits" in r else "     -     -"))
    print(f"\nz threshold {Z_THRESHOLD} — detected: "
          + ", ".join(n for n, _p, _l in VARIANTS
                      if n != "human" and out["variants"][n]["modelled_z_detected"]))
    print("-> example/removal/analysis.json")


if __name__ == "__main__":
    main()
