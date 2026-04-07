"""User-facing decorators for lexigram-ai-safety guard.

Applied by application developers when attaching safety guards to
LLM-calling functions.
"""

from __future__ import annotations

from collections.abc import Callable
import functools
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from lexigram.contracts.ai.guards import InputGuardProtocol, OutputGuardProtocol

F = TypeVar("F", bound=Callable[..., Any])

__all__ = ["guarded"]


def guarded(
    input_guards: list[InputGuardProtocol] | None = None,
    output_guards: list[OutputGuardProtocol] | None = None,
) -> Callable[[F], F]:
    """Apply input and/or output safety guards to the decorated async function.

    Guards are attached as metadata on the wrapper. The actual guard pipeline
    execution is handled by the GuardPipelineProtocol implementation resolved
    from the container — this decorator is a marker/configuration mechanism.

    Args:
        input_guards: Guards to evaluate against string inputs before calling.
        output_guards: Guards to evaluate against string output after calling.

    Returns:
        A decorator that attaches guard metadata to the wrapped coroutine.

    Example:
        @guarded(
            input_guards=[PromptInjectionGuard()],
            output_guards=[PIIFilterGuard()],
        )
        async def chat(prompt: str) -> str: ...
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await func(*args, **kwargs)

        wrapper._input_guards = input_guards or []  # type: ignore[attr-defined]
        wrapper._output_guards = output_guards or []  # type: ignore[attr-defined]
        return wrapper  # type: ignore[return-value]

    return decorator
