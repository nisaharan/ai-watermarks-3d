# LinkedIn feed post

Roughly 290 words, which is the range that reads as a practitioner sharing a
result rather than a brand publishing content. LinkedIn hides everything past
about 200 characters behind "see more", so the first two lines carry the click.

Attach one GIF on its own. A GIF placed in a multi-image post stops animating,
so a single moving image beats a moving image plus stills.

Put the link in the first comment. An outbound link in the body costs reach.

**Attach:** `gifs/06_sentence_skyline.gif`

---

## Main version, 288 words

> Spent the weekend trying to strip the watermark out of AI-generated text. Ended up breaking my own detector instead.
>
> Setup: the Wikipedia intro for the Sydney Opera House against a chatbot's version of the same subject. Same topic, same length, ~350 words each.
>
> The strongest signal turned out not to be statistical at all. I counted sentences per paragraph.
>
> Wikipedia: 2, 3, 1, 4, 2
> Chatbot: 4, 4, 4, 4, 4
>
> Five paragraphs, four sentences in each. For comparison, GPT-2 perplexity barely separated them: 4.15 vs 3.61 bits per word, where the textbook diagrams promise a cliff.
>
> Then I pointed a watermark remover at it.
>
> Layer one strips invisible Unicode. It changed 0 characters out of 2,087. Obvious in hindsight, since you cannot scrub a signature out of the bytes when it is encoded in token choice.
>
> Layer two is a prompt you plug your own model into. I ran all four modes and tracked bigram survival as a proxy for surviving watermark evidence. Backtranslation through French kept 73% of the original word pairs, which models out to z ≈ 5.8, comfortably above a threshold of 4. Only the modes that effectively rewrote the document from scratch landed under it.
>
> The part I did not expect:
>
> The heaviest rewrite overshot. Sentence-length CV of 0.73 against Wikipedia's 0.42. Perplexity of 5.18 bits against 4.15. On the exact features public detectors threshold on, laundered machine text scored more human than the human.
>
> None of these metrics has a ceiling labelled "person". Which is presumably related to why they misfire on second-language writers.
>
> n=1 pair, so directional rather than conclusive. Code and 12 annotated visualisations in the comments.

---

## Shorter cut, 176 words

Same voice, drops the removal-tool mechanics and keeps the reversal.

> Spent the weekend trying to strip the watermark out of AI-generated text. Ended up breaking my own detector instead.
>
> Setup: Wikipedia's Sydney Opera House intro against a chatbot's version of the same subject, same length, ~350 words each.
>
> The clearest signal was not statistical. Sentences per paragraph:
>
> Wikipedia: 2, 3, 1, 4, 2
> Chatbot: 4, 4, 4, 4, 4
>
> GPT-2 perplexity barely separated them by comparison, 4.15 against 3.61 bits per word.
>
> Then I rewrote the machine text hard enough to evade detection, and checked the result.
>
> Sentence-length CV came out at 0.73 against Wikipedia's 0.42. Perplexity at 5.18 against 4.15. On the exact features public detectors threshold on, the laundered text scored more human than the human article.
>
> None of these metrics has a ceiling labelled "person". A detector that flags you for being too predictable will clear you for being wildly unpredictable, which is presumably related to why they misfire on second-language writers.
>
> n=1 pair, directional rather than conclusive. Code in the comments.

---

## First comment

> Write-up, code, and twelve annotated visualisations:
> github.com/nisaharan/ai-watermarks-3d
>
> Method notes: surprisal measured with gpt2-large, bigram survival as the proxy
> for watermark evidence, z modelled from the published green-list scheme rather
> than measured, since nobody outside the vendor holds the key. Rewrites came
> from the removal tool's own prompts run against a different model.

---

## Stills, if you skip the GIF

`article/stills/skyline.png` and `article/stills/convergence.png` are the final
frames of GIFs 06 and 12. Two stills form a carousel and stay sharp, trading the
motion for it.
