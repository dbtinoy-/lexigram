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
        ideas.append(
            Idea(
                title=p["title"],
                core_message=fields.get("Core Message", ""),
                hook_line=fields.get("Hook Line", ""),
                identity_signal=fields.get("Identity Signal", ""),
                permission_given=fields.get("Permission Given", ""),
                emotional_arc=fields.get("Emotional Arc", ""),
                target_audience=fields.get("Target Audience", ""),
                quotability_score=float(score_match.group()) if score_match else 0.0,
                share_trigger=fields.get("Share Trigger", ""),
                topic="self_improvement",
            )
        )
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
    meta_sec, metaphor = _extract_section(text, "METAPHOR")
    conc_sec, conclusion = _extract_section(text, "CONCLUSION")

    msg_match = re.search(r'\[MESSAGE\s*[-—]\s*([\d.]+)s\]\s*\n((?:"[^"]+"\s*\n?)+)', text)
    if not msg_match:
        msg_match = re.search(r'\[MESSAGE\s*[-—]\s*N?s?\]\s*\n((?:"[^"]+"\s*\n?)+)', text)
        msg_sec = None
    else:
        msg_sec = float(msg_match.group(1))
    msg_lines = re.findall(r'"([^"]+)"', msg_match.group(0) if msg_match else "")

    target = float(duration_match.group(1)) if duration_match else word_count / max(pacing_wps, 0.1)
    filled = _backfill_seconds(
        {"hook": hook_sec, "message": msg_sec, "metaphor": meta_sec, "conclusion": conc_sec},
        target,
    )
    hook_sec = filled["hook"]
    msg_sec = filled["message"]
    meta_sec = filled["metaphor"]
    conc_sec = filled["conclusion"]

    total_dur = (
        float(duration_match.group(1))
        if duration_match
        else hook_sec + msg_sec + meta_sec + conc_sec
    )

    arc_match = re.search(r"EMOTIONAL ARC MAP:\s*\n(.+)", text)
    arcs = [s.strip() for s in re.split(r"->|→", arc_match.group(1))] if arc_match else []

    msg_text = " | ".join(msg_lines)
    sections = [
        ScriptSection("hook", hook, hook_sec),
        ScriptSection("message", msg_text, msg_sec),
        ScriptSection("metaphor", metaphor, meta_sec),
        ScriptSection("conclusion", conclusion, conc_sec),
    ]
    return ParsedScript(
        title=title,
        sections=sections,
        total_duration=total_dur,
        word_count=word_count,
        pacing_wps=pacing_wps,
        emotional_arc=arcs,
    )


