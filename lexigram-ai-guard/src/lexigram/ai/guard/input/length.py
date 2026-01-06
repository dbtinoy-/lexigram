"""Input length guard.

Rejects or warns on inputs that exceed a configured character or token
budget.  This prevents prompt stuffing attacks and controls API costs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.ai.guard.input.base import AbstractInputGuard
from lexigram.ai.guard.pipeline.result import GuardCheckResult
from lexigram.contracts.ai.guards import GuardResultProtocol
from lexigram.result import Ok, Result

if TYPE_CHECKING:
    from lexigram.contracts.ai.exceptions import GuardError


class InputLengthGuard(AbstractInputGuard):
    """GuardProtocol that enforces a maximum input length.

    Length is measured in character count.  For a rough token
    estimate divide by 4 (GPT tokenizer average).

    Args:
        max_chars: Maximum allowed character count.
        action: Action when the limit is exceeded — ``"block"`` (default)
                or ``"warn"``.

    Example::

        guard = InputLengthGuard(max_chars=8000, action="block")
        result = await guard.check(user_input)
        if not result.passed:
            return Err(InputTooLongError(len(user_input)))
    """

    def __init__(self, max_chars: int, action: str = "block") -> None:
        """Initialise the length guard.

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
        messages: list[Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Result[GuardResultProtocol, GuardError]:
        """Check whether content exceeds the configured length limit.

        Args:
            content: Input text to measure.
            messages: Unused — present for protocol compatibility.
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
                    reason=f"Input length {length} chars exceeds soft limit {self._max_chars}",
                    char_count=length,
                    max_chars=self._max_chars,
                )
            )

        return Ok(
            GuardCheckResult.block(
                self.name,
                reason=f"Input length {length} chars exceeds maximum {self._max_chars}",
                char_count=length,
                max_chars=self._max_chars,
            )
        )


__all__ = ["InputLengthGuard"]
