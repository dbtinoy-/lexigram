"""Declarative fact extraction — regex rules over first-person statements.

Pure function; returns empty list on no match. Subject is ALWAYS the
owner_id: semantic memory is not owner-scoped by contract, so subject
namespacing is what keeps users isolated.
"""

from __future__ import annotations

import re

Triple = tuple[str, str, str, float]

_CONFIDENCE: dict[str, float] = {
    "diet": 0.9,
    "allergy": 0.95,
    "preference": 0.7,
}

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
    """Extract deduplicated (subject, predicate, object, confidence)."""
    triples: list[Triple] = []
    seen: set[tuple[str, str, str]] = set()
    for pattern, predicate in _RULES:
        for match in pattern.finditer(text):
            obj = match.group(1).lower()
            key = (owner_id, predicate, obj)
            if key in seen:
                continue
            seen.add(key)
            triples.append((owner_id, predicate, obj, _CONFIDENCE[predicate]))
    return triples
