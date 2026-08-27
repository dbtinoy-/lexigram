"""The two support-reply prompt variants under iteration.

Lexigram convention: ``repository/`` holds data access, fixtures, and
scripted stores.  These templates are plain Python — no framework imports
beyond the prompt contracts.  ``build_v1`` and ``build_v2`` are factories
that return fresh ``ChatPromptTemplate`` instances, keyed by variant id
in the ``TEMPLATES`` dict.

The ``PromptVariable`` declarations let the framework validate that every
``{issue}`` and ``{tone}`` placeholder is supplied at render time —
undeclared variables fail ``validate()`` with a clear error.
"""

from __future__ import annotations

from collections.abc import Callable

from lexigram.ai.prompt.template.base import AbstractPromptTemplate
from lexigram.ai.prompt.template.chat import ChatPromptTemplate
from lexigram.ai.prompt.variables.types import PromptVariable

__all__ = ["TEMPLATES", "VARIANT_LABELS", "build_v1", "build_v2"]

_VARS = [
    PromptVariable(name="issue"),
    PromptVariable(name="tone"),
]

_V2_EXAMPLES = (
    "Customer: My parcel is two weeks late.\n"
    "Agent: I'm so sorry about the delay — I'm happy to help you track "
    "it down right now.\n\n"
    "Customer: This refund process is confusing.\n"
    "Agent: Totally understandable! Happy to help walk you through it "
    "step by step."
)


def build_v1() -> AbstractPromptTemplate:
    """Terse instruction template."""
    return ChatPromptTemplate(
        "support-v1",
        system="You are a terse support agent. Answer in one sentence.",
        user="Issue: {issue}\nTone: {tone}\nAnswer:",
        variables=list(_VARS),
        version="1",
    )


def build_v2() -> AbstractPromptTemplate:
    """Empathetic few-shot template."""
    return ChatPromptTemplate(
        "support-v2",
        system=(
            "You are a warm support agent. Acknowledge feelings, then "
            "help. Follow the examples.\n\n" + _V2_EXAMPLES
        ),
        user="Issue: {issue}\nTone: {tone}\nAnswer:",
        variables=[PromptVariable(name=v.name) for v in _VARS],
        version="1",
    )


TEMPLATES: dict[str, Callable[[], AbstractPromptTemplate]] = {
    "v1": build_v1,
    "v2": build_v2,
}

VARIANT_LABELS = {"v1": "Terse", "v2": "Empathetic"}
