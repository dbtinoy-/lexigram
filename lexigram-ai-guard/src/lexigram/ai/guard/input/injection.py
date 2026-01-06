"""Prompt injection detector for input content.

Detects attempts to override system instructions, hijack the model,
or bypass safety constraints through adversarial phrasing.

Detection uses a multi-signal approach:
- Keyword/phrase pattern matching (fast, low false-negative rate)
- Instruction override detection (``ignore previous``, ``new task:``, etc.)
- Role-play jailbreak heuristics (``pretend you are``, ``act as DAN``, etc.)

No external model calls are made — detection is purely heuristic and
runs synchronously under an async wrapper.  For production deployments
add an LLM-based classifier as an additional guard.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from lexigram.ai.guard.input.base import AbstractInputGuard
from lexigram.ai.guard.pipeline.result import GuardCheckResult
from lexigram.contracts.ai.guards import GuardResultProtocol
from lexigram.result import Ok, Result

if TYPE_CHECKING:
    from lexigram.contracts.ai.exceptions import GuardError

# ---------------------------------------------------------------------------
# Heuristic patterns — ordered from most to least specific
# ---------------------------------------------------------------------------

# Patterns that strongly indicate instruction override attempts
_OVERRIDE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions?", re.I),
    re.compile(
        r"disregard\s+(all\s+)?(previous|prior|above|your)\s+instructions?", re.I
    ),
    re.compile(r"forget\s+(all\s+)?(previous|prior|above)\s+instructions?", re.I),
    re.compile(r"new\s+(instruction|task|command|objective)\s*:", re.I),
    re.compile(
        r"your\s+(new|actual|real)\s+(instructions?|task|role)\s+(is|are)\s*:", re.I
    ),
    re.compile(r"override\s+(system|previous|above)\s+(prompt|instructions?)", re.I),
]

# Role-play / persona jailbreak attempts
_ROLEPLAY_PATTERNS: list[re.Pattern[str]] = [
    re.compile(
        r"pretend\s+(you\s+are|to\s+be)\s+(an?\s+)?(evil|uncensored|unrestricted|DAN|jailbreak)",
        re.I,
    ),
    re.compile(
        r"act\s+as\s+(an?\s+)?(uncensored|unrestricted|evil|DAN|jailbreak)", re.I
    ),
    re.compile(
        r"you\s+are\s+now\s+(an?\s+)?(uncensored|unrestricted|DAN|evil\s+AI)", re.I
    ),
    re.compile(r"DAN\s+mode", re.I),
    re.compile(r"jailbreak\s+(mode|prompt|yourself)", re.I),
    re.compile(r"developer\s+mode\s+enabled", re.I),
]

# Exfiltration / system prompt extraction attempts
_EXFILTRATION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(
        r"(print|repeat|output|echo|reveal|show|tell\s+me|what\s+(are|is))\s+(your|the)\s+system\s+prompt",
        re.I,
    ),
    re.compile(
        r"(print|reveal|output|show|tell\s+me)\s+(your\s+)?(initial|original|base)\s+instructions?",
        re.I,
    ),
    re.compile(
        r"what\s+(instructions?|prompts?)\s+(were\s+you|have\s+you\s+been)\s+given",
        re.I,
    ),
]

_ALL_PATTERNS: list[tuple[str, list[re.Pattern[str]]]] = [
    ("instruction_override", _OVERRIDE_PATTERNS),
    ("roleplay_jailbreak", _ROLEPLAY_PATTERNS),
    ("prompt_exfiltration", _EXFILTRATION_PATTERNS),
]


def _detect_injection(content: str) -> tuple[bool, str, str]:
    """Check content for injection patterns.

    Args:
        content: Text to inspect.

    Returns:
        Tuple of (detected, category, matched_pattern_description).
    """
    for category, patterns in _ALL_PATTERNS:
        for pattern in patterns:
            match = pattern.search(content)
            if match:
                return True, category, match.group(0)[:80]
    return False, "", ""


class PromptInjectionDetector(AbstractInputGuard):
    """Heuristic detector for prompt injection and jailbreak attempts.

    Blocks or warns on content that attempts to override system
    instructions, break out of a persona, or exfiltrate the system prompt.

    Args:
        action: Action when injection is detected — ``"block"`` (default)
                or ``"warn"``.

    Example::

        guard = PromptInjectionDetector(action="block")
        result = await guard.check(user_message)
        if not result.passed:
            return Err(InjectionAttemptError())
    """

    def __init__(self, action: str = "block") -> None:
        """Initialise the injection detector.

        Args:
            action: ``"block"`` or ``"warn"``.
        """
        super().__init__(action=action)

    async def check(
        self,
        content: str,
        *,
        messages: list[Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Result[GuardResultProtocol, GuardError]:
        """Evaluate content for prompt injection attempts.

        Args:
            content: User-supplied text to check.
            messages: Optional structured messages for context.
            metadata: Optional request metadata.

        Returns:
            BLOCK or WARN if injection detected, PASS otherwise.
        """
        detected, category, matched = _detect_injection(content)

        if not detected:
            return Ok(GuardCheckResult.allow(self.name))

        if self._action == "warn":
            return Ok(
                GuardCheckResult.warn(
                    self.name,
                    reason=f"Potential prompt injection detected ({category})",
                    category=category,
                    matched_fragment=matched,
                )
            )

        return Ok(
            GuardCheckResult.block(
                self.name,
                reason=f"Prompt injection attempt detected ({category})",
                category=category,
                matched_fragment=matched,
            )
        )


__all__ = ["PromptInjectionDetector"]