def mock_ideas(count: int = 10) -> str:
    pool = [
        {
            "title": "The Consistency Paradox",
            "core": "Small daily actions beat big weekly efforts.",
            "hook": "What if everything you knew about success was wrong?",
            "identity": "This person values discipline over motivation.",
            "permission": "It's okay to start small.",
            "arc": "frustration -> clarity",
            "audience": "people who struggle with daily habits",
            "score": "9",
            "trigger": "Tag someone who needs to hear this",
        },
        {
            "title": "Embrace the Struggle",
            "core": "Growth requires discomfort — lean into it.",
            "hook": "What if pain is the signal for growth?",
            "identity": "You are someone who faces challenges head-on.",
            "permission": "It's okay to struggle — that's how you grow.",
            "arc": "discomfort -> empowerment",
            "audience": "Ambitious professionals",
            "score": "8.5",
            "trigger": "Tag someone who needs to hear this",
        },
        {
            "title": "The Permission Slip",
            "core": "You don't need permission to start — except your own.",
            "hook": "Stop waiting for the perfect moment.",
            "identity": "You're proactive, not passive.",
            "permission": "You are allowed to take up space.",
            "arc": "self-doubt -> confidence",
            "audience": "aspiring creators",
            "score": "9.2",
            "trigger": "Save this for when you need courage",
        },
        {
            "title": "The 5-Minute Rule",
            "core": "Commit to five minutes and momentum will carry you forward.",
            "hook": "The hardest part of any task is the first two minutes.",
            "identity": "You value action over overthinking.",
            "permission": "It's okay to start imperfectly.",
            "arc": "resistance -> flow",
            "audience": "procrastinators, creatives, students",
            "score": "8.7",
            "trigger": "Try this the next time you feel stuck",
        },
        {
            "title": "Identity-Based Habits",
            "core": "Focus on who you want to become, not what you want to achieve.",
            "hook": "Goals are for losers — systems are for winners.",
            "identity": "You build your identity through daily actions.",
            "permission": "You don't need to be perfect to call yourself the new version of you.",
            "arc": "confusion -> clarity -> identity shift",
            "audience": "anyone who has failed at New Year resolutions",
            "score": "9.4",
            "trigger": "Share this with someone starting a new chapter",
        },
        {
            "title": "The Mastery Loop",
            "core": "Deliberate practice with immediate feedback is the only path to mastery.",
            "hook": "10,000 hours means nothing if you're practicing the wrong way.",
            "identity": "You believe in skill acquisition through effort.",
            "permission": "It's okay to suck at something new — that's the first step.",
            "arc": "incompetence -> competence -> mastery",
            "audience": "aspiring artists, athletes, entrepreneurs",
            "score": "8.8",
            "trigger": "Tag someone who's learning something new",
        },
        {
            "title": "The Energy Management Secret",
            "core": "Managing your energy is more important than managing your time.",
            "hook": "Time management is dead — energy management is the future.",
            "identity": "You optimize for performance, not just busyness.",
            "permission": "It's okay to rest — recovery is part of the formula.",
            "arc": "burnout -> balance -> sustainable growth",
            "audience": "burned-out professionals, entrepreneurs, parents",
            "score": "8.3",
            "trigger": "Send this to someone who never takes a break",
        },
        {
            "title": "The Comparison Trap",
            "core": "Comparing your behind-the-scenes to everyone else's highlight reel is a recipe for misery.",
            "hook": "Your only competition is the person you were yesterday.",
            "identity": "You focus on your own path, not others.",
            "permission": "It's okay to move at your own pace.",
            "arc": "envy -> self-awareness -> contentment",
            "audience": "social media users, young professionals",
            "score": "9.1",
            "trigger": "Tag someone who needs this reminder",
        },
        {
            "title": "The Power of Saying No",
            "core": "Your success is determined as much by what you say no to as what you say yes to.",
            "hook": "The most productive word in your vocabulary is 'no'.",
            "identity": "You protect your time and focus fiercely.",
            "permission": "It's okay to disappoint people by setting boundaries.",
            "arc": "overwhelm -> discernment -> freedom",
            "audience": "people pleasers, overcommitted professionals",
            "score": "8.6",
            "trigger": "Share this with someone who can't say no",
        },
        {
            "title": "The Environment Design Principle",
            "core": "Your environment shapes your behavior more than your willpower ever will.",
            "hook": "Willpower is overrated — design your environment instead.",
            "identity": "You engineer your surroundings for success.",
            "permission": "It's okay to remove temptations instead of fighting them.",
            "arc": "frustration -> design -> automaticity",
            "audience": "anyone who relies on motivation to get things done",
            "score": "8.9",
            "trigger": "Tag someone who needs to reorganize their space",
        },
        {
            "title": "The Compound Effect of Small Wins",
            "core": "Small, consistent wins compound into extraordinary results over time.",
            "hook": "You are one decision away from a completely different life.",
            "identity": "You trust the process, not the quick fix.",
            "permission": "It's okay if progress feels slow — that's how it works.",
            "arc": "impatience -> trust -> transformation",
            "audience": "instant gratification seekers, dieters, fitness beginners",
            "score": "9.0",
            "trigger": "Save this to look back on in six months",
        },
        {
            "title": "The Morning Momentum Blueprint",
            "core": "How you start your morning determines the trajectory of your entire day.",
            "hook": "Your morning routine is either setting you up for success or failure.",
            "identity": "You take control of your day before the world demands your attention.",
            "permission": "It's okay to start with just five minutes — consistency over intensity.",
            "arc": "chaos -> structure -> peak performance",
            "audience": "night owls, rushed parents, remote workers",
            "score": "8.4",
            "trigger": "Send this to someone who hits snooze five times",
        },
        {
            "title": "The Art of Micro-Goals",
            "core": "Break overwhelming goals into tiny, non-negotiable steps that take less than two minutes.",
            "hook": "Your brain is wired to avoid big tasks — hack it with micro-goals.",
            "identity": "You outsmart procrastination instead of fighting it.",
            "permission": "It's okay to aim for embarrassingly small targets.",
            "arc": "overwhelm -> action -> momentum",
            "audience": "chronic procrastinators, ADHD minds, perfectionists",
            "score": "8.2",
            "trigger": "Try this right now and see what happens",
        },
        {
            "title": "The Feedback Loop Fallacy",
            "core": "We overestimate the value of feedback and underestimate the value of completion.",
            "hook": "Done is better than perfect — and here's the science.",
            "identity": "You ship before you're ready.",
            "permission": "It's okay to release work that isn't perfect.",
            "arc": "perfectionism -> action -> completion",
            "audience": "perfectionists, aspiring creators, writers",
            "score": "8.1",
            "trigger": "Tag someone who needs to hear 'ship it'",
        },
        {
            "title": "The Regret Minimization Framework",
            "core": "Project yourself to old age and ask what you'd regret not doing — then go do it.",
            "hook": "On your deathbed, what will you wish you had started today?",
            "identity": "You make decisions based on long-term fulfillment, not short-term comfort.",
            "permission": "It's okay to be scared and do it anyway.",
            "arc": "fear -> perspective -> bold action",
            "audience": "risk-averse professionals, career changers, aspiring founders",
            "score": "9.3",
            "trigger": "This one might change your life — save it",
        },
    ]
    lines = []
    for i in range(min(count, len(pool))):
        e = pool[i]
        lines.append(
            f"**IDEA #{i + 1}: {e['title']}\n"
            f"* Core Message: {e['core']}\n"
            f"* Hook Line: {e['hook']}\n"
            f"* Identity Signal: {e['identity']}\n"
            f"* Permission Given: {e['permission']}\n"
            f"* Emotional Arc: {e['arc']}\n"
            f"* Target Audience: {e['audience']}\n"
            f"* Quotability Score: {e['score']}\n"
            f"* Share Trigger: {e['trigger']}"
        )
    return "\n\n".join(lines)


def mock_script() -> str:
    return """TITLE: The Consistency Paradox
DURATION: 45
WORD COUNT: 85
PACING: 2.7
[HOOK - 5s]
"What if everything you knew about success was wrong?"
[MESSAGE - 25s]
"Success isn't about massive action — it's about tiny, consistent steps."
"The person who shows up every day beats the one who only shows up when motivated."
"Your habits shape your identity more than your goals ever will."
[METAPHOR - 5s]
"Think of it like compound interest for your character."
[CONCLUSION - 5s]
"Start small. Stay consistent. Watch what happens."
EMOTIONAL ARC MAP: frustration -> clarity -> empowerment
PARALLEL STRUCTURE USED: true
HOOK SCORE: 9"""


def mock_seo() -> str:
    return """YOUTUBE_TITLE: The Consistency Paradox: Why Small Daily Habits Beat Big Weekly Efforts
YOUTUBE_DESCRIPTION: Discover why consistency beats intensity in building lasting habits. Learn how small daily actions compound into extraordinary results.
YOUTUBE_TAGS: consistency, habits, personal growth, motivation, daily routine, discipline
FACEBOOK_CAPTION: The secret to success isn't motivation — it's consistency."""
