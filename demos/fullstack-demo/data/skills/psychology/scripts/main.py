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
        if not hook:
            hook = fields.get("Psychological Concept", "")
        ideas.append(Idea(
            title=p["title"],
            core_message=fields.get("Core Message", ""),
            hook_line=hook,
            identity_signal=fields.get("Identity Signal", ""),
            permission_given=fields.get("Real-World Application", ""),
            emotional_arc=fields.get("Emotional Arc", ""),
            target_audience=fields.get("Target Audience", ""),
            quotability_score=float(score_match.group()) if score_match else 0.0,
            share_trigger=fields.get("Share Trigger", ""),
            topic="psychology",
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
    app_sec, application = _extract_section(text, "APPLICATION")
    refl_sec, reflection = _extract_section(text, "REFLECTION")

    ctx_match = re.search(r'\[CONTEXT\s*[-—]\s*([\d.]+)s\]\s*\n"([^"]+)"', text)
    if not ctx_match:
        ctx_match = re.search(r'\[CONTEXT\s*[-—]\s*N?s?\]\s*\n"([^"]+)"', text)
        ctx_sec = None
    else:
        ctx_sec = float(ctx_match.group(1))
    ctx_text = ctx_match.group(2) if ctx_match else ""

    exp_match = re.search(r'\[EXPLANATION\s*[-—]\s*([\d.]+)s\]\s*\n((?:"[^"]+"\s*\n?)+)', text)
    if not exp_match:
        exp_match = re.search(r'\[EXPLANATION\s*[-—]\s*N?s?\]\s*\n((?:"[^"]+"\s*\n?)+)', text)
        exp_sec = None
    else:
        exp_sec = float(exp_match.group(1))
    exp_lines = re.findall(r'"([^"]+)"', exp_match.group(0) if exp_match else "")

    target = float(duration_match.group(1)) if duration_match else word_count / max(pacing_wps, 0.1)
    filled = _backfill_seconds(
        {"hook": hook_sec, "context": ctx_sec, "explanation": exp_sec, "application": app_sec, "reflection": refl_sec},
        target,
    )
    hook_sec = filled["hook"]
    ctx_sec = filled["context"]
    exp_sec = filled["explanation"]
    app_sec = filled["application"]
    refl_sec = filled["reflection"]

    total_dur = float(duration_match.group(1)) if duration_match else hook_sec + ctx_sec + exp_sec + app_sec + refl_sec

    arc_match = re.search(r"EMOTIONAL ARC MAP:\s*\n(.+)", text)
    arcs = [s.strip() for s in re.split(r"->|→", arc_match.group(1))] if arc_match else []

    sections = [
        ScriptSection("hook", hook, hook_sec),
        ScriptSection("context", ctx_text, ctx_sec),
        ScriptSection("explanation", " | ".join(exp_lines), exp_sec),
        ScriptSection("application", application, app_sec),
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
            "title": "The Spotlight Effect",
            "core": "We overestimate how much others notice and remember our flaws.",
            "hook": "You're not as visible as you think you are.",
            "concept": "Spotlight effect — the tendency to believe we're being noticed more than we are.",
            "application": "Take more risks in social situations — people aren't watching as closely as you fear.",
            "identity": "You're self-aware and intellectually curious.",
            "arc": "anxiety -> relief -> freedom",
            "audience": "socially anxious overthinkers, young professionals",
            "score": "9.1",
            "trigger": "Tag a friend who needs to hear they're not being judged",
        },
        {
            "title": "Why Your Brain Loves Shortcuts",
            "core": "Cognitive heuristics help us decide fast, but they lead to predictable errors.",
            "hook": "Your brain is lazy — and that's costing you.",
            "concept": "Cognitive heuristics — mental shortcuts that speed up decision-making but introduce bias.",
            "application": "Pause before snap judgments; ask 'what evidence am I missing?'",
            "identity": "You value clear thinking and self-awareness.",
            "arc": "curiosity -> recognition -> empowerment",
            "audience": "decision-makers, students, anyone prone to snap judgments",
            "score": "8.8",
            "trigger": "Share this with someone who always trusts their first instinct",
        },
        {
            "title": "The Paradox of Choice",
            "core": "More options don't make us happier — they make us more anxious and less satisfied.",
            "hook": "Too many choices might be making you miserable.",
            "concept": "The paradox of choice — Barry Schwartz's research on how abundance of options decreases satisfaction.",
            "application": "Set personal decision limits (e.g., only consider 3 options before choosing).",
            "identity": "You think critically about modern life.",
            "arc": "recognition -> discomfort -> clarity",
            "audience": "overwhelmed professionals, consumers, anyone facing decision fatigue",
            "score": "8.5",
            "trigger": "Send this to someone who spends 30 minutes choosing where to eat",
        },
        {
            "title": "The Halo Effect at Work",
            "core": "One positive trait unfairly colors our perception of everything else about a person.",
            "hook": "That impressive person you admire? You're probably wrong about half of what you assume.",
            "concept": "Halo effect — our tendency to let one positive attribute (looks, confidence, status) influence our overall judgment.",
            "application": "Evaluate people and ideas on separate dimensions — don't let one strength blind you to weaknesses.",
            "identity": "You see people clearly, without bias.",
            "arc": "awareness -> skepticism -> clarity",
            "audience": "hiring managers, investors, anyone evaluating others",
            "score": "8.7",
            "trigger": "Tag a friend who fell for a charismatic sales pitch",
        },
        {
            "title": "Cognitive Dissonance in Action",
            "core": "We change our beliefs to align with our actions — even when those actions are irrational.",
            "hook": "Your brain would rather rewrite reality than admit it was wrong.",
            "concept": "Cognitive dissonance — the mental discomfort of holding contradictory beliefs, leading us to rationalize instead of reconsider.",
            "application": "When you feel yourself defending a bad decision, pause and ask: 'Am I protecting my ego or finding truth?'",
            "identity": "You pursue truth over comfort.",
            "arc": "discomfort -> recognition -> growth",
            "audience": "anyone who has stayed in a bad relationship, job, or investment too long",
            "score": "9.2",
            "trigger": "Share this with someone who always has an excuse",
        },
        {
            "title": "The Anchoring Effect in Negotiations",
            "core": "The first number mentioned in a negotiation anchors everyone's expectations — even when it's arbitrary.",
            "hook": "The person who says the first number wins the negotiation.",
            "concept": "Anchoring effect — the cognitive bias where initial information (the anchor) disproportionately influences subsequent judgments.",
            "application": "Always state your number first in negotiations — you set the anchor. When buying, recognize the seller's anchor and consciously adjust.",
            "identity": "You negotiate with psychological savvy.",
            "arc": "naivety -> awareness -> strategic advantage",
            "audience": "negotiators, job seekers, sales professionals, bargain hunters",
            "score": "8.9",
            "trigger": "Use this in your next negotiation and thank me later",
        },
        {
            "title": "Loss Aversion: Why Fear Beats Hope",
            "core": "Losing hurts roughly twice as much as winning feels good — and this distorts our decisions.",
            "hook": "Your fear of losing is making you play smaller than you should.",
            "concept": "Loss aversion — Kahneman and Tversky's finding that losses loom larger than equivalent gains.",
            "application": "When making a decision, ask: 'What do I stand to gain?' not just 'What might I lose?' Reframe risk as opportunity.",
            "identity": "You make decisions based on upside, not fear.",
            "arc": "fear -> reframe -> boldness",
            "audience": "risk-averse investors, career changers, cautious decision-makers",
            "score": "9.0",
            "trigger": "Send this to someone who plays it too safe",
        },
        {
            "title": "The Dunning-Kruger Effect",
            "core": "Incompetent people overestimate their ability, while experts underestimate theirs.",
            "hook": "The dumbest people in the room are the most confident — and they have no idea.",
            "concept": "Dunning-Kruger effect — the cognitive bias where unskilled individuals suffer illusory superiority, while skilled individuals underestimate their competence.",
            "application": "If you feel confident about a complex topic, ask: 'What am I missing?' If you feel unsure, you're probably on the right track.",
            "identity": "You know what you don't know.",
            "arc": "false confidence -> humility -> genuine expertise",
            "audience": "new managers, recent graduates, social media commentators",
            "score": "9.3",
            "trigger": "Tag someone who needs to read this (gently)",
        },
        {
            "title": "The Mere Exposure Effect",
            "core": "We develop a preference for things simply because we're familiar with them.",
            "hook": "The reason you like that song is probably just that you've heard it before.",
            "concept": "Mere exposure effect — Zajonc's finding that repeated exposure increases liking, even without conscious awareness.",
            "application": "Use repetition strategically: show up consistently, and people will naturally warm to you and your ideas.",
            "identity": "You understand the psychology of influence.",
            "arc": "neutrality -> familiarity -> preference",
            "audience": "marketers, creators, job seekers, anyone building a personal brand",
            "score": "8.6",
            "trigger": "Share this with someone building a brand or following",
        },
        {
            "title": "The Bystander Effect and Personal Responsibility",
            "core": "The more people present in an emergency, the less likely anyone is to help.",
            "hook": "If you're in trouble, don't shout for help — point at one person.",
            "concept": "Bystander effect — diffusion of responsibility causes individuals to assume someone else will act.",
            "application": "In any group, assign specific tasks to specific people. Never say 'someone should...' — say 'Alex, can you...?'",
            "identity": "You take initiative when others hesitate.",
            "arc": "ignorance -> awareness -> personal responsibility",
            "audience": "team leaders, organizers, anyone working in groups",
            "score": "8.4",
            "trigger": "Tag someone who always steps up when others don't",
        },
        {
            "title": "The Peak-End Rule",
            "core": "We judge experiences not by their total quality, but by their peak moment and how they end.",
            "hook": "Your memory of a vacation has almost nothing to do with most of it.",
            "concept": "Peak-end rule — Kahneman's finding that our recollection of an experience is shaped primarily by its most intense moment and its conclusion.",
            "application": "Design experiences — dates, presentations, products — with a strong peak and a satisfying end. The rest matters less than you think.",
            "identity": "You design memorable experiences intentionally.",
            "arc": "realization -> strategic redesign -> impact",
            "audience": "UX designers, event planners, hosts, storytellers",
            "score": "8.8",
            "trigger": "Send this to someone planning an event or presentation",
        },
        {
            "title": "The Zeigarnik Effect: Unfinished Tasks",
            "core": "Our brains remember interrupted or unfinished tasks far better than completed ones.",
            "hook": "That half-finished project is taking up more mental space than you realize.",
            "concept": "Zeigarnik effect — the tendency to remember uncompleted or interrupted tasks more vividly than completed ones.",
            "application": "Start tasks you're likely to interrupt — the mental itch will pull you back. Or list unfinished items to free working memory.",
            "identity": "You understand how your memory really works.",
            "arc": "distraction -> insight -> control",
            "audience": "procrastinators, multitaskers, students",
            "score": "8.2",
            "trigger": "Tag someone who has 15 tabs open right now",
        },
        {
            "title": "The Backfire Effect in Arguments",
            "core": "When presented with evidence against their beliefs, people often believe them more strongly.",
            "hook": "Facts don't change minds — they often make them worse.",
            "concept": "Backfire effect — the phenomenon where correcting misinformation strengthens the original misconception.",
            "application": "Don't argue with facts alone. Find common identity first, then gently introduce alternative perspectives.",
            "identity": "You persuade with psychology, not confrontation.",
            "arc": "frustration -> understanding -> effective communication",
            "audience": "debators, parents, teachers, activists",
            "score": "9.1",
            "trigger": "Share this with someone who loves winning arguments",
        },
        {
            "title": "Fundamental Attribution Error",
            "core": "We attribute others' failures to their character and our own to circumstance.",
            "hook": "When you mess up it's 'the situation.' When they mess up it's 'who they are.'",
            "concept": "Fundamental attribution error — the tendency to overemphasize personality and underestimate situational factors when judging others.",
            "application": "Before judging someone's behavior, ask: 'What circumstances might explain this?' Extend the same grace you give yourself.",
            "identity": "You judge fairly and understand context.",
            "arc": "judgment -> empathy -> wisdom",
            "audience": "managers, parents, anyone in relationships",
            "score": "8.7",
            "trigger": "Tag someone who needs to be less judgmental",
        },
        {
            "title": "The Pratfall Effect",
            "core": "Competent people become more likable when they make a small mistake.",
            "hook": "Being too perfect actually makes people like you less.",
            "concept": "Pratfall effect — the tendency for perceptions of competent individuals to improve after they commit a minor blunder.",
            "application": "Admit small mistakes openly. Vulnerability after demonstrated competence builds trust and likability.",
            "identity": "You know that authenticity beats perfection.",
            "arc": "pressure -> relief -> connection",
            "audience": "leaders, public speakers, influencers, perfectionists",
            "score": "8.3",
            "trigger": "Send this to someone afraid of being imperfect",
        },
    ]
    lines = []
    for i in range(min(count, len(pool))):
        e = pool[i]
        lines.append(
            f"**IDEA #{i + 1}: {e['title']}\n"
            f"* Core Message: {e['core']}\n"
            f"* Hook Line: {e['hook']}\n"
            f"* Psychological Concept: {e['concept']}\n"
            f"* Real-World Application: {e['application']}\n"
            f"* Identity Signal: {e['identity']}\n"
            f"* Emotional Arc: {e['arc']}\n"
            f"* Target Audience: {e['audience']}\n"
            f"* Quotability Score: {e['score']}\n"
            f"* Share Trigger: {e['trigger']}"
        )
    return "\n\n".join(lines)


def mock_script() -> str:
    return """TITLE: The Spotlight Effect
DURATION: 50
WORD COUNT: 95
PACING: 1.9
[HOOK - 3s]
"You're not as visible as you think you are."
[BEAT]
[CONTEXT - 8s]
"Psychologists call this the spotlight effect — the belief that people notice and remember us far more than they actually do."
[EXPLANATION - 18s]
"In a famous study, researchers had students wear embarrassing t-shirts into a room full of strangers."
"Only half the observers could even identify who wore the shirt."
"The students predicted 50% would notice. The real number was closer to 20%."
[BEAT]
[APPLICATION - 10s]
"Next time you're worried about how you look or sound in public, remember: most people are too busy worrying about themselves to scrutinize you."
[REFLECTION - 6s]
"Paradoxically, realizing you're less visible gives you more freedom to be yourself."
EMOTIONAL ARC MAP: anxiety -> relief -> freedom
KEY INSIGHT: "You're not as visible as you think you are — and that's liberating."
CURIOUS QUESTION: What would you do differently if you knew no one was watching?"""


def mock_seo() -> str:
    return """YOUTUBE_TITLE: The Spotlight Effect: Why You're Not as Visible as You Think
YOUTUBE_DESCRIPTION: Discover the psychology behind the spotlight effect — and why we overestimate how much others notice us. Learn how this cognitive bias shapes social anxiety and what to do about it.
YOUTUBE_TAGS: psychology, spotlight effect, cognitive bias, social anxiety, behavioral science, mind
FACEBOOK_CAPTION: You're not as visible as you think. The spotlight effect explained."""
