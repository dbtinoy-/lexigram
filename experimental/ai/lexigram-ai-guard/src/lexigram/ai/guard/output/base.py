"""Abstract base class for output guards."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lexigram.contracts.ai.exceptions import GuardError
    from lexigram.contracts.ai.guards import GuardResultProtocol
    from lexigram.result import Result


class AbstractOutputGuard(ABC):
    """Base class for all output content guards.

    Subclasses implement :meth:`check` to evaluate LLM response content
    and return a :class:`~lexigram.ai.guard.pipeline.result.GuardCheckResult`.

    Args:
        action: Default action to take when this guard triggers
                (``"block"``, ``"warn"``, or ``"redact"``).
    """

    def __init__(self, action: str = "block") -> None:
        """Initialise the guard with a default action.

        Args:
            action: Action taken when the guard triggers.
        """
        self._action = action

    @property
    def name(self) -> str:
        """GuardProtocol identifier derived from the class name."""
        return type(self).__name__

    @property
    def action(self) -> str:
        """Configured action for this guard."""
        return self._action

    @abstractmethod
    async def check(
        self,
        content: str,
        *,
        original_input: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Result[GuardResultProtocol, GuardError]:
        """Evaluate the LLM response and return a result.

        Args:
            content: LLM response text to evaluate.
            original_input: The original user input for context.
            metadata: Optional metadata (model, provider, etc.).

        Returns:
            Result indicating the outcome.
        """


__all__ = ["AbstractOutputGuard"]
