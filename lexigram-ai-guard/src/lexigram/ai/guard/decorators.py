"""User-facing decorators for lexigram-ai-safety guard.

Applied by application developers when attaching safety guards to
LLM-calling functions. The decorator executes a real
:class:`~lexigram.ai.guard.pipeline.guard_pipeline.GuardPipeline` around
the wrapped coroutine: input is checked before the call, output after.
Blocked content raises ``GuardPipelineError``; redacted content is
forwarded to the wrapped call (input) or returned to the caller (output).
Guard evaluation errors are never swallowed.
"""

from __future__ import annotations

from collections.abc import Callable
import functools
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from lexigram.contracts.ai.guards import (
        GuardPipelineProtocol,
        InputGuardProtocol,
        OutputGuardProtocol,
    )

F = TypeVar("F", bound=Callable[..., Any])

__all__ = ["guarded"]


def _first_string_arg(args: tuple[Any, ...], kwargs: dict[str, Any]) -> str:
    """Return the first string-ish positional argument (or a kwarg)."""
    for arg in args:
        if isinstance(arg, str):
            return arg
    for value in kwargs.values():
        if isinstance(value, str):
            return value
    return ""


def _final_content(check_result: Any) -> str | None:
    """Extract the possibly-redacted final content from an aggregate result."""
    try:
        return str(getattr(check_result, "final_content", None) or "")
    except (TypeError, ValueError):
        return None


def guarded(
    input_guards: list[InputGuardProtocol] | None = None,
    output_guards: list[OutputGuardProtocol] | None = None,
    *,
    pipeline: GuardPipelineProtocol | None = None,
) -> Callable[[F], F]:
    """Apply input and/or output safety guards to the decorated async function.

    Builds a :class:`~lexigram.ai.guard.pipeline.guard_pipeline.GuardPipeline`
    from ``input_guards``/``output_guards`` (or uses the supplied ``pipeline``)
    and executes it around every call: ``check_input`` on the string content
    argument before the call, ``check_output`` on the string result after.
    A BLOCK raises :class:`~lexigram.ai.guard.exceptions.GuardPipelineError`;
    redacted content replaces the value passed to / returned by the wrapped
    function. Guard infrastructure errors propagate (fail-closed).

    Args:
        input_guards: Guards to evaluate against string inputs before calling.
        output_guards: Guards to evaluate against string output after calling.
        pipeline: Optional pre-built pipeline; overrides the guards arguments.

    Returns:
        A decorator that guards every invocation of the wrapped coroutine.

    Raises:
        GuardPipelineError: If an input or output guard blocks the content.

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
            from lexigram.ai.guard.exceptions import GuardPipelineError
            from lexigram.ai.guard.pipeline.guard_pipeline import GuardPipeline

            active: GuardPipelineProtocol = pipeline or GuardPipeline(  # type: ignore[assignment]
                input_guards=input_guards or [],
                output_guards=output_guards or [],
            )

            content = _first_string_arg(args, kwargs)
            if content:
                in_res = await active.check_input(content=content)
                if in_res.is_err():
                    raise GuardPipelineError(
                        f"Input guard failed: {in_res.unwrap_err()}"
                    ) from in_res.unwrap_err()
                agg = in_res.unwrap()
                if bool(getattr(agg, "blocked", False)):
                    blocking = getattr(agg, "blocking_result", None)
                    reason = (
                        getattr(blocking, "reason", None)
                        or "Input blocked by security guards"
                    )
                    raise GuardPipelineError(reason)
                redacted = _final_content(agg)
                if redacted:
                    args, kwargs = _replace_first_string(args, kwargs, redacted)

            result = await func(*args, **kwargs)

            out_text = result if isinstance(result, str) else None
            if out_text is not None:
                out_res = await active.check_output(
                    content=out_text, original_input=content or None
                )
                if out_res.is_err():
                    raise GuardPipelineError(
                        f"Output guard failed: {out_res.unwrap_err()}"
                    )
                out_agg = out_res.unwrap()
                if bool(getattr(out_agg, "blocked", False)):
                    blocking = getattr(out_agg, "blocking_result", None)
                    reason = (
                        getattr(blocking, "reason", None)
                        or "Output blocked by security guards"
                    )
                    raise GuardPipelineError(reason)
                final = _final_content(out_agg)
                if final is not None:
                    result = final

            return result

        wrapper._input_guards = input_guards or []  # type: ignore[attr-defined]
        wrapper._output_guards = output_guards or []  # type: ignore[attr-defined]
        return wrapper  # type: ignore[return-value]

    return decorator


def _replace_first_string(
    args: tuple[Any, ...], kwargs: dict[str, Any], replacement: str
) -> tuple[tuple[Any, ...], dict[str, Any]]:
    """Replace the first string positional arg (or kwarg) in a copy."""
    for i, arg in enumerate(args):
        if isinstance(arg, str):
            return (*args[:i], replacement, *args[i + 1 :]), kwargs
    new_kwargs = dict(kwargs)
    for key, value in kwargs.items():
        if isinstance(value, str):
            new_kwargs[key] = replacement
            break
    return args, new_kwargs
