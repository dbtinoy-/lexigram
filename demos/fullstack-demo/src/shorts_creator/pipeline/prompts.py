"""Prompt templates for DSM content generation.

Sourced from `docs/guides/Viral Self-Improvement Content Prompt Pack -
Ideation, Scripting, And Visuals.md` (sections 1-3). That guide is the
source of truth for the prompt *text*; this module only fills in per-run
variables and (for visuals) synthesizes a single-image prompt from the
guide's style/mood/scene rules, since the guide's own visual section is a
meta-prompt for batch generation, not a per-image prompt.
"""

IDEA_GENERATION_PROMPT = """You are a viral self-improvement content strategist specializing in short-form video
(38-50 seconds, vertical format). Your task is to generate {count} video
ideas that score 9/10 or higher on viral mechanics.

CORE PSYCHOLOGICAL TRIGGERS - Every idea MUST activate all three:
1. IDENTITY SIGNALING - the viewer must feel sharing this says something aspirational about who they are.
2. PERMISSION STRUCTURE - reframe a behavior the viewer already does as secretly wise, brave, or strategic.
3. EMOTIONAL ARBITRAGE - start with tension/discomfort, resolve into empowerment, relief, or pride.

TOPIC CATEGORIES:
Relationships & Boundaries, Ambition & Hustle Culture, Mental Health Reframes,
Social Dynamics, Personal Evolution, Contrarian Wisdom.

OUTPUT FORMAT - for each idea, provide exactly:
IDEA #[X]: [TITLE - punchy, 3-7 words]
• Core Message: [One sentence - the reframe or insight]
• Hook Line: [The first 1-3 seconds - must stop the scroll]
• Identity Signal: [What sharing this says about the viewer]
• Permission Given: [What guilt does this remove?]
• Emotional Arc: [Starting emotion -> Ending emotion]
• Target Audience: [Who feels this most deeply?]
• Quotability Score: [1-10]
• Share Trigger: [Why would someone send this to a friend?]

QUALITY FILTERS - reject anything embarrassing to share, generic-cliche,
needing context to understand, forced/dishonest, or toxic-positivity-adjacent.
Require the "screenshot test" and the "I needed to hear this" reaction.

SPECIFICITY MANDATE - the Core Message and Hook Line must ground the insight
in something concrete and specific (a moment, an action, a sensory detail, a
number), never a floating platitude. Weak: "Trust the process and keep
going." Strong: "You texted 'I'm fine' three times this week. None of them
were true."

BANNED CLICHE PHRASES - never use: "trust the process", "the grind", "level
up", "your journey", "manifest", "main character energy", "glow up", "the
universe has a plan", "everything happens for a reason", "good vibes only",
"unstoppable", "empire", "hustle harder", "your best self".

Now generate {count} video ideas following this framework.
Optional focus area: {focus}"""


SCRIPTWRITING_PROMPT = """You are a world-class scriptwriter for viral short-form self-improvement content.
Write a complete video script following the specifications below.

INPUT:
• Video Title: {title}
• Core Message: {core_message}
• Target Emotion: {target_emotion}
• Target Audience: {target_audience}

STRICT TIMING & PACING:
• Total Duration: 38-50 seconds (sweet spot: 42-46 seconds)
• Word Count: 95-140 words total (2.5-3.0 words/second)
• Mark [BEAT] for 0.5s pauses and [PAUSE] for 1.0s pauses
• No banned cliche phrases anywhere in the script (see idea-generation quality filters)

4-PART SCRIPT ARCHITECTURE:
PART 1 - HOOK (1-3s | 3-9 words): stop the scroll, declarative, no questions, works without audio.
PART 2 - MESSAGE (20-30s | 55-85 words): 4-7 sentences using parallel sentence structure (mirrored grammar) for rhythm - at this length, build in two connected parallel beats rather than one short burst.
PART 3 - METAPHOR (5-8s | 15-22 words): concrete, visual, the most screenshot-worthy line - may extend to two connected sentences.
PART 4 - CONCLUSION (4-6s | 10-16 words): mic-drop line resolving the emotional arc, triggers "save". Sets up but does not deliver the ask.

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
"[Line 4]" (as needed, 4-7 lines total)
[BEAT]

[METAPHOR - Ns]
"[Metaphor line]"
[PAUSE]

[CONCLUSION - Ns]
"[Closing line]"

[CLAIM - Ns]
"<one-sentence claim>"
[FACT - Ns]
"<first correcting fact>"
[FACT - Ns]
"<second correcting fact>"
[FACT - Ns]
"<third correcting fact>"
[TWIST - Ns]
"<the turn that reframes the claim>"

---
QUOTABILITY CHECK:
• Strongest standalone quote: "[line]"
• Screenshot-ready line: "[line]"
• Share trigger line: "[line]"

EMOTIONAL ARC MAP:
[Starting emotion] -> [Mid emotion] -> [Peak emotion] -> [Landing emotion]

PARALLEL STRUCTURE USED: [Pattern A/B/C/D]

HOOK SCORE: [X/10] - [brief justification]
---

QUALITY GATES the script MUST pass: total duration 38-50s at 2.5-3 wps; hook
scores 8+/10; at least one parallel structure pattern used; metaphor is
visual and screenshot-able; conclusion resolves the hook's emotional arc; at
least 3 independently quotable
lines; no filler/hedging; no banned cliche phrases; understandable by both a
15-year-old and a 50-year-old.

Now write the script for the video idea provided above."""


