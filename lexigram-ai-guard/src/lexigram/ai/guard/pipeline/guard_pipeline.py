"""GuardProtocol pipeline — orchestrates input and output guards.

The pipeline runs guards in registration order. For input guards it
applies them sequentially to the request content; for output guards it
applies them to the LLM response.  Any BLOCK result stops further
evaluation and returns immediately.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeAlias

from lexigram.ai.guard.pipeline.result import (
    AggregateGuardResult,
    GuardAction,
)
from lexigram.contracts.ai.exceptions import GuardError
from lexigram.contracts.ai.guards import GuardResultProtocol
from lexigram.logging import (
    get_logger,
)
from lexigram.result import Err, Ok, Result

if TYPE_CHECKING:
    from lexigram.contracts.ai.guards import InputGuardProtocol, OutputGuardProtocol

logger = get_logger(__name__)

GuardResult: TypeAlias = Result[GuardResultProtocol, GuardError]
GuardResultOrException: TypeAlias = GuardResult | BaseException


class GuardPipeline:
    """Ordered chain of input and output guards.

    Guards are evaluated in order.  For input, content flows through
    each guard; if a guard redacts content, the redacted version is
    passed to subsequent guards.  A BLOCK stops evaluation immediately.

    Args:
        input_guards: Guards to run on user inputs before sending to LLM.
        output_guards: Guards to run on LLM outputs before returning to caller.

    Example::

        pipeline = GuardPipeline(
            input_guards=[
                PromptInjectionDetector(action="block"),
                PIIDetector(action="redact"),
            ],
            output_guards=[
                PIIRedactor(entities=["SSN", "CREDIT_CARD"]),
                LengthGuard(max_chars=10000, action="block"),
            ],
        )

        result = await pipeline.check_input(user_message)
        if result.blocked:
            return Err(GuardViolationError(result))
        safe_input = result.final_content or user_message
    """

    def __init__(
        self,
        input_guards: list[InputGuardProtocol] | None = None,
        output_guards: list[OutputGuardProtocol] | None = None,
    ) -> None:
        """Initialise the guard pipeline.

        Args:
            input_guards: Ordered list of input guards to apply.
            output_guards: Ordered list of output guards to apply.
        """
        self._input_guards: list[InputGuardProtocol] = input_guards or []
        self._output_guards: list[OutputGuardProtocol] = output_guards or []

    def add_input_guard(self, guard: InputGuardProtocol) -> None:
        """Append an input guard to the pipeline.

        Args:
            guard: GuardProtocol to add.
        """
        self._input_guards.append(guard)

    def add_output_guard(self, guard: OutputGuardProtocol) -> None:
        """Append an output guard to the pipeline.

        Args:
            guard: GuardProtocol to add.
        """
        self._output_guards.append(guard)

    async def check_input(
        self,
        content: str,
        *,
        messages: list[Any] | None = None,
        metadata: dict[str, Any] | None = None,
        parallel: bool = False,
    ) -> Result[AggregateGuardResult, GuardError]:
        """Run all input guards against the content.

        Guards are applied in order.  Redacted content is forwarded to
        subsequent guards.  A BLOCK terminates evaluation immediately.
        If `parallel` is True, all guards are run concurrently and redaction
        chaining is disabled (each operates on the original content).

        Args:
            content: Raw input text to evaluate.
            messages: Optional structured message list for context.
            metadata: Optional request metadata (user_id, model, etc.).
            parallel: Whether to run guards concurrently with asyncio.gather.

        Returns:
            Ok(AggregateGuardResult) combining all individual guard outcomes,
            or Err(GuardError) if a guard fails unexpectedly.
        """
        if not self._input_guards:
            return Ok(
                AggregateGuardResult(
                    passed=True,
                    action=GuardAction.PASS,
                    results=[],
                    final_content=content,
                )
            )

        results: list[GuardResultProtocol] = []
        current_content = content

        if parallel:
            import asyncio

            coros = [
                guard.check(content, messages=messages, metadata=metadata)
                for guard in self._input_guards
            ]
            check_results: list[GuardResultOrException] = await asyncio.gather(
                *coros, return_exceptions=True
            )

            for _guard, check_result in zip(
                self._input_guards, check_results, strict=False
            ):
                if isinstance(check_result, BaseException):
                    return Err(
                        GuardError(f"Guard failed: {check_result}", cause=check_result)
                    )

                if check_result.is_err():
                    return Err(check_result.unwrap_err())

                res = check_result.unwrap()
                results.append(res)
                logger.debug(
                    "input_guard_evaluated_parallel",
                    guard=res.guard_name,
                    action=res.action,
                )

                if res.action == GuardAction.BLOCK:
                    logger.info(
                        "input_guard_blocked",
                        guard=res.guard_name,
                        reason=res.details.get("reason", ""),
                    )
                    return Ok(
                        AggregateGuardResult(
                            passed=False,
                            action=GuardAction.BLOCK,
                            results=results,
                            final_content=None,
                        )
                    )

            return Ok(AggregateGuardResult.from_results(results, content))

        for guard in self._input_guards:
            guard_result = await guard.check(
                current_content,
                messages=messages,
                metadata=metadata,
            )

            if guard_result.is_err():
                return Err(guard_result.unwrap_err())

            res = guard_result.unwrap()
            results.append(res)
            logger.debug(
                "input_guard_evaluated",
                guard=res.guard_name,
                action=res.action,
            )

            if res.action == GuardAction.BLOCK:
                logger.info(
                    "input_guard_blocked",
                    guard=res.guard_name,
                    reason=res.details.get("reason", ""),
                )
                return Ok(
                    AggregateGuardResult(
                        passed=False,
                        action=GuardAction.BLOCK,
                        results=results,
                        final_content=None,
                    )
                )

            if res.action == GuardAction.REDACT and res.redacted_content is not None:
                current_content = res.redacted_content

        return Ok(AggregateGuardResult.from_results(results, current_content))

    async def check_output(
        self,
        content: str,
        *,
        original_input: str | None = None,
        metadata: dict[str, Any] | None = None,
        parallel: bool = False,
    ) -> Result[AggregateGuardResult, GuardError]:
        """Run all output guards against the LLM response.

        Args:
            content: LLM response text to evaluate.
            original_input: The original user input for context.
            metadata: Optional request metadata (model, provider, etc.).
            parallel: Whether to run guards concurrently.

        Returns:
            Ok(AggregateGuardResult) combining all individual guard outcomes.
        """
        if not self._output_guards:
            return Ok(
                AggregateGuardResult(
                    passed=True,
                    action=GuardAction.PASS,
                    results=[],
                    final_content=content,
                )
            )

        results: list[GuardResultProtocol] = []
        current_content = content

        if parallel:
            import asyncio

            coros = [
                guard.check(content, original_input=original_input, metadata=metadata)
                for guard in self._output_guards
            ]
            check_results: list[GuardResultOrException] = await asyncio.gather(
                *coros, return_exceptions=True
            )

            for _guard, check_result in zip(
                self._output_guards, check_results, strict=False
            ):
                if isinstance(check_result, BaseException):
                    return Err(
                        GuardError(f"Guard failed: {check_result}", cause=check_result)
                    )

                if check_result.is_err():
                    return Err(check_result.unwrap_err())

                res = check_result.unwrap()
                results.append(res)
                logger.debug(
                    "output_guard_evaluated_parallel",
                    guard=res.guard_name,
                    action=res.action,
                )

                if res.action == GuardAction.BLOCK:
                    logger.info(
                        "output_guard_blocked",
                        guard=res.guard_name,
                        reason=res.details.get("reason", ""),
                    )
                    return Ok(
                        AggregateGuardResult(
                            passed=False,
                            action=GuardAction.BLOCK,
                            results=results,
                            final_content=None,
                        )
                    )

            return Ok(AggregateGuardResult.from_results(results, content))

        for guard in self._output_guards:
            guard_result = await guard.check(
                current_content,
                original_input=original_input,
                metadata=metadata,
            )
            if guard_result.is_err():
                return Err(guard_result.unwrap_err())

            res = guard_result.unwrap()
            results.append(res)
            logger.debug(
                "output_guard_evaluated",
                guard=res.guard_name,
                action=res.action,
            )

            if res.action == GuardAction.BLOCK:
                logger.info(
                    "output_guard_blocked",
                    guard=res.guard_name,
                    reason=res.details.get("reason", ""),
                )
                return Ok(
                    AggregateGuardResult(
                        passed=False,
                        action=GuardAction.BLOCK,
                        results=results,
                        final_content=None,
                    )
                )

            if res.action == GuardAction.REDACT and res.redacted_content is not None:
                current_content = res.redacted_content

        return Ok(AggregateGuardResult.from_results(results, current_content))


__all__ = ["GuardPipeline"]
