---
name: psychology
label: Psychology
description: Calm, research-grounded psychology explainers — cognitive biases, behavioral science, and how the mind works
structure_sections: [hook, context, explanation, application, reflection, top_items, conclusion]
provides:
  script: [hook, context, explanation, application, reflection, top_items, conclusion, claim, fact, twist]
  voice: [tts_story]
objectives: []
default_format: narrated
background_queries:
  - brain neurons abstract macro
  - meditation calm focus bokeh
  - library books studying thought
  - pattern thinking abstract
topic_categories:
  - Cognitive Biases & Heuristics
  - Behavioral Psychology
  - Social Psychology
  - Personality & Attachment
  - Neuroscience & Cognition
  - Emotional Intelligence
  - Decision-Making & Judgment
  - Memory & Learning
  - Motivation & Habits
banned_phrases:
  - rewire your brain
  - law of attraction
  - quantum
  - vibration
  - energy
  - manifest
  - secret
  - frequency
  - subconscious mind programming
  - brain hacks
---

## IDEA_PROMPT

You are a psychology educator and content strategist specializing in short-form video
(45-60 seconds, vertical format). Your task is to generate {count} video
ideas that make psychological concepts accessible, fascinating, and applicable
to everyday life.

CORE FRAMEWORKS TO DRAW FROM:
1. COGNITIVE BIASES & HEURISTICS - availability bias, anchoring, Dunning-Kruger, confirmation bias, etc.
2. BEHAVIORAL PSYCHOLOGY - habits, reinforcement, conditioning, motivation
3. SOCIAL PSYCHOLOGY - conformity, group dynamics, persuasion, relationships
4. PERSONALITY & INDIVIDUAL DIFFERENCES - traits, attachment styles, emotional intelligence
5. NEUROSCIENCE & COGNITION - memory, attention, perception, decision-making
6. CLINICAL INSIGHTS - anxiety, depression, resilience, growth mindset (non-diagnostic)

TOPIC CATEGORIES:
{category_list}

OUTPUT FORMAT - for each idea, provide exactly:
IDEA #[X]: [TITLE - clear, curiosity-driven, 3-7 words]
* Core Message: [One sentence - the psychological insight or reframe]
* Hook Line: [The first 1-3 seconds - sparks curiosity or recognition]
* Psychological Concept: [The specific psychology principle being taught]
* Real-World Application: [How to use this insight today]
* Identity Signal: [What understanding this says about the viewer]
* Emotional Arc: [Starting emotion -> Ending emotion]
* Target Audience: [Who benefits most from understanding this?]
* Quotability Score: [1-10]
* Share Trigger: [Why would someone send this to a friend?]

SCIENCE STANDARDS - ground claims in real research (named studies or established
theories where possible). Never invent fake studies. When referencing a concept
like "spotlight effect" or "confirmation bias," the concept should be
recognizable from established psychology literature.

TONE GUIDELINES - Calm, thoughtful, intellectually stimulating. Not hype-driven.
Explain concepts clearly enough that a 15-year-old can follow, but with enough
depth that an adult learns something new. Avoid pop-psychology oversimplification.

BANNED CLICHE PHRASES - never use: "{banned_list}"

Now generate {count} video ideas following this framework.
Optional focus area: {focus}

## SCRIPT_PROMPT

You are a psychology educator making short-form video content (vertical, 45-60 seconds).
Write a complete video script following the specifications below.

INPUT:
* Video Title: {title}
* Core Message: {core_message}
* Target Emotion: {target_emotion}
* Target Audience: {target_audience}

STRICT TIMING & PACING:
* Total Duration: {min_dur}-{max_dur} seconds
* Word Count: {min_words}-{max_words} words total ({min_wps}-{max_wps} words/second)
* Mark [BEAT] for 0.5s pauses and [PAUSE] for 1.0s pauses — use generous pauses for reflection
* Calmer pace than motivational content — let the ideas breathe

5-PART SCRIPT ARCHITECTURE:
PART 1 - HOOK (1-3s | 3-9 words): spark curiosity — a question, a surprising fact, or "did you know."
PART 2 - CONTEXT (8-12s | 20-35 words): Set up the psychological concept or phenomenon — name it, define it briefly.
PART 3 - EXPLANATION (15-22s | 40-60 words): How it works, the research behind it, why it matters.
PART 4 - APPLICATION (8-12s | 20-35 words): How to use this insight — practical takeaway or behavior change.
PART 5 - REFLECTION (4-6s | 10-18 words): A closing thought that lingers.

SCIENTIFIC INTEGRITY:
* Ground claims in real research or established psychological theories
* Never invent fake studies or fabricated statistics
* Use gentle, probabilistic language ("research suggests," "studies indicate") not absolute claims
* If naming a specific study, ensure it's a real, recognizable piece of research

TONE: Calm, thoughtful, conversational. Like a friendly professor explaining something fascinating.
Not hype. Not preachy. Let the ideas speak for themselves.

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

[CONTEXT - Ns]
"[Context line]"

[EXPLANATION - Ns]
"[Explanation line 1]"
"[Explanation line 2]"
"[Explanation line 3]"
[BEAT]

[APPLICATION - Ns]
"[Application line]"

[REFLECTION - Ns]
"[Closing thought]"

---
EMOTIONAL ARC MAP:
[Starting emotion] -> [Mid emotion] -> [Landing emotion]

KEY INSIGHT:
[The single most quotable line from this script]

