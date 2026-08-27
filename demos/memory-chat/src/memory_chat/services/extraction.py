"""Declarative fact extraction — regex rules over first-person statements.

Pure function; returns empty list on no match.  Subject is ALWAYS the
owner_id: semantic memory is not owner-scoped by contract, so subject
namespacing is what keeps users isolated.

Extraction rules map natural-language statements to structured triples::

    "I'm vegetarian"
    → ("alice", "diet", "vegetarian", 0.9)

    "I'm allergic to peanuts"
    → ("alice", "allergy", "peanuts", 0.95)

    "I like Thai food"
    → ("alice", "preference", "thai", 0.7)

Each predicate carries a fixed confidence weight — allergy/diet are
high-confidence (user knows what they want), preference is lower (taste
may change).  The responder uses these weights for template selection;
the semantic store uses them for fact importance ranking.

Rules are deliberately simple regex patterns.  A real production system
would use an LLM-backed extractor or a fine-tuned classifier — but this
demo proves the memory subsystem works standalone without any model.
"""

from __future__ import annotations

import re

Triple = tuple[str, str, str, float]

# Confidence weights per predicate — allergy/diet are high (user knows what
# they want), preference is lower (taste may change).  These propagate to
# semantic store importance ranking.
_CONFIDENCE: dict[str, float] = {
    "diet": 0.9,
    "allergy": 0.95,
    "preference": 0.7,
}

# Each rule: (compiled regex, predicate label).
# Patterns match first-person statements — the demo assumes a conversational
# interface where the user says "I'm vegetarian" or "I'm allergic to peanuts".
# A production system would use an LLM-backed extractor instead.
_RULES: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(
            r"\bi(?:'m| am)\s+(?:a\s+)?(vegetarian|vegan|pescatarian)\b",
            re.IGNORECASE,
        ),
        "diet",
    ),
    (
        re.compile(r"\bi(?:'m| am)\s+allergic\s+to\s+([\w-]+)", re.IGNORECASE),
        "allergy",
    ),
    (
        re.compile(r"\bi\s+have\s+(?:a\s+)?([\w-]+)\s+allergy", re.IGNORECASE),
        "allergy",
    ),
    (
        re.compile(r"\bi\s+(?:really\s+)?like\s+([\w-]+)", re.IGNORECASE),
        "preference",
    ),
]


def extract_facts(owner_id: str, text: str) -> list[Triple]:
    """Extract deduplicated (subject, predicate, object, confidence).

    Subject is always ``owner_id`` — this is how isolation works when
    semantic memory isn't owner-scoped by contract.

    Returns an empty list on no match, so callers can safely iterate
    without guarding.
    """
    triples: list[Triple] = []
    seen: set[tuple[str, str, str]] = set()
    for pattern, predicate in _RULES:
        for match in pattern.finditer(text):
            obj = match.group(1).lower()
            key = (owner_id, predicate, obj)
            if key in seen:
                continue  # restating a fact must not duplicate storage
            seen.add(key)
            triples.append((owner_id, predicate, obj, _CONFIDENCE[predicate]))
    return triples
