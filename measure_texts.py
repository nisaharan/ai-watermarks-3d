"""Measure per-word surprisal with GPT-2 for two real texts, dump JSON."""
import json, math, os, re, statistics
import torch
from transformers import GPT2LMHeadModel, GPT2TokenizerFast

MODEL = "gpt2-large"
_tok = _model = None


def _load():
    """Load lazily, so `from measure_texts import profile` costs nothing until used."""
    global _tok, _model
    if _model is None:
        _tok = GPT2TokenizerFast.from_pretrained(MODEL)
        _model = GPT2LMHeadModel.from_pretrained(MODEL).eval()
    return _tok, _model


def word_surprisal(text):
    """Return [(word, bits)] aggregating sub-token surprisal to whole words."""
    tok, model = _load()
    enc = tok(text, return_tensors="pt", return_offsets_mapping=True)
    ids = enc["input_ids"]
    offs = enc["offset_mapping"][0].tolist()
    with torch.no_grad():
        logits = model(ids).logits
    logprobs = torch.log_softmax(logits[0, :-1].float(), dim=-1)
    tgt = ids[0, 1:]
    bits = (-logprobs[torch.arange(len(tgt)), tgt] / math.log(2)).tolist()
    # token i>=1 has surprisal bits[i-1]; token 0 has no context
    pairs = [(offs[i], bits[i - 1]) for i in range(1, len(offs))]

    # group sub-tokens into words by whitespace boundaries in the source
    words, cur, cur_bits, cur_start = [], "", [], None
    for (s, e), b in pairs:
        piece = text[s:e]
        if piece.startswith(" ") or piece.startswith("\n") or cur == "":
            if cur.strip():
                words.append((cur.strip(), sum(cur_bits)))
            cur, cur_bits = piece, [b]
        else:
            cur += piece
            cur_bits.append(b)
    if cur.strip():
        words.append((cur.strip(), sum(cur_bits)))
    return words


def sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]


def profile(name, text):
    ws = word_surprisal(text)
    vals = [b for _, b in ws]
    sents = sentences(text)
    slen = [len(s.split()) for s in sents]
    toks = [w.lower().strip(".,;:()—–\"'") for w, _ in ws]
    toks = [t for t in toks if t]
    ttr = len(set(toks)) / len(toks)
    puncts = set(re.findall(r"[,;:—–()\-\"'?!]", text))
    return {
        "name": name,
        "n_words": len(ws),
        "words": [w for w, _ in ws],
        "bits": [round(b, 4) for _, b in ws],
        "mean_bits": statistics.mean(vals),
        "sd_bits": statistics.pstdev(vals),
        "median_bits": statistics.median(vals),
        "sent_lens": slen,
        "n_sents": len(sents),
        "sent_mean": statistics.mean(slen),
        "sent_sd": statistics.pstdev(slen),
        "sent_cv": statistics.pstdev(slen) / statistics.mean(slen),
        "ttr": ttr,
        "punct_variety": len(puncts),
        "sentences": sents,
    }


if __name__ == "__main__":
    BASE = os.path.dirname(os.path.abspath(__file__))
    EX = os.path.join(BASE, "example")

    human = profile("human", open(os.path.join(EX, "human_wikipedia.txt")).read())
    ai = profile("ai", open(os.path.join(EX, "ai_generated.txt")).read())
    json.dump({"human": human, "ai": ai},
              open(os.path.join(EX, "profiles.json"), "w"), indent=1)

    for p in (human, ai):
        print(f"{p['name']:6s} words={p['n_words']:4d} sents={p['n_sents']:3d} "
              f"surprisal mean={p['mean_bits']:5.2f} sd={p['sd_bits']:5.2f} med={p['median_bits']:5.2f} | "
              f"sent mean={p['sent_mean']:5.1f} sd={p['sent_sd']:4.1f} CV={p['sent_cv']:.2f} | "
              f"TTR={p['ttr']:.3f} punct={p['punct_variety']}")

    for p in (human, ai):
        top = sorted(zip(p["words"], p["bits"]), key=lambda x: -x[1])[:8]
        print(p["name"], "most surprising:", ", ".join(f"{w}({b:.0f})" for w, b in top))
