# The laundered text scored more human than the human

I spent a week building tools to spot machine-written text. Then I tried to disguise some, and broke my own test.

Here is what happened.

I placed two short articles side by side. Both describe the Sydney Opera House. Both run to about 350 words. Volunteers wrote one of them on Wikipedia. A chatbot wrote the other.

<!-- GIF 06_sentence_skyline.gif -->
*Each tower is one sentence, and its height is the word count. Wikipedia on the left.*

Before touching any statistics, I counted the words in each sentence.

Wikipedia lurches. Sixteen, then twenty-seven, then forty-three, and somewhere in the middle a monster of fifty-nine. The bot never went below ten or above twenty-four.

Then I counted sentences per paragraph instead. Wikipedia went 2, 3, 1, 4, 2. The bot went 4, 4, 4, 4, 4.

Five paragraphs. Four sentences in each. Nobody writes that way by accident, and spotting it took no software at all.

## Then I tried to remove the fingerprint

Some AI vendors now stamp a hidden signature into whatever their systems produce. It lives in the vocabulary, spread thinly across a whole passage, so no individual word gives anything away.

Tools exist to strip it out. I ran a popular one.

Its first stage scrubs invisible characters. It changed nothing whatsoever. Not one character. You cannot scrub a signature out of the letters when the signature lives in the word choices, yet this is precisely the step people run before declaring themselves clean.

Its second stage asks a different model to rewrite your text, and offers four ways to do it. Translating into French and back preserved almost three quarters of the original wording, which made it the feeblest of the four, despite being the trick most of us reach for first.

Two of those four rewrites would still be caught.

## The part that broke my test

<!-- GIF 12_convergence.gif -->
*The orange mark is the real Wikipedia article. Watch the dots sail past it.*

Rewriting does make text look more human. Then it keeps going.

The heaviest rewrite finished more uneven in rhythm than the Wikipedia article, and its word choices were harder to predict. On the exact measurements that AI detectors run, it scored as more human than writing by actual humans.

None of these numbers has a ceiling marked "person". A detector that flags you for being too predictable will happily clear you for being wildly unpredictable, and it cannot separate an overcooked rewrite from a distinctive writer.

That failure already has casualties. These tools are documented as scoring second-language writers as machine-like, because careful non-native prose genuinely is more predictable.

## Why this matters at work

If your organisation is weighing detection software for academic integrity, hiring or compliance, ask what the percentage actually measures.

It measures sentence rhythm and word rarity. Someone determined to cheat adjusts both in a single editing pass. Someone honest may fail both on the day they write with unusual care.

The hidden signature answers a much narrower question: did this vendor's system touch this text? It cannot tell you who thought of the ideas, because asking a model to tidy three of your own sentences can stamp the output.

The most dependable signal I found in a week of work needed no software.

Read the thing. Count the sentences in each paragraph. If it runs 4, 4, 4, 4, 4, you already know.

---

*Full write-up, code and twelve annotated visualisations: [github.com/nisaharan/ai-watermarks-3d](https://github.com/nisaharan/ai-watermarks-3d)*

*Caveat worth stating: one matched pair of texts is one matched pair. Treat the direction of each effect as the finding and the size of it as a single sample.*
