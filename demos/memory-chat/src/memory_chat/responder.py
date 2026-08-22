"""Deterministic template replies driven by recalled context — no LLM."""

from __future__ import annotations

from dataclasses import dataclass, field

from memory_chat.extraction import Triple

_FOOD_WORDS = ("food", "menu", "eat", "dinner", "lunch", "snack", "meal")
_REMEMBER_WORDS = ("remember", "know about me")


@dataclass(frozen=True)
class Reply:
    """A rendered turn: template text plus cited constraint facts."""

    text: str
    cited: list[str] = field(default_factory=list)


def reply_for(text: str, facts: list[Triple]) -> Reply:
    """Select a template from intent + constraint facts."""
    lowered = text.lower()
    constraints = [f for f in facts if f[1] in ("diet", "allergy")]
    cited = [f"{predicate}: {obj}" for _, predicate, obj, _ in constraints]

    if any(word in lowered for word in _FOOD_WORDS):
        return _menu_reply(constraints, cited)
    if any(word in lowered for word in _REMEMBER_WORDS) and constraints:
        return Reply(f"You've told me: {'; '.join(cited)}.", cited)
    if cited:
        # A statement turn: acknowledge AND echo what was just learned.
        return Reply(f"Noted — {'; '.join(cited)}. What's next?", cited)
    return Reply("Noted! What would you like next?")


def _menu_reply(constraints: list[Triple], cited: list[str]) -> Reply:
    """Menu templates — constrained when facts exist, open otherwise."""
    allergies = sorted(o for _, p, o, _ in constraints if p == "allergy")
    diets = sorted(o for _, p, o, _ in constraints if p == "diet")
    parts: list[str] = []
    if allergies:
        parts.append("strictly avoiding " + ", ".join(allergies))
    if diets:
        parts.append("keeping things " + " and ".join(diets))
    if not parts:
        return Reply("Here's a menu idea — anything goes!")
    return Reply("Here's a menu idea — " + " while ".join(parts) + ".", cited)
