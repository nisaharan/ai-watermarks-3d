#!/usr/bin/env python3
"""Scan text for the surface tells catalogued in Wikipedia's "Signs of AI writing".

https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing

These are Tier 3 in the project's own taxonomy: habits, not measurements. They
are the easiest signals for a reader to check and the easiest for a writer to
edit away, and — importantly — they fire on human prose too. The scanner is
deliberately conservative and only uses patterns the guide names explicitly, so
that a hit can always be traced back to a line on that page.

Run it directly to print the tally for the two example texts.
"""
import re
import sys

# Sentence-initial, without swallowing the previous sentence's full stop.
SENT = r"(?:(?<=\.\s)|(?<=\n)|(?<=^))"

# (category, plain-English gloss, [(label, regex), ...])
# Category names follow the Wikipedia guide's own section headings.
TELLS = [
    ("Undue emphasis on significance",
     "puffing a fact up into a milestone or a symbol",
     [("stands as", r"\bstands? as\b"),
      ("remains a testament", r"\b(remains?|is|stood) a testament\b"),
      ("a lasting/powerful symbol", r"\b(lasting|powerful|enduring|potent) symbol\b"),
      ("plays a vital role", r"\bplays? a (vital|key|crucial|significant|pivotal|central) role\b"),
      ("marking a milestone", r"\bmarking a (major |significant |key )?(milestone|moment|turning point|shift)\b"),
      ("represents a ...", r"\brepresents a (lasting|significant|major|profound)\b"),
      ("cemented its place", r"\bcement(ed|ing|s)? (its|his|her|their) (place|status|legacy)\b")]),

    ("Superficial -ing analysis",
     "a clause bolted onto the end that restates rather than adds",
     [("..., marking ...", r",\s+marking\b"),
      ("..., highlighting ...", r",\s+highlight(ing|s)\b"),
      ("..., underscoring ...", r",\s+underscor(ing|es)\b"),
      ("..., emphasising ...", r",\s+emphasi[sz](ing|es)\b"),
      ("..., reflecting ...", r",\s+reflect(ing|s)\b"),
      ("..., showcasing ...", r",\s+showcas(ing|es)\b"),
      ("..., contributing to ...", r",\s+contribut(ing|es) to\b"),
      ("which contribute to", r"\bwhich contribute[sd]? to\b"),
      ("..., ensuring ...", r",\s+ensur(ing|es)\b"),
      ("..., covering ...", r",\s+cover(ing|s)\b"),
      ("..., facing ...", r",\s+fac(ing|es)\b")]),

    ("Avoidance of basic copulatives",
     "reaching for “serves as” where “is” would do",
     [("serves as", r"\bserves? as\b"),
      ("is home to", r"\bis home to\b"),
      ("continues to serve/be", r"\bcontinues? to (serve|be|stand)\b"),
      ("boasts", r"\bboasts?\b"),
      ("features (as a verb)", r"\b(it|which|that) features\b")]),

    ("Promotional language",
     "brochure adjectives standing in for facts",
     [("remarkable", r"\bremarkable\b"),
      ("rich and varied", r"\brich and (varied|diverse|vibrant)\b"),
      ("vibrant", r"\bvibrant\b"),
      ("outstanding", r"\boutstanding\b"),
      ("innovative", r"\binnovativ\w*\b"),
      ("ambitious", r"\bambitious\b"),
      ("every corner of the globe", r"\bevery corner of the (globe|world)\b"),
      ("world-class / leading", r"\b(world-class|a leading)\b"),
      ("breathtaking / stunning", r"\b(breathtaking|stunning|iconic)\b")]),

    ("Vague attribution",
     "“widely regarded”, “experts say” — by whom?",
     [("widely regarded/considered", r"\bwidely (regarded|considered|seen|recognised|recognized)\b"),
      ("experts say/argue", r"\bexperts? (say|argue|believe|note)\b"),
      ("studies show", r"\bstudies (show|suggest|indicate)\b"),
      ("industry reports", r"\bindustry (reports?|observers?)\b"),
      ("it is said/believed", r"\bit is (said|believed|thought)\b")]),

    ("Negative parallelism",
     "“not just X, but Y” and its relatives",
     [("not only ... but also", r"\bnot only\b.{0,80}?\bbut (also|equally)\b"),
      ("it is not X, it is Y", r"\b(is|it's|its) not (just |merely |simply )?\w+.{0,40}?[,;]\s*(it|but) (is|it's)\b"),
      ("rather than", r"\b(prioritis|prioritiz|choos|opt)\w*\b.{0,40}?\brather than\b")]),

    ("Rule of three",
     "three-item lists used as a default rhythm",
     [("adj, adj, and adj", r"\b\w+ly?,\s+\w+,\s+and\s+\w+\b")]),

    ("Section-final summary",
     "a closing sentence that only restates the paragraph",
     [("As a result, ...", SENT + r"As a result,"),
      ("Today, ...", SENT + r"Today,"),
      ("Overall, ...", SENT + r"Overall,"),
      ("In conclusion, ...", SENT + r"In (conclusion|summary),"),
      ("It remains ...", SENT + r"It remains\b")]),
]


def scan(text):
    """Return {category: [(label, matched phrase, start, end), ...]}.

    Overlapping matches inside a category are collapsed, so that a phrase like
    "represents a lasting symbol" counts once rather than twice.
    """
    found = {}
    for cat, _gloss, pats in TELLS:
        raw = []
        for label, rx in pats:
            for m in re.finditer(rx, text, flags=re.IGNORECASE | re.MULTILINE):
                s, e = m.start(), m.end()
                while s < e and not text[s].isalnum():   # patterns anchored on a
                    s += 1                               # comma shouldn't claim
                raw.append((label, text[s:e], s, e))     # the word before it
        hits, taken = [], []
        for h in sorted(raw, key=lambda h: (h[2], -(h[3] - h[2]))):
            if any(h[2] < e and s < h[3] for s, e in taken):
                continue
            hits.append(h)
            taken.append((h[2], h[3]))
        found[cat] = hits
    return found


def paragraph_shape(text):
    """Sentences per paragraph — the guide's 'outline-like' structure tell,
    reduced to something countable."""
    paras = [p.strip() for p in text.split("\n") if p.strip()]
    return [len(re.findall(r"[.!?](?:\s|$)", p)) for p in paras]


GLOSS = {cat: gloss for cat, gloss, _ in TELLS}
CATEGORIES = [cat for cat, _, _ in TELLS]


if __name__ == "__main__":
    import os
    base = os.path.dirname(os.path.abspath(__file__))
    texts = {
        "human": open(os.path.join(base, "example/human_wikipedia.txt")).read(),
        "ai": open(os.path.join(base, "example/ai_generated.txt")).read(),
    }
    for name, t in texts.items():
        f = scan(t)
        total = sum(len(v) for v in f.values())
        print(f"\n=== {name}  ({total} hits, paragraphs {paragraph_shape(t)}) ===")
        for cat in CATEGORIES:
            hits = f[cat]
            mark = "·" if not hits else "→"
            print(f" {mark} {cat:34s} {len(hits)}"
                  + ("   " + "; ".join(f"“{h[1]}”" for h in hits) if hits else ""))
