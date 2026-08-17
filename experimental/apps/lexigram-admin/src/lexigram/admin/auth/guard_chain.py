"""AdminGuardChain — implements GuardChainProtocol for lexigram-admin."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.contracts.exceptions.security import GuardDeniedError
from lexigram.di.decorators import inject
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.contracts.web.guard import GuardProtocol

logger = get_logger(__name__)


@inject
class AdminGuardChain:
    """Executes a sequence of guards, short-circuiting on first denial.

    Implements GuardChainProtocol so it can be resolved from the container.

    Args:
        guards: Initial list of guards to add to the chain.
    """

    def __init__(self, guards: list[GuardProtocol] | None = None) -> None:
        self._guards: list[GuardProtocol] = list(guards or [])

    def add(self, guard: GuardProtocol) -> AdminGuardChain:
        """Add a guard to the chain (fluent API)."""
        self._guards.append(guard)
        return self

    async def execute(self, context: dict[str, Any]) -> None:
        """Execute all guards in order. Raises GuardDeniedError on first denial.

        Args:
            context: Arbitrary request context forwarded to each guard.

        Raises:
            GuardDeniedError: If any guard's can_activate returns False.
        """
        for guard in self._guards:
            allowed = await guard.can_activate(context)  # type: ignore[arg-type]
            if not allowed:
                guard_name = type(guard).__name__
                logger.warning("GuardProtocol %s denied access", guard_name)
                raise GuardDeniedError(
                    f"Access denied by guard: {guard_name}",
                )


__all__ = ["AdminGuardChain"]
