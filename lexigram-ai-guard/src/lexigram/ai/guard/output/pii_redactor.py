"""PII redactor output guard.

Scans LLM responses for PII and redacts it before returning content to
or storing it.  Uses the same regex-based detection as the input
:class:`~lexigram.ai.guard.input.pii.PIIDetector`.

This guard always uses ``action="redact"`` — if you want to *block*
responses containing PII use a ``PIIDetector`` with ``action="block"``
as the output guard instead.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.ai.guard.input.pii import _PII_PATTERNS, _redact_pii, _scan_for_pii
from lexigram.ai.guard.output.base import AbstractOutputGuard
from lexigram.ai.guard.pipeline.result import GuardCheckResult
from lexigram.contracts.ai.guards import GuardResultProtocol
from lexigram.result import Ok, Result

if TYPE_CHECKING:
    from lexigram.contracts.ai.exceptions import GuardError


class PIIRedactor(AbstractOutputGuard):
    """Output guard that redacts PII from LLM responses.

    Args:
        entities: List of PII entity types to redact.
                  Defaults to all supported types.
        action: ``"redact"`` (default) or ``"block"`` (rejects any
                response containing PII rather than sanitising it).

    Example::

        guard = PIIRedactor(entities=["SSN", "CREDIT_CARD", "EMAIL"])
        result = await guard.check(llm_response)
        safe_response = result.final_content or llm_response
    """

    _DEFAULT_ENTITIES: list[str] = list(_PII_PATTERNS.keys())

    def __init__(
        self,
        entities: list[str] | None = None,
        action: str = "redact",
    ) -> None:
        """Initialise the PII redactor.

        Args:
            entities: PII types to redact.  Defaults to all types.
            action: ``"redact"`` or ``"block"``.
        """
        super().__init__(action=action)
        self._entities: list[str] = [
            e.upper() for e in (entities or self._DEFAULT_ENTITIES)
        ]

    async def check(
        self,
        content: str,
        *,
        original_input: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Result[GuardResultProtocol, GuardError]:
        """Scan LLM response for PII and apply the configured action.

        Args:
            content: LLM response text to scan.
            original_input: Unused — present for protocol compatibility.
            metadata: Optional metadata.

        Returns:
            PASS if no PII; REDACT with sanitised content or BLOCK otherwise.
        """
        found = _scan_for_pii(content, self._entities)

        if not found:
            return Ok(GuardCheckResult.allow(self.name))

        entity_list = list(found.keys())

        if self._action == "block":
            return Ok(
                GuardCheckResult.block(
                    self.name,
                    reason=f"LLM response contains PII: {', '.join(entity_list)}",
                    detected_entities=entity_list,
                )
            )

        redacted = _redact_pii(content, found)
        return Ok(
            GuardCheckResult.redact(
                self.name,
                redacted_content=redacted,
                reason=f"PII redacted from response: {', '.join(entity_list)}",
                detected_entities=entity_list,
            )
        )


__all__ = ["PIIRedactor"]