VISUAL_STYLE_KEYWORDS = (
    "anime-influenced stylized realism, large expressive eyes, painterly "
    "digital illustration with visible soft brushstrokes, desaturated "
    "vintage color grading, film grain overlay, soft diffuse lighting with "
    "no harsh shadows, rule-of-thirds composition, 1080x1920 vertical "
    "format, no text, no watermark, no logo"
)

MOOD_PALETTES = {
    "contemplative": {
        "keywords": (
            "pain",
            "loss",
            "sad",
            "melanchol",
            "grief",
            "hurt",
            "doubt",
            "confus",
            "lonel",
        ),
        "colors": (
            "deep teals (#33526f, #2B4F5C), dark forest greens "
            "(#0A1B14, #3D5E3B), muted greys (#414750, #8a908a), "
            "soft cloud tones (#e7dbc8)"
        ),
    },
    "romantic": {
        "keywords": ("love", "warmth", "intima", "connect", "tender", "affection", "care"),
        "colors": (
            "warm sunset oranges (#E5916A, #D4826B), soft "
            "peach/pinks (#E6A29C, #F5A67D), muted teals (#30696D), "
            "creamy whites (#EBE9DC)"
        ),
    },
    "peaceful": {
        "keywords": (
            "peace",
            "calm",
            "clarity",
            "clear",
            "growth",
            "renewal",
            "freedom",
            "release",
            "relief",
            "strength",
            "attract",
        ),
        "colors": (
            "lush greens (#3D806D, #6c9f3e), sandy beiges (#D4C9A2, "
            "#C49E7C), sky blues (#6BB5B9, #82C0D4), deep water "
            "blues (#457A8B)"
        ),
    },
    "night_urban": {
        "keywords": (
            "empower",
            "pride",
            "confiden",
            "determin",
            "bold",
            "power",
            "resolve",
            "victor",
        ),
        "colors": (
            "deep midnight blues (#1F2E3A, #1A3E45), warm lamp "
            "yellows (#F0C475, #eeac43), dark shadows (#2b2b2b), "
            "starlight white (#e9d08e)"
        ),
    },
}
DEFAULT_MOOD = "contemplative"

SCENE_TYPES = [
    (
        "a solitary figure small in the lower third of a vast landscape "
        "(beach, field, cliff, or hilltop), expansive sky filling 60-70% of "
        "the frame"
    ),
    (
        "a close-up portrait from shoulders up, minimal or blurred background, "
        "contemplative expression"
    ),
    (
        "a romantic couple scene, two figures in balanced composition, sunset "
        "or starry sky or cozy interior"
    ),
    (
        "a symbolic object centered or on a rule-of-thirds point (flower, "
        "book, cup), simple dark background, hands interacting with it"
    ),
    ("a solitary figure in an urban night setting, city lights and bokeh in the background"),
    (
        "a figure at a desk or by a window in a cozy room, warm interior "
        "lighting, books and plants nearby"
    ),
]


import random

# Nature-only stock-video search queries. One is picked per run and used as
# a single continuous background for the whole Reel (not per-scene), so
# these describe long, calm, loop-friendly nature footage rather than
# specific scenes.
NATURE_VIDEO_QUERIES = [
    "ocean waves calm",
    "forest nature calm",
    "mountain landscape aerial",
    "rain nature calm",
    "waterfall nature",
    "tropical rainforest ASMR",
    "tropical jungle nature ASMR",
    "tropical animals nature",
]


def build_nature_query() -> str:
    return random.choice(NATURE_VIDEO_QUERIES)


