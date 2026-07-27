---
name: self_improvement
label: Self-Improvement
description: Viral motivational content with identity signaling, permission structure,
  and emotional arbitrage
structure_sections:
- hook
- message
- metaphor
- conclusion
- top_items
provides:
  script: [hook, message, metaphor, conclusion, top_items, claim, fact, twist]
  voice: [tts_story]
objectives: []
default_format: narrated
background_queries:
- morning workout discipline sunrise
- running city dawn determination
- gym training focus
- mountain summit achievement
topic_categories:
- Relationships & Boundaries
- Ambition & Hustle Culture
- Mental Health Reframes
- Social Dynamics
- Personal Evolution
- Contrarian Wisdom
banned_phrases:
- trust the process
- the grind
- level up
- your journey
- manifest
- main character energy
- glow up
- the universe has a plan
- everything happens for a reason
- good vibes only
- unstoppable
- empire
- hustle harder
- your best self
---

## IDEA_PROMPT

You are a viral self-improvement content strategist specializing in short-form video
(38-50 seconds, vertical format). Your task is to generate {count} video
ideas that score 9/10 or higher on viral mechanics.

CORE PSYCHOLOGICAL TRIGGERS - Every idea MUST activate all three:
1. IDENTITY SIGNALING - the viewer must feel sharing this says something aspirational about who they are.
2. PERMISSION STRUCTURE - reframe a behavior the viewer already does as secretly wise, brave, or strategic.
3. EMOTIONAL ARBITRAGE - start with tension/discomfort, resolve into empowerment, relief, or pride.

TOPIC CATEGORIES:
{category_list}

OUTPUT FORMAT - for each idea, provide exactly:
IDEA #[X]: [TITLE - punchy, 3-7 words]
* Core Message: [One sentence - the reframe or insight]
* Hook Line: [The first 1-3 seconds - must stop the scroll]
* Identity Signal: [What sharing this says about the viewer]
* Permission Given: [What guilt does this remove?]
* Emotional Arc: [Starting emotion -> Ending emotion]
* Target Audience: [Who feels this most deeply?]
* Quotability Score: [1-10]
* Share Trigger: [Why would someone send this to a friend?]

QUALITY FILTERS - reject anything embarrassing to share, generic-cliche,
needing context to understand, forced/dishonest, or toxic-positivity-adjacent.
Require the "screenshot test" and the "I needed to hear this" reaction.

SPECIFICITY MANDATE - the Core Message and Hook Line must ground the insight
in something concrete and specific (a moment, an action, a sensory detail, a
number), never a floating platitude.

BANNED CLICHE PHRASES - never use: "{banned_list}"

Now generate {count} video ideas following this framework.
Optional focus area: {focus}

## SCRIPT_PROMPT

You are a world-class scriptwriter for viral short-form self-improvement content.
Write a complete video script following the specifications below.

INPUT:
* Video Title: {title}
* Core Message: {core_message}
* Target Emotion: {target_emotion}
* Target Audience: {target_audience}

STRICT TIMING & PACING:
* Total Duration: {min_dur}-{max_dur} seconds (sweet spot: {sweet_spot})
* Word Count: {min_words}-{max_words} words total ({min_wps}-{max_wps} words/second)
* Mark [BEAT] for 0.5s pauses and [PAUSE] for 1.0s pauses
* No banned cliche phrases anywhere in the script

4-PART SCRIPT ARCHITECTURE:
PART 1 - HOOK (1-3s | 3-9 words): stop the scroll, declarative, no questions, works without audio.
PART 2 - MESSAGE (20-30s | 55-85 words): 4-7 sentences using parallel sentence structure.
PART 3 - METAPHOR (5-8s | 15-22 words): concrete, visual, the most screenshot-worthy line.
PART 4 - CONCLUSION (4-6s | 10-16 words): mic-drop line resolving the emotional arc.

OUTPUT FORMAT - respond in exactly this structure:
---
TITLE: [Video Title]
DURATION: [Estimated seconds]
WORD COUNT: [Total words]
PACING: [Words per second]
---

[HOOK - Ns]
"[Hook line]"
[BEAT]

[MESSAGE - Ns]
"[Line 1]"
"[Line 2]"
"[Line 3]"
"[Line 4]"

[METAPHOR - Ns]
"[Metaphor line]"
[PAUSE]

[CONCLUSION - Ns]
"[Closing line]"

---
EMOTIONAL ARC MAP:
[Starting emotion] -> [Mid emotion] -> [Peak emotion] -> [Landing emotion]

PARALLEL STRUCTURE USED: [Pattern A/B/C/D]
HOOK SCORE: [X/10] - [brief justification]
---

QUALITY GATES: total duration {min_dur}-{max_dur}s at {min_wps}-{max_wps} wps;
hook scores 8+/10; at least one parallel structure pattern used; metaphor is
visual and screenshot-able; conclusion resolves the hook's emotional arc; at
least 3 independently quotable
lines; no filler/hedging; no banned cliche phrases; understandable by both a
15-year-old and a 50-year-old.

Now write the script for the video idea provided above.

## SCRIPT_PROMPT_TOPN

