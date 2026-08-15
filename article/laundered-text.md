# The laundered text scored more human than the human

I built a way to see AI writing. The final experiment undermined the premise.

The setup was simple. I took the opening of Wikipedia's article on the Sydney Opera House, about 350 words assembled by many hands over many years. Then I asked a language model for an encyclopedia-style overview of the same building at the same length. One subject, one length, one variable: authorship.

Both versions open with the same four words. *The Sydney Opera House.* After that they diverge.

<!-- GIF 06 -->

## Counting beats measuring

Before touching a neural network, try something you can do on paper. Count the words in each sentence.

Wikipedia lurches. Sixteen words, then twenty-seven, then forty-three. Later one sentence runs to fifty-nine. The machine produced twenty sentences and never left the band between ten and twenty-four.

Now count sentences per paragraph. Wikipedia gives you 2, 3, 1, 4, 2. There is a one-sentence paragraph in there, which writers use when a fact deserves to sit alone.

The machine gives you 4, 4, 4, 4, 4.

Five consecutive paragraphs of exactly four sentences is not an accident. That row of digits told me more than anything I later computed with GPT-2.

## What the model actually sees

Perplexity underpins most public detectors. Feed a language model some writing one word at a time, ask it to guess what comes next, and record how badly it loses. Odd choices score high. Predictable ones score near zero.

Folk wisdom says people surprise the model and machines do not. Teaching diagrams draw the first as a mountain range and the second as a flat lake.

On my pair, Wikipedia averaged 4.15 bits per word against the generated version's 3.61.

The difference is genuine. It is also 0.54 bits, where the diagram promised 3.4. Plot both surfaces side by side and they look like siblings. Anyone selling detection built on that number alone is overselling.

<!-- GIF 07 -->

A second result deserves attention. Type-token ratio measures how much vocabulary repeats. Theory holds that machines repeat themselves, so they ought to score lower. Wikipedia scored 0.548. The generated piece scored 0.574.

Backwards. An encyclopedia says *Sydney* and *the building* over and over, while the model kept reaching for fresh synonyms.

## Removing something that was never there

Watermarking is the other half of this story. When a vendor marks generated text, the mark rides in the choices themselves: a secret key nudges each successive pick toward half the dictionary, and detection counts how often the finished prose landed on the favoured half. No single word proves anything. The tally does.

Which raises an obvious question. What do the removal tools remove?

I ran one at my sample. The repository I picked splits into two parts. Part one strips invisible Unicode: zero-width spaces, bidirectional controls, tag characters, exotic whitespace. Part two hands the copy to a second generator for rewriting.

Part one changed nothing. Not almost nothing. Input and output were byte-identical across 2,087 characters, and the tool said so itself: *no deterministic carriers detected.* The only unusual glyph in my sample was the ø in Jørn Utzon, a Norwegian letter doing an honest job.

That result should be obvious in hindsight, yet it is exactly the step people run before declaring themselves clean. Scrubbing characters cannot touch a signal encoded in vocabulary.

<!-- GIF 11 -->

Part two ships no model. It emits a prompt and you supply the rewriter, which means efficacy depends entirely on what you plug in. Four prompts exist for ordinary writing. I ran all of them and measured how many of the original word pairs survived, because a marked term only carries evidence while its predecessor stays put.

Round-tripping through French preserved 73 percent. Paraphrasing preserved 56. Writing afresh from a bullet outline preserved 45. The most aggressive prompt preserved 34.

Translation, the trick most people reach for first, turned out weakest. Translators work sentence by sentence and hand back the same skeleton wearing different clothes. Variability went from 0.23 to 0.22, marginally tighter than before. Paragraph shape stayed at 4, 4, 4, 4, 4.

Two of the four rewrites remain above the detection threshold. Only the two that effectively rebuild the document fall below it, and at that point the honest description is no longer *removal*. Someone wrote a different article.

## The overshoot

Here is where my premise fell apart.

<!-- GIF 12 -->

Rewriting improves the style metrics. It improves them past the target.

Length variability in the heaviest rewrite reached 0.73, against Wikipedia's 0.42. Unpredictability reached 5.18 bits, against Wikipedia's 4.15. Vocabulary freshness drifted further from the encyclopedia with every prompt I applied.

Read that again. On the exact heuristics public detectors run, laundered machine prose now looks more human than an article humans wrote.

None of these quantities has a ceiling labelled *person*. A detector thresholding on burstiness or perplexity cannot separate authentic from overcooked, and the same overshoot that slips past it would flag any florid writer who happens to enjoy long sentences and rare words. That failure mode already has victims: such tools are documented as biased against people writing in a second language, whose prose is genuinely more predictable.

## What survives

One measurement resisted everything, and it needs no model at all.

Wikipedia editors maintain a catalogue called *Signs of AI writing*: inflated significance, promotional adjectives, vague attribution, trailing clauses that restate rather than add. I turned the prose half of that list into a scanner.

My generated sample tripped it 25 times. The Wikipedia article tripped it once.

Every rewrite reduced the count. The best reached six, still six times the encyclopedia. What clung on through all four attempts was the promotional vocabulary. *Rich and varied. Ambitious. Innovative. Outstanding. Every corner of the globe.* Those phrases survived translation into French and back, survived paraphrase, survived being rebuilt from an outline.

<!-- GIF 09 -->

Worth noting against my own tool: part of that improvement was fake. The French round trip converted *widely regarded* into *generally considered* and *as a result* into *therefore*. Identical habit, different string, no longer matched by my regular expression. A scanner counts phrasings, not habits, so treat its verdict as a floor.

## What I would tell you to conclude

Detection scores answer a narrow question. A cryptographic mark, when present and readable, tells you a system processed some text. It never tells you who composed the ideas, because asking a model to proofread three of your own sentences can mark the output.

Everything below that tier is style, and style is negotiable. My experiment moved every statistical indicator wherever I wanted within an afternoon, mostly overshooting the target by trying moderately hard.

So if your institution plans to discipline anyone on the strength of a percentage from a detector, understand what that percentage rests on. Rhythm of phrasing, and rarity of vocabulary. Quantities a determined student adjusts in a single editing pass, and that an unlucky honest one may fail on the day they write with unusual care.

The tell that lasted was not statistical. It was a habit list compiled by volunteer editors who read suspected machine drafts all day, and the strongest single signal in my entire investigation was five paragraphs of exactly four sentences.

Read the prose. Count the sentences. That still works.

---

*Code, data, and twelve annotated visualisations: [github.com/nisaharan/ai-watermarks-3d](https://github.com/nisaharan/ai-watermarks-3d)*

*One matched pair of texts is one matched pair. Treat the direction of each effect as the finding and the magnitude as a single sample. The rewrites came from prompting a model with the tool's own instructions rather than from the tool's pipeline, and no detection score here is a measurement, because nobody outside the vendor holds the key.*
