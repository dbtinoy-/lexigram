import re

from shorts_creator.topics.base import (
    Idea,
    ParsedScript,
    ScriptSection,
    _backfill_seconds,
    _extract_section,
    _parse_common_ideas,
    _parse_myth_script,
    _parse_topn_script,
)


def parse_ideas(text: str) -> list[Idea]:
    parsed = _parse_common_ideas(text)
    ideas = []
    for p in parsed:
        fields = p["fields"]
        score_text = fields.get("Quotability Score", "0")
        score_match = re.search(r"[\d.]+", score_text)
        hook = fields.get("Hook Line", "")
        ideas.append(Idea(
            title=p["title"],
            core_message=fields.get("Core Message", ""),
            hook_line=hook,
            identity_signal=fields.get("Stoic Principle", ""),
            permission_given=fields.get("Modern Application", ""),
            emotional_arc=fields.get("Emotional Arc", ""),
            target_audience=fields.get("Target Audience", ""),
            quotability_score=float(score_match.group()) if score_match else 0.0,
            share_trigger=fields.get("Share Trigger", ""),
            topic="stoic",
        ))
    return ideas


def parse_script(text: str) -> ParsedScript:
    if "[TOP_ITEMS" in text:
        return _parse_topn_script(text)
    if "[CLAIM" in text:
        return _parse_myth_script(text)
    title_match = re.search(r"TITLE:\s*(.+)", text)
    title = title_match.group(1).strip() if title_match else "Untitled"
    wc_match = re.search(r"WORD COUNT:\s*(\d+)", text)
    word_count = int(wc_match.group(1)) if wc_match else 0
    pacing_match = re.search(r"PACING:\s*([\d.]+)", text)
    pacing_wps = float(pacing_match.group(1)) if pacing_match else 0.0
    duration_match = re.search(r"DURATION:\s*([\d.]+)", text)

    hook_sec, hook = _extract_section(text, "HOOK")
    prob_sec, problem = _extract_section(text, "PROBLEM")
    prac_sec, practice = _extract_section(text, "PRACTICE")
    refl_sec, reflection = _extract_section(text, "REFLECTION")

    prin_match = re.search(r'\[PRINCIPLE\s*[-—]\s*([\d.]+)s\]\s*\n"([^"]+)"', text)
    if not prin_match:
        prin_match = re.search(r'\[PRINCIPLE\s*[-—]\s*N?s?\]\s*\n"([^"]+)"', text)
        prin_sec = None
    else:
        prin_sec = float(prin_match.group(1))
    prin_text = prin_match.group(2) if prin_match else ""

    target = float(duration_match.group(1)) if duration_match else word_count / max(pacing_wps, 0.1)
    filled = _backfill_seconds(
        {"hook": hook_sec, "problem": prob_sec, "principle": prin_sec, "practice": prac_sec, "reflection": refl_sec},
        target,
    )
    hook_sec = filled["hook"]
    prob_sec = filled["problem"]
    prin_sec = filled["principle"]
    prac_sec = filled["practice"]
    refl_sec = filled["reflection"]

    total_dur = float(duration_match.group(1)) if duration_match else hook_sec + prob_sec + prin_sec + prac_sec + refl_sec

    arc_match = re.search(r"EMOTIONAL ARC MAP:\s*\n(.+)", text)
    arcs = [s.strip() for s in re.split(r"->|→", arc_match.group(1))] if arc_match else []

    sections = [
        ScriptSection("hook", hook, hook_sec),
        ScriptSection("problem", problem, prob_sec),
        ScriptSection("principle", prin_text, prin_sec),
        ScriptSection("practice", practice, prac_sec),
        ScriptSection("reflection", reflection, refl_sec),
    ]
    return ParsedScript(
        title=title, sections=sections,
        total_duration=total_dur, word_count=word_count, pacing_wps=pacing_wps,
        emotional_arc=arcs,
    )