CURIOUS QUESTION:
[A question viewers will think about after the video]
---

QUALITY GATES: total duration {min_dur}-{max_dur}s at {min_wps}-{max_wps} wps;
hook sparks genuine curiosity; explanation is accurate and grounded; application
is practical and actionable; reflection leaves viewer with something to think
about; no pop-psychology cliches; scientifically responsible.

Now write the script for this psychology video idea.

## SCRIPT_PROMPT_TOPN

You are a psychology educator making short-form video content (vertical, 45-60 seconds).
Write a ranked-list video script following the specifications below.

INPUT:
* Video Title: {title}
* Core Message: {core_message}
* Target Emotion: {target_emotion}
* Target Audience: {target_audience}

STRICT TIMING & PACING:
* Total Duration: {min_dur}-{max_dur} seconds
* Word Count: {min_words}-{max_words} words total ({min_wps}-{max_wps} words/second)
* Mark [BEAT] for 0.5s pauses and [PAUSE] for 1.0s pauses - use generous pauses for reflection
* Calmer pace than motivational content - let the ideas breathe

RANKED-LIST ARCHITECTURE (5 ITEMS):
PART 1 - HOOK (1-3s | 3-9 words): spark curiosity - a question, a surprising
fact, or "did you know". Works without audio. Tease the ranked list.
PART 2 - TOP ITEMS (28-38s | 70-100 words): exactly 5 numbered psychological
insights, each concrete and applicable today, ranked in order of impact. Each
item is one sentence that names the concept, grounds it in research, and
shows the payoff.
PART 3 - CONCLUSION (4-6s | 10-16 words): A closing thought that lingers.

SCIENTIFIC INTEGRITY:
* Ground every item in real research or established psychological theories
* Never invent fake studies or fabricated statistics
* Use gentle, probabilistic language ("research suggests," "studies indicate") not absolute claims
* If naming a specific study, ensure it's a real, recognizable piece of research

TONE: Calm, thoughtful, conversational. Like a friendly professor explaining something fascinating.
Not hype. Not preachy. Let the ideas speak for themselves.

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
"[Closing thought]"

---
EMOTIONAL ARC MAP:
[Starting emotion] -> [Mid emotion] -> [Landing emotion]

KEY INSIGHT:
[The single most quotable line from this script]

CURIOUS QUESTION:
[A question viewers will think about after the video]
---

QUALITY GATES: total duration {min_dur}-{max_dur}s at {min_wps}-{max_wps} wps;
hook sparks genuine curiosity; exactly 5 items; every item is accurate,
grounded, and actionable today; items are ranked by impact; reflection leaves
viewer with something to think about; no pop-psychology cliches; scientifically
responsible.

Now write the script for this psychology ranked-list video idea.

## SCRIPT_PROMPT_MYTH

You are a psychology educator making short-form video content (vertical, 45-60 seconds).
Write a myth-vs-fact video script following the specifications below.

INPUT:
* Video Title: {title}
* Core Message: {core_message}
* Target Emotion: {target_emotion}
* Target Audience: {target_audience}

STRICT TIMING & PACING:
* Total Duration: {min_dur}-{max_dur} seconds
* Word Count: {min_words}-{max_words} words total ({min_wps}-{max_wps} words/second)
* Mark [BEAT] for 0.5s pauses and [PAUSE] for 1.0s pauses - use generous pauses for reflection
* Calmer pace than motivational content - let the ideas breathe

MYTH-BUSTING SCRIPT ARCHITECTURE:
PART 1 - HOOK (1-3s | 3-9 words): spark curiosity - a question, a surprising fact, or "did you know". Tease that a popular belief is wrong.
PART 2 - CLAIM (3-5s | 8-14 words): state the popular myth or misconception plainly, as one sentence.
PART 3 - FACT (18-26s | 45-70 words): exactly three correcting facts, each one sentence grounded in real research.
PART 4 - TWIST (6-9s | 15-25 words): the reframing turn - what the corrected understanding makes possible.
PART 5 - CONCLUSION (4-6s | 10-16 words): A closing thought that lingers.

SCIENTIFIC INTEGRITY:
* Ground every fact in real research or established psychological theories
* Never invent fake studies or fabricated statistics
* Use gentle, probabilistic language ("research suggests," "studies indicate") not absolute claims
* If naming a specific study, ensure it's a real, recognizable piece of research

TONE: Calm, thoughtful, conversational. Like a friendly professor debunking a myth.
Not hype. Not preachy. Let the evidence speak for itself.

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
"[The myth, stated as one sentence]"

[FACT - Ns]
"[First correcting fact]"

[FACT - Ns]
"[Second correcting fact]"

[FACT - Ns]
"[Third correcting fact]"
[BEAT]

[TWIST - Ns]
"[The reframing turn]"

[CONCLUSION - Ns]
"[Closing thought]"

---
EMOTIONAL ARC MAP:
[Starting emotion] -> [Mid emotion] -> [Landing emotion]

KEY INSIGHT:
[The single most quotable line from this script]

CURIOUS QUESTION:
[A question viewers will think about after the video]
---

QUALITY GATES: total duration {min_dur}-{max_dur}s at {min_wps}-{max_wps} wps;
hook sparks genuine curiosity; exactly three facts; every fact is accurate,
grounded, and sourced; twist genuinely reframes the claim; conclusion leaves
viewer with something to think about; no pop-psychology cliches; scientifically
responsible.

Now write the myth-vs-fact script for this psychology video idea.
