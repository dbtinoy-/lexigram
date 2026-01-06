"""Output length guard.

Rejects LLM responses that exceed a configured maximum length.
Used to prevent runaway generation and enforce SLA constraints.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.ai.guard.output.base import AbstractOutputGuard
from lexigram.ai.guard.pipeline.result import GuardCheckResult
from lexigram.contracts.ai.guards import GuardResultProtocol
from lexigram.result import Ok, Result

if TYPE_CHECKING:
    from lexigram.contracts.ai.exceptions import GuardError


class OutputLengthGuard(AbstractOutputGuard):
    """GuardProtocol that enforces a maximum LLM response length.

    Args:
        max_chars: Maximum allowed character count in the response.
        action: Action when the limit is exceeded — ``"block"`` (default)
                or ``"warn"``.

    Example::

        guard = OutputLengthGuard(max_chars=50000, action="warn")
        result = await guard.check(llm_response)
    """

    def __init__(self, max_chars: int, action: str = "block") -> None:
        """Initialise the output length guard.

        Args:
            max_chars: Maximum allowed character count.
            action: ``"block"`` or ``"warn"``.
        """
        super().__init__(action=action)
        self._max_chars = max_chars

    async def check(
        self,
        content: str,
        *,
        original_input: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Result[GuardResultProtocol, GuardError]:
        """Check whether the response exceeds the configured length.

        Args:
            content: LLM response text to measure.
            original_input: Unused — present for protocol compatibility.
            metadata: Optional metadata.

        Returns:
            PASS if within limit; BLOCK or WARN if exceeded.
        """
        length = len(content)
        if length <= self._max_chars:
            return Ok(GuardCheckResult.allow(self.name, char_count=length))

        if self._action == "warn":
            return Ok(
                GuardCheckResult.warn(
                    self.name,
                    reason=f"Response length {length} chars exceeds soft limit {self._max_chars}",
                    char_count=length,
                    max_chars=self._max_chars,
                )
            )

        return Ok(
            GuardCheckResult.block(
                self.name,
                reason=f"Response length {length} chars exceeds maximum {self._max_chars}",
                char_count=length,
                max_chars=self._max_chars,
            )
        )


__all__ = ["OutputLengthGuard"]
