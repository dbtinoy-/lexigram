"""Deterministic template replies driven by recalled context — no LLM.

This is the **domain renderer** — it receives recalled facts and the
user's message, then selects a template that proves memory is working.
No model calls, no embeddings, no vector search: just regex intent
detection + constraint echo.

Template selection logic:

1. **Food intent** ("menu", "eat", "dinner", ...) → constrained menu reply
   using diet/allergy facts
2. **Memory intent** ("remember", "know about me") → echo all stored facts
3. **Statement turn** (has facts, no food/memory intent) → acknowledge + echo
4. **Default** → "Noted! What would you like next?"

The ``Reply.cited`` list contains the constraint strings the template
used — this is what the UI displays as provenance, proving the reply
actually drew from stored memory, not hallucination.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from memory_chat.services.extraction import Triple

# Intent detection words — kept deliberately simple.  A real production
# system would use intent classification, but this demo's point is to
# prove the memory subsystem works, not to build a chatbot.
_FOOD_WORDS = ("food", "menu", "eat", "dinner", "lunch", "snack", "meal")
_REMEMBER_WORDS = ("remember", "know about me")


@dataclass(frozen=True)
class Reply:
    """A rendered turn: template text plus cited constraint facts.

    ``cited`` contains human-readable strings like ``"diet: vegetarian"``
    that the template engine used — displayed in the UI as provenance
    metadata, proving the reply drew from stored memory.
    """

    text: str
    cited: list[str] = field(default_factory=list)


def reply_for(text: str, facts: list[Triple]) -> Reply:
    """Select a template from intent + constraint facts.

    Intent detection is regex-over-keywords — deliberately simple for
    a demo that proves memory works, not chatbot intelligence.  The
    responder is called by ``ConciergeService.send`` after recall.
    """
    lowered = text.lower()
    # Filter to diet/allergy constraints — preferences don't constrain menus
    constraints = [f for f in facts if f[1] in ("diet", "allergy")]
    cited = [f"{predicate}: {obj}" for _, predicate, obj, _ in constraints]

    if any(word in lowered for word in _FOOD_WORDS):
        return _menu_reply(constraints, cited)
    if any(word in lowered for word in _REMEMBER_WORDS) and constraints:
        return Reply(f"You've told me: {'; '.join(cited)}.", cited)
    if cited:
        # A statement turn: acknowledge AND echo what was just learned.
        # This proves extraction worked — the reply cites facts extracted
        # from the user's own words in an earlier turn.
        return Reply(f"Noted — {'; '.join(cited)}. What's next?", cited)
    return Reply("Noted! What would you like next?")


def _menu_reply(constraints: list[Triple], cited: list[str]) -> Reply:
    """Menu templates — constrained when facts exist, open otherwise.

    This is the core demonstration: alice says "I'm vegetarian" in turn 1,
    then asks for a menu in turn 2, and the reply cites both constraints.
    Bob never said anything, so his menu is unconstrained.  That's the
    memory proving it works.
    """
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