def mock_ideas(count: int = 10) -> str:
    pool = [
        {
            "title": "You Are Not Your Thoughts",
            "core": "Stoicism teaches that between a stimulus and your response lies your power of choice — and most people forget they have it.",
            "hook": "You are not your thoughts. You are the one noticing them.",
            "philosopher": "Epictetus",
            "principle": "The Dichotomy of Control",
            "application": "Next time you feel anxiety or anger rising, pause and ask: 'Is this in my control?' — the answer will set you free.",
            "arc": "overwhelm -> clarity -> empowerment",
            "audience": "overthinkers, anxious professionals, chronic worriers",
            "score": "9.3",
            "trigger": "Tag someone who needs to hear they are not their anxiety",
        },
        {
            "title": "The Art of Negative Visualization",
            "core": "Imagining loss is not morbid — it is the fastest path to gratitude and presence.",
            "hook": "To appreciate what you have, imagine losing it.",
            "philosopher": "Seneca",
            "principle": "Negative Visualization (Praemeditatio Malorum)",
            "application": "Each morning, briefly imagine losing one thing you take for granted — your health, your home, a loved one. Then feel the gratitude flood in.",
            "arc": "discomfort -> appreciation -> peace",
            "audience": "anyone feeling entitled, ungrateful, or stuck in comparison",
            "score": "8.9",
            "trigger": "Send this to a friend who needs perspective",
        },
        {
            "title": "The Shortness of Life",
            "core": "Life is not short — we make it short by wasting most of it on things that do not matter.",
            "hook": "You will die. Are you spending your time like it?",
            "philosopher": "Seneca",
            "principle": "Memento Mori",
            "application": "At the end of each day, ask yourself: 'Did I live today as if it were my last, or did I waste it on things I won't remember?'",
            "arc": "urgency -> reflection -> clarity",
            "audience": "procrastinators, people-pleasers, anyone who feels life is passing them by",
            "score": "9.1",
            "trigger": "Save this — it will reframe your entire week",
        },
        {
            "title": "The Wall of Discipline",
            "core": "Discipline is the bridge between your goals and your accomplishments — and it must be built daily.",
            "hook": "Motivation is a liar. Discipline is the only truth.",
            "philosopher": "Marcus Aurelius",
            "principle": "Discipline as the foundation of character",
            "application": "Choose one small, uncomfortable action each morning and do it before you check your phone. That's your discipline deposit for the day.",
            "arc": "weakness -> struggle -> strength",
            "audience": "anyone who relies on motivation and keeps failing",
            "score": "9.0",
            "trigger": "Tag someone who needs to stop waiting for motivation",
        },
        {
            "title": "The View from Above",
            "core": "Zooming out to a cosmic perspective dissolves the importance of petty worries and daily frustrations.",
            "hook": "Your biggest problem right now is microscopic from space.",
            "philosopher": "Marcus Aurelius",
            "principle": "Cosmic perspective (The View from Above)",
            "application": "When a problem feels overwhelming, visualize yourself from space — then from orbit, then from the edge of the solar system. Watch how small your worry becomes.",
            "arc": "overwhelm -> perspective -> peace",
            "audience": "stress-prone professionals, chronic worriers, anxious parents",
            "score": "8.8",
            "trigger": "Share this with someone who needs perspective today",
        },
        {
            "title": "The Invictus Mindset",
            "core": "You cannot control what happens to you, but you can always control your response — and that is everything.",
            "hook": "They can take everything from you except one thing: your choice of response.",
            "philosopher": "Epictetus",
            "principle": "The ruling center — your ability to choose your response",
            "application": "When something outside your control goes wrong, say: 'This is indifferent. What matters is how I respond.' Then choose dignity over reactivity.",
            "arc": "victimhood -> ownership -> indomitability",
            "audience": "anyone who feels victimized by circumstances",
            "score": "9.4",
            "trigger": "Save this for when life feels unfair",
        },
        {
            "title": "The Art of Voluntary Discomfort",
            "core": "Choosing discomfort deliberately builds resilience and shrinks the power of fear.",
            "hook": "Comfort is slowly killing your potential.",
            "philosopher": "Seneca",
            "principle": "Voluntary discomfort (Voluntaria Incommoditas)",
            "application": "Once a week, do something uncomfortable on purpose — cold shower, sleeping on the floor, fasting a meal. Notice how your fear of discomfort shrinks.",
            "arc": "softness -> discomfort -> resilience",
            "audience": "comfort seekers, growth-minded individuals, stoic practitioners",
            "score": "8.7",
            "trigger": "Tag someone who needs to get uncomfortable",
        },
        {
            "title": "The Obstacle Is the Way",
            "core": "What stands in the path becomes the path itself — turn obstacles into fuel.",
            "hook": "The thing blocking your path is actually your path forward.",
            "philosopher": "Marcus Aurelius",
            "principle": "Turning obstacles into opportunities",
            "application": "When you hit a wall, don't look for a way around. Ask: 'How does this obstacle show me the way forward?' The blockage IS the direction.",
            "arc": "frustration -> reframe -> forward motion",
            "audience": "entrepreneurs, creators, anyone facing setbacks",
            "score": "9.2",
            "trigger": "Send this to someone going through a tough time",
        },
        {
            "title": "The Inner Citadel",
            "core": "Build a fortress within yourself that no external event can breach.",
            "hook": "If your peace depends on external circumstances, you are a slave to them.",
            "philosopher": "Marcus Aurelius",
            "principle": "The Inner Citadel — constructing an unshakable inner fortress",
            "application": "Each morning, imagine putting on armor: 'Nothing outside my own judgment can harm me.' Throughout the day, retreat into your citadel when chaos strikes.",
            "arc": "vulnerability -> construction -> unshakability",
            "audience": "emotionally reactive people, leaders under pressure, first responders",
            "score": "8.6",
            "trigger": "Tag someone who needs emotional armor today",
        },
        {
            "title": "The Preemptive Pause",
            "core": "Before reacting, pause and ask: 'Is this within my control?' — the answer defuses the reaction.",
            "hook": "The space between stimulus and response is where your freedom lives.",
            "philosopher": "Epictetus",
            "principle": "The preemptive pause before reaction",
            "application": "Set a phone reminder that says 'PAUSE' three times a day. When it goes off, take one breath and ask: 'Am I responding or reacting?'",
            "arc": "reactivity -> awareness -> conscious choice",
            "audience": "reactive personalities, parents, leaders, drivers in traffic",
            "score": "8.5",
            "trigger": "Try this today — it will change how you handle stress",
        },
        {
            "title": "The Nightly Audit",
            "core": "Daily self-reflection is the Stoic's most powerful tool for continuous improvement.",
            "hook": "The person who does not examine their day is doomed to repeat their mistakes.",
            "philosopher": "Seneca",
            "principle": "Daily self-audit and reflection",
            "application": "Each night, ask three questions: 'What did I do well? What could I improve? What will I do differently tomorrow?' Write it down.",
            "arc": "blindness -> awareness -> growth",
            "audience": "anyone committed to self-improvement, leaders, parents",
            "score": "8.4",
            "trigger": "Share this with someone who wants to grow intentionally",
        },
        {
            "title": "The Circle of Control",
            "core": "Focus all your energy on what you can control and release everything else — this is the heart of Stoic practice.",
            "hook": "90% of your stress comes from things you cannot control.",
            "philosopher": "Epictetus",
            "principle": "The Circle (Dichotomy) of Control",
            "application": "Draw two circles on paper. Inside: your thoughts, actions, and choices. Outside: everything else. Spend your energy only inside the inner circle today.",
            "arc": "anxiety -> focus -> serenity",
            "audience": "chronic worriers, control freaks, anxious leaders",
            "score": "9.0",
            "trigger": "Draw this circle today — it will change how you see everything",
        },
        {
            "title": "Amor Fati — Love of Fate",
            "core": "Love everything that happens to you, including the suffering — it's all material for growth.",
            "hook": "Don't just accept what happens — love it.",
            "philosopher": "Nietzsche (channeling Stoic roots)",
            "principle": "Amor Fati — embracing and loving one's fate completely",
            "application": "When something goes 'wrong,' add the phrase 'and that's exactly what I needed.' Not as denial — as reframing every event into fuel.",
            "arc": "resistance -> acceptance -> active love of fate",
            "audience": "anyone struggling with acceptance, grief, or unexpected change",
            "score": "9.1",
            "trigger": "Save this — it's the ultimate mindset shift",
        },
        {
            "title": "The Garbage In, Garbage Out Rule",
            "core": "What you consume — media, conversations, food, entertainment — shapes your character. Guard your inputs.",
            "hook": "You are not what you eat. You are what you consume mentally.",
            "philosopher": "Seneca",
            "principle": "Mindful curation of external influences",
            "application": "Audit your inputs for one week: What do you read, watch, listen to, and talk about? Cut anything that doesn't serve your character.",
            "arc": "passive consumption -> curated awareness -> character growth",
            "audience": "social media addicts, news junkies, anyone feeling mentally polluted",
            "score": "8.3",
            "trigger": "Tag someone who scrolls too much",
        },
        {
            "title": "The Final Hour Test",
            "core": "Before any action, ask: 'If this were my last day, would I do this?' It clarifies everything.",
            "hook": "You are dying. Are your current worries worthy of your final hours?",
            "philosopher": "Seneca",
            "principle": "Memento Mori applied to daily decisions",
            "application": "Before acting on something trivial, imagine your final hour. Would you care about this email, this argument, this worry? Let the answer guide your attention.",
            "arc": "triviality -> perspective -> meaningful action",
            "audience": "people who get caught up in drama, perfectionists, workaholics",
            "score": "8.9",
            "trigger": "Ask yourself this before your next frustration",
        },
    ]
    lines = []
    for i in range(min(count, len(pool))):
        e = pool[i]
        lines.append(
            f"**IDEA #{i + 1}: {e['title']}\n"
            f"* Core Message: {e['core']}\n"
            f"* Hook Line: {e['hook']}\n"
            f"* Relevant Philosopher: {e['philosopher']}\n"
            f"* Stoic Principle: {e['principle']}\n"
            f"* Modern Application: {e['application']}\n"
            f"* Emotional Arc: {e['arc']}\n"
            f"* Target Audience: {e['audience']}\n"
            f"* Quotability Score: {e['score']}\n"
            f"* Share Trigger: {e['trigger']}"
        )
    return "\n\n".join(lines)


