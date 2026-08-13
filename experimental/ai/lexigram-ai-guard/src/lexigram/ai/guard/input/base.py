"""Abstract base class for input guards."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lexigram.contracts.ai.exceptions import GuardError
    from lexigram.contracts.ai.guards import GuardResultProtocol
    from lexigram.result import Result


class AbstractInputGuard(ABC):
    """Base class for all input content guards.

    Subclasses implement :meth:`check` to evaluate a piece of input
    content and return a :class:`~lexigram.ai.guard.pipeline.result.GuardCheckResult`.

    Args:
        action: Default action to take when this guard triggers
                (``"block"``, ``"warn"``, or ``"redact"``).
                Not all guards support all actions.
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
        messages: list[Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Result[GuardResultProtocol, GuardError]:
        """Evaluate the content and return a result.

        Args:
            content: Raw text content to evaluate.
            messages: Optional structured message list for context.
            metadata: Optional metadata (user_id, model, etc.).

        Returns:
            Result indicating the outcome.
        """


__all__ = ["AbstractInputGuard"]
