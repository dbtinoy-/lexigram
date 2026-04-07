"""PII (Personally IdentifiableProtocol Information) detector for input content.

Detects and optionally redacts PII in user input before it is sent to an
external LLM provider.  Detection uses regex patterns — no external API
calls are made.

Supported PII entity types:
- ``EMAIL``       — email addresses
- ``PHONE``       — US/international phone numbers
- ``SSN``         — US Social Security Numbers (``xxx-xx-xxxx`` format)
- ``CREDIT_CARD`` — major card formats (Visa, MC, Amex, Discover)
- ``IP_ADDRESS``  — IPv4 addresses
- ``AWS_KEY``     — AWS access key IDs

When ``action="redact"`` the matched content is replaced with
``[REDACTED:<ENTITY_TYPE>]``.  When ``action="block"`` the request is
rejected entirely.  When ``action="warn"`` the request is allowed but a
structured warning is returned.
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
# PII patterns
# ---------------------------------------------------------------------------

_PII_PATTERNS: dict[str, re.Pattern[str]] = {
    "EMAIL": re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"),
    "PHONE": re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    "SSN": re.compile(r"\b(?!000|666|9\d{2})\d{3}-(?!00)\d{2}-(?!0000)\d{4}\b"),
    "CREDIT_CARD": re.compile(
        r"\b(?:4[0-9]{12}(?:[0-9]{3})?|[25][1-7][0-9]{14}|"
        r"6(?:011|5[0-9]{2})[0-9]{12}|3[47][0-9]{13}|"
        r"3(?:0[0-5]|[68][0-9])[0-9]{11})\b"
    ),
    "IP_ADDRESS": re.compile(
        r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}"
        r"(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b"
    ),
    "AWS_KEY": re.compile(r"\b(AKIA|ASIA|ABIA|ACCA)[0-9A-Z]{16}\b"),
}


def _scan_for_pii(
    content: str,
    entities: list[str],
) -> dict[str, list[str]]:
    """Scan content for PII matches.

    Args:
        content: Text to scan.
        entities: List of entity type names to check.

    Returns:
        Dict mapping entity type to list of matched strings.
    """
    found: dict[str, list[str]] = {}
    for entity in entities:
        pattern = _PII_PATTERNS.get(entity.upper())
        if pattern is None:
            continue
        matches = pattern.findall(content)
        if matches:
            found[entity.upper()] = matches
    return found


def _redact_pii(content: str, found: dict[str, list[str]]) -> str:
    """Replace PII matches in content with redaction tokens.

    Args:
        content: Original content.
        found: Dict of {entity_type: [matched_strings]}.

    Returns:
        Content with PII replaced by ``[REDACTED:<TYPE>]`` tokens.
    """
    result = content
    for entity, matches in found.items():
        for match in matches:
            result = result.replace(match, f"[REDACTED:{entity}]")
    return result


class PIIDetector(AbstractInputGuard):
    """Input guard that detects and optionally redacts PII.

    Args:
        action: ``"redact"`` (default), ``"block"``, or ``"warn"``.
        entities: List of PII entity types to detect.
                  Defaults to all supported types.

    Example::

        guard = PIIDetector(action="redact", entities=["EMAIL", "SSN"])
        result = await guard.check(user_message)
        safe_content = result.redacted_content or user_message
    """

    _DEFAULT_ENTITIES: list[str] = list(_PII_PATTERNS.keys())

    def __init__(
        self,
        action: str = "redact",
        entities: list[str] | None = None,
    ) -> None:
        """Initialise the PII detector.

        Args:
            action: Action when PII is found — ``"redact"``, ``"block"``, or ``"warn"``.
            entities: PII entity types to scan for.  Defaults to all types.
        """
        super().__init__(action=action)
        self._entities: list[str] = [
            e.upper() for e in (entities or self._DEFAULT_ENTITIES)
        ]

    async def check(
        self,
        content: str,
        *,
        messages: list[Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Result[GuardResultProtocol, GuardError]:
        """Scan content for PII and apply the configured action.

        Args:
            content: Input text to scan.
            messages: Unused — present for protocol compatibility.
            metadata: Optional metadata.

        Returns:
            PASS if no PII detected; otherwise the configured action result.
        """
        found = _scan_for_pii(content, self._entities)

        if not found:
            return Ok(GuardCheckResult.allow(self.name))

        entity_list = list(found.keys())

        if self._action == "block":
            return Ok(
                GuardCheckResult.block(
                    self.name,
                    reason=f"PII detected: {', '.join(entity_list)}",
                    detected_entities=entity_list,
                )
            )

        if self._action == "warn":
            return Ok(
                GuardCheckResult.warn(
                    self.name,
                    reason=f"PII present in input: {', '.join(entity_list)}",
                    detected_entities=entity_list,
                )
            )

        # Default: redact
        redacted = _redact_pii(content, found)
        return Ok(
            GuardCheckResult.redact(
                self.name,
                redacted_content=redacted,
                reason=f"PII redacted: {', '.join(entity_list)}",
                detected_entities=entity_list,
            )
        )


__all__ = ["PIIDetector"]
