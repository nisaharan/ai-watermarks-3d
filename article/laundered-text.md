# The laundered text scored more human than the human

**I spent a week learning to spot machine writing. Then I tried to hide it, and broke my own test.**

Start with a game.

I put two short articles side by side. Both describe the Sydney Opera House. Both run to about 350 words. One was assembled by volunteers on Wikipedia over many years. The other came from a chatbot I asked for an encyclopedia entry.

Show them to a room and most people pick correctly. I wanted to know what the room was noticing.

## The picket fence

Forget algorithms for a minute. Count the words in each sentence.

Wikipedia jumps around. Sixteen words, then twenty-seven, then forty-three. Somewhere in the middle sits a monster of fifty-nine.

The bot never went below ten or above twenty-four. Not once, across twenty attempts.

<!-- GIF 06_sentence_skyline.gif -->
*Each tower is one sentence. Height is its word count. Wikipedia on the left, the machine on the right.*

Now count sentences per paragraph instead. Wikipedia goes 2, 3, 1, 4, 2. That lonely one-sentence paragraph is a very human move, the sort you make when a fact deserves the spotlight to itself.

The bot went 4, 4, 4, 4, 4.

Five paragraphs. Four sentences in each. Every single time.

Nobody does that by accident. Out of everything I measured that week, including some fairly heavy statistics, that little row of digits was the clearest signal I found.

## What the detectors are really doing

Tools that claim to catch AI text mostly watch two things, and both are simpler than the marketing suggests.

The first is predictability. Show a computer a passage one word at a time and ask it to guess what comes next. People choose odd words. Machines choose expected ones. Keep score.

The second is variety, which is the picket fence again. Machines find a comfortable rhythm and stay in it. People speed up, slow down, and now and then write a sentence that gets away from them.

Received wisdom says the predictability gap is enormous. Textbook diagrams draw human writing as a mountain range and machine writing as a still lake.

On my two samples that gap was tiny. Genuine, but tiny. About half a unit on a scale where the diagram had promised more than three.

One result nobody had warned me about: machines are supposed to repeat themselves more than people do. Mine did the reverse. The encyclopedia kept saying *Sydney* and *the building*, while the bot reached for a fresh synonym every chance it got.

## Then I tried to wipe the fingerprint

Some AI companies now stamp a hidden signature into whatever their systems write. It does not hide in invisible characters. It hides in the vocabulary itself, spread thinly across the whole passage, so no individual word betrays anything and only the overall pattern does.

Naturally, tools exist to strip it out. I picked a popular one and aimed it at my chatbot paragraph.

It comes in two parts.

Part one scrubs invisible characters. It ran, and it changed absolutely nothing. Not a single character moved. The tool said so itself.

Which makes sense the moment you think about it. You cannot scrub a signature out of the letters when the signature lives in the vocabulary. Scrubbing is nonetheless the exact step most of us run before announcing ourselves clean.

<!-- GIF 11_removal_ladder.gif -->
*Each row is one thing the removal tool can do. Red bars are still detectable. Green bars slipped under the line.*

Part two hands your text to a second chatbot for rewriting. It offers four approaches. I tried all four and measured how much of the original wording survived each one.

Translating into French and back preserved almost three quarters. Rephrasing preserved just over half. Rebuilding from bullet notes preserved a bit under half. The most aggressive rewrite preserved a third.

Translation turned out to be the feeblest option, which surprised me, since it is the trick most of us reach for first. Translators work one sentence at a time and hand back the same skeleton in different clothes. The rhythm never shifted at all. Those five paragraphs of four sentences stayed exactly where they were.

Two of the four rewrites would still be caught. The two that escaped had chewed through so much of the original that calling the result the same document felt generous.

## The part that broke my test

Here is where it got strange.

<!-- GIF 12_convergence.gif -->
*Four measurements. The orange mark is where the real Wikipedia article sits. Watch the dots overshoot it.*

Rewriting does make your text look more human. Then it keeps going.

The heaviest rewrite came out more uneven in its rhythm than the Wikipedia article. Its word choices were harder to predict than the Wikipedia article. On the very measurements that AI detectors run, it scored as more human than writing by actual humans.

Read that again, because it is the whole point. None of these numbers has a ceiling marked *person*. A tool that flags you for being too predictable will happily clear you for being wildly unpredictable, and it cannot separate an overcooked rewrite from a distinctive writer.

That failure already has casualties. These detectors are documented as scoring people who write in a second language as machine-like, because careful non-native prose genuinely is more predictable.

## The one thing that survived

Volunteers at Wikipedia keep a page called *Signs of AI writing*. It contains no statistics whatsoever. It is a catalogue of habits: puffing small facts up into milestones, brochure adjectives, vague gestures at what experts supposedly think, closing lines that only restate what you just read.

I turned that page into a simple checker.

My chatbot paragraph tripped it twenty-five times. The Wikipedia article tripped it once.

Every rewrite brought the count down. The best reached six, still six times the encyclopedia. What clung on hardest was the marketing vocabulary. *Rich and varied. Ambitious. Innovative. Outstanding. Every corner of the globe.* Those phrases survived a trip through French. They survived rephrasing. They survived being rebuilt from notes.

I owe my own checker one caveat. Part of that improvement was an illusion. The French round trip converted *widely regarded* into *generally considered*. Identical habit, different words, no longer caught by my pattern. A checker counts phrasings, not habits, so treat its verdict as a floor rather than a score.

## What to take from this

If someone accuses you, or your student, on the strength of a percentage from a detector, ask what that percentage measures.

It measures sentence rhythm and word rarity. A motivated cheat adjusts both in a single editing pass. An honest writer may fail both on the day they write with unusual care.

The hidden signature is a separate matter, and a narrower one. It answers exactly one question: did this company's system touch this text? It cannot tell you who thought of the ideas, because asking a chatbot to tidy three of your own sentences can stamp the output.

The most dependable tell I found in a week of work needed no software at all.

Read the thing. Count the sentences in each paragraph. If it runs 4, 4, 4, 4, 4, you already know.

---

*Code, data and twelve annotated visualisations: [github.com/nisaharan/ai-watermarks-3d](https://github.com/nisaharan/ai-watermarks-3d)*

*One matched pair of texts is one matched pair. Treat the direction of each effect as the finding and the size of it as a single sample. The rewrites came from prompting a model with the removal tool's own instructions rather than from the tool's own pipeline, and no detection score here is a measurement, because nobody outside the vendor holds the key.*