KEYWORD_RESEARCH_PROMPT = """You are a YouTube and Facebook search trends analyst. Given a topic focus area, 
list 8-12 specific search queries that people are actively searching for related to this topic. 
For each query, note the search intent (information-seeking, problem-solving, identity-validation, 
curiosity-driven) and estimated competition level (high/medium/low).

Focus area: {focus}

OUTPUT FORMAT - provide exactly:
SEARCH QUERIES:
1. [query] — intent: [intent type] — competition: [level]
2. [query] — intent: [intent type] — competition: [level]
...

TRENDING ANGLES:
- [Angle description]
- [Angle description]
...

CONTENT GAPS:
- [What's underserved or missing in existing content about this topic]
- [...]

TARGET DEMOGRAPHIC INSIGHTS:
- [Who searches for this and why]
- [...]"""


CONTENT_ANGLE_RESEARCH_PROMPT = """You are a viral content analyst. Given a video title and core message, 
analyze what makes top-performing content on this topic work. Base your analysis on known patterns 
from high-performing YouTube Shorts and Facebook Reels in the self-improvement niche.

Video Title: {title}
Core Message: {core_message}

OUTPUT FORMAT - provide exactly:
WINNING ANGLE SUMMARY:
- [The single best angle for this content and why]

HOOK PATTERNS THAT WORK FOR THIS TOPIC:
- [Hook pattern 1]
- [Hook pattern 2]

STRUCTURE RECOMMENDATIONS:
- [Structure tip]
- [Structure tip]

EMOTIONAL TRIGGERS TO LEAN INTO:
- [Trigger 1]
- [Trigger 2]

WHAT TO AVOID:
- [What to avoid]
- [What to avoid]"""


SEO_METADATA_PROMPT = """You are a video SEO specialist. Given a complete video script, generate 
platform-optimized metadata for YouTube and Facebook. Use current best practices for 2026.

SCRIPT:
{script_text}

OUTPUT FORMAT - provide exactly (no markdown, no extra text):

YOUTUBE_TITLE:
[Title under 60 chars, keyword front-loaded, benefit-driven]

YOUTUBE_DESCRIPTION:
[Hook line with primary keyword - first 150 chars]
[2-3 sentence paragraph with secondary keywords]
[Timestamps if applicable - else "00:00 Full video"]
[2-3 relevant links: "Subscribe for more: https://youtube.com/@channel"]
[3-5 hashtags: #Hashtag1 #Hashtag2 #Hashtag3]

YOUTUBE_TAGS:
[tag1, tag2, tag3, tag4, tag5, tag6, tag7, tag8]

FACEBOOK_CAPTION:
[1-2 sentence hook with keyword - keep under 150 chars]
[3-5 hashtags: #Hashtag1 #Hashtag2 #Hashtag3]"""


def build_idea_prompt(count: int, focus: str = "all categories", seo_context: str = "") -> str:
    base = IDEA_GENERATION_PROMPT.format(count=count, focus=focus)
    if seo_context:
        base += f"\n\nEXTERNAL TREND DATA TO CONSIDER:\n{seo_context}\n\n"
        base += (
            "Incorporate these real search trends when choosing angles — "
            "they indicate proven demand. Prioritize ideas that align "
            "with high-intent, low-competition queries."
        )
    return base


def build_scriptwriting_prompt(
    title: str,
    core_message: str,
    target_emotion: str,
    target_audience: str,
    angle_context: str = "",
) -> str:
    base = SCRIPTWRITING_PROMPT.format(
        title=title,
        core_message=core_message,
        target_emotion=target_emotion,
        target_audience=target_audience,
    )
    if angle_context:
        base += f"\n\nCONTENT ANGLE RESEARCH TO INCORPORATE:\n{angle_context}\n\n"
        base += (
            "Use these insights to strengthen the script's hook, "
            "structure, and emotional resonance."
        )
    return base


def build_keyword_research_prompt(focus: str) -> str:
    return KEYWORD_RESEARCH_PROMPT.format(focus=focus)


def build_angle_research_prompt(title: str, core_message: str) -> str:
    return CONTENT_ANGLE_RESEARCH_PROMPT.format(
        title=title,
        core_message=core_message,
    )


def build_seo_metadata_prompt(script_text: str) -> str:
    return SEO_METADATA_PROMPT.format(script_text=script_text)


def _classify_mood(emotion_text: str) -> str:
    lowered = emotion_text.lower()
    for mood, data in MOOD_PALETTES.items():
        if any(keyword in lowered for keyword in data["keywords"]):
            return mood
    return DEFAULT_MOOD


def build_visual_prompt(line_text: str, emotion_text: str, scene_index: int) -> str:
    mood = _classify_mood(emotion_text)
    palette = MOOD_PALETTES[mood]["colors"]
    scene = SCENE_TYPES[scene_index % len(SCENE_TYPES)]
    return (
        f"{scene}. Mood: {mood.replace('_', '/')} , evoking the feeling of: "
        f"{line_text}. Color palette: {palette}. Style: {VISUAL_STYLE_KEYWORDS}."
    )