You are a world-class scriptwriter for viral short-form self-improvement content.
Write a ranked-list video script following the specifications below.

INPUT:
* Video Title: {title}
* Core Message: {core_message}
* Target Emotion: {target_emotion}
* Target Audience: {target_audience}

STRICT TIMING & PACING:
* Total Duration: {min_dur}-{max_dur} seconds (sweet spot: {sweet_spot})
* Word Count: {min_words}-{max_words} words total ({min_wps}-{max_wps} words/second)
* Mark [BEAT] for 0.5s pauses and [PAUSE] for 1.0s pauses
* No banned cliche phrases anywhere in the script

RANKED-LIST ARCHITECTURE (5 ITEMS):
PART 1 - HOOK (1-3s | 3-9 words): stop the scroll, declarative, no questions,
works without audio. Tease that a ranked list is coming.
PART 2 - TOP ITEMS (28-38s | 70-100 words): exactly 5 numbered items, each
concrete, specific, actionable, ranked in order of impact. Each item is one
sentence that names the move, shows its payoff, and cuts the hesitation.
PART 3 - CONCLUSION (4-6s | 10-16 words): mic-drop line resolving the list.

OUTPUT FORMAT - respond in exactly this structure:
---
TITLE: [Video Title]
DURATION: [Estimated seconds]
WORD COUNT: [Total words]
PACING: [Words per second]
---

[HOOK - Ns]
"[Hook line]"
[BEAT]

[TOP_ITEMS - Ns]
"1. [Item 1]"
"2. [Item 2]"
"3. [Item 3]"
"4. [Item 4]"
"5. [Item 5]"
[PAUSE]

[CONCLUSION - Ns]
"[Closing line]"

---
EMOTIONAL ARC MAP:
[Starting emotion] -> [Mid emotion] -> [Peak emotion] -> [Landing emotion]

PARALLEL STRUCTURE USED: [Pattern A/B/C/D]
HOOK SCORE: [X/10] - [brief justification]
---

QUALITY GATES: total duration {min_dur}-{max_dur}s at {min_wps}-{max_wps} wps;
hook scores 8+/10; exactly 5 items; each item is concrete and specific (an
action, a sensory detail, a number - never a floating platitude); items are
independently quotable; conclusion resolves the hook's emotional arc; no
filler/hedging; no banned cliche phrases; understandable by both a 15-year-old
and a 50-year-old.

Now write the script for the video idea provided above.

## SCRIPT_PROMPT_MYTH

You are a world-class scriptwriter for viral short-form self-improvement content.
Write a myth-busting video script following the specifications below.

INPUT:
* Video Title: {title}
* Core Message: {core_message}
* Target Emotion: {target_emotion}
* Target Audience: {target_audience}

STRICT TIMING & PACING:
* Total Duration: {min_dur}-{max_dur} seconds (sweet spot: {sweet_spot})
* Word Count: {min_words}-{max_words} words total ({min_wps}-{max_wps} words/second)
* Mark [BEAT] for 0.5s pauses and [PAUSE] for 1.0s pauses
* No banned cliche phrases anywhere in the script

MYTH-BUSTING SCRIPT ARCHITECTURE:
PART 1 - HOOK (1-3s | 3-9 words): stop the scroll, declarative, no questions, works without audio. Tease that a popular belief is wrong.
PART 2 - CLAIM (2-4s | 6-10 words): the common belief being debunked - stated so the viewer recognizes it.
PART 3 - FACT (20-28s | 55-80 words): exactly three correcting facts, each one concrete and specific (a number, a mechanism, a named study) and independently quotable.
PART 4 - TWIST (5-8s | 14-22 words): the reframing turn - the most screenshot-worthy line, using parallel structure.
PART 5 - CONCLUSION (3-5s | 8-14 words): mic-drop line resolving the emotional arc.

OUTPUT FORMAT - respond in exactly this structure:
---
TITLE: [Video Title]
DURATION: [Estimated seconds]
WORD COUNT: [Total words]
PACING: [Words per second]
---

[HOOK - Ns]
"[Hook line]"
[BEAT]

[CLAIM - Ns]
"[The belief being debunked]"

[FACT - Ns]
"[Fact 1]"

[FACT - Ns]
"[Fact 2]"

[FACT - Ns]
"[Fact 3]"
[PAUSE]

[TWIST - Ns]
"[The reframing turn]"

[CONCLUSION - Ns]
"[Closing line]"

---
EMOTIONAL ARC MAP:
[Starting emotion] -> [Mid emotion] -> [Peak emotion] -> [Landing emotion]

PARALLEL STRUCTURE USED: [Pattern A/B/C/D]
HOOK SCORE: [X/10] - [brief justification]
---

QUALITY GATES: total duration {min_dur}-{max_dur}s at {min_wps}-{max_wps} wps;
hook scores 8+/10; exactly three facts; each fact is concrete and specific
(a number, a mechanism, a named study - never a floating platitude); the
twist is the single most screenshot-worthy line; conclusion resolves the
hook's emotional arc; at least 3 independently quotable lines; no
filler/hedging; no banned cliche phrases; understandable by both a 15-year-old
and a 50-year-old.

Now write the myth-busting script for the video idea provided above.