def mock_script() -> str:
    return """TITLE: You Are Not Your Thoughts
DURATION: 52
WORD COUNT: 85
PACING: 1.6
PHILOSOPHER: Epictetus
[HOOK - 3s]
"You are not your thoughts. You are the one noticing them."
[BEAT]
[PROBLEM - 10s]
"Most people live at the mercy of every emotion that arises — anger, anxiety, craving — as if they have no choice but to obey."
[PRINCIPLE - 18s]
"Epictetus taught that between a stimulus and your response there is a space. In that space is your power to choose. The things outside your control — opinions, events, other people's actions — are indifferent. What matters is how you respond."
[BEAT]
[PRACTICE - 12s]
"Today, when you feel a reactive emotion rising, pause for one breath. Say to yourself: 'This is a impression, not a command.' Then choose your response — not your reaction."
[REFLECTION - 7s]
"The Stoics called this the ruling center. Guard it. Everything else is externals."
EMOTIONAL ARC MAP: overwhelm -> clarity -> empowerment
STOIC SOURCE: Epictetus, Discourses — "We are not disturbed by things, but by the view we take of them."
DAILY PRACTICE: Set three alarms today. When each rings, pause and ask: "Am I reacting or choosing?" """


def mock_seo() -> str:
    return """YOUTUBE_TITLE: You Are Not Your Thoughts — A Stoic Lesson on Emotional Mastery
YOUTUBE_DESCRIPTION: Epictetus taught that between stimulus and response lies your power of choice. Learn how the Dichotomy of Control can free you from anxiety and reactive living.
YOUTUBE_TAGS: stoicism, stoic philosophy, epictetus, dichotomy of control, emotional mastery, ancient wisdom, mental health, resilience
FACEBOOK_CAPTION: You are not your thoughts. You are the one noticing them. — Epictetus"""
