"""Resilience pipeline implementation."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, TypeVar, cast

from lexigram.logging import get_logger
from lexigram.primitives import clock as ambient_clock
from lexigram.resilience.bulkhead.limiter import Bulkhead, BulkheadConfig
from lexigram.resilience.circuit.breaker import CircuitBreaker, CircuitBreakerConfig
from lexigram.resilience.circuit.timeout import TimeoutConfig, timeout_context
from lexigram.resilience.retry import RetryConfig, RetryPolicy

logger = get_logger(__name__)

T = TypeVar("T")


class ResiliencePipeline:
    """Pipeline combining multiple resilience patterns."""

    def __init__(
        self,
        retry_config: RetryConfig | None = None,
        circuit_config: CircuitBreakerConfig | None = None,
        bulkhead_config: BulkheadConfig | None = None,
        timeout_config: TimeoutConfig | None = None,
        *,
        order: list[str] | tuple[str, ...] | None = None,
    ) -> None:
        """Initialize a resilience pipeline.

        Args:
            retry_config: Configuration for retry behaviour. When provided, a
                :class:`RetryPolicy` will be created and applied when
                ``execute`` is invoked.
            circuit_config: Configuration for the circuit breaker. When
                provided, a :class:`CircuitBreaker` will be created.
            bulkhead_config: Configuration for the bulkhead limiter. When
                provided, a :class:`Bulkhead` will be created.
            timeout_config: Optional timeout configuration. If set and the
                ``timeout`` step appears in ``order``, the wrapped function
                will execute within a :func:`timeout_context`.
            order: Optional sequence defining the execution order of the
                resilience steps. Valid names are ``"bulkhead"``,
                ``"circuit_breaker"``, ``"retry"`` and ``"timeout"``.
                The first element in the list is the outermost wrapper. If
                ``None`` (the default) the canonical order
                ``["bulkhead", "circuit_breaker", "retry", "timeout"]``
                is used. This parameter enables scenarios such as applying
                timeout *outside* of retries or placing the bulkhead at any
                position in the pipeline.
        """
        self.retry_policy = RetryPolicy(retry_config) if retry_config else None
        self.circuit_breaker = (
            CircuitBreaker(circuit_config) if circuit_config else None
        )
        self.bulkhead = Bulkhead(bulkhead_config) if bulkhead_config else None
        self.timeout_config = timeout_config

        # parse/validate execution order
        default = ["bulkhead", "circuit_breaker", "retry", "timeout"]
        if order is None:
            self.order = default
        else:
            self.order = list(order)
            valid = set(default)
            for step in self.order:
                if step not in valid:
                    raise ValueError(f"invalid resilience step: {step}")

    def add(self, pattern: Any) -> ResiliencePipeline:
        """Add a resilience pattern to the pipeline.

        Note: This is currently a type-hint compatibility method to satisfy
        the ResiliencePipelineProtocol. Parameters should ideally be
        set via constructor for full pipeline ordering.
        """
        # For now, we don't have a way to dynamically add patterns to the
        # already-ordered list without more refactoring.
        return self

    async def execute(
        self,
        func: Callable[..., Awaitable[T]],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """Execute function with all configured resilience patterns."""

        # start with the raw target invocation
        async def base() -> T:
            return await func(*args, **kwargs)

        current_func: Callable[..., Awaitable[T]] = base

        # build wrappers according to requested order; the loop runs in
        # reverse because we want the first element in ``self.order`` to be
        # the outermost wrapper.
        for step in reversed(self.order):
            if step == "timeout" and self.timeout_config:
                # wrap with timeout context
                inner = current_func
                timeout_cfg = self.timeout_config  # narrows to TimeoutConfig (not None)

                async def timeout_func(
                    _inner: Callable[..., Awaitable[T]] = inner,
                ) -> T:
                    async with timeout_context(timeout_cfg):
                        return await _inner()

                current_func = timeout_func

            elif step == "bulkhead" and self.bulkhead:
                bulkhead = self.bulkhead
                inner = current_func

                async def bulkhead_func(
                    _inner: Callable[..., Awaitable[T]] = inner,
                    _bulkhead: Bulkhead | None = bulkhead,
                ) -> T:
                    assert _bulkhead is not None  # noqa: S101  # closure default captures step arg
                    return cast("T", await _bulkhead.execute(_inner))

                current_func = bulkhead_func

            elif step == "circuit_breaker" and self.circuit_breaker:
                circuit = self.circuit_breaker
                inner = current_func

                async def circuit_func(
                    _inner: Callable[..., Awaitable[T]] = inner,
                    _circuit: CircuitBreaker | None = circuit,
                ) -> T:
                    assert _circuit is not None  # noqa: S101  # closure default captures step arg
                    return cast("T", await _circuit.execute(_inner))

                current_func = circuit_func

            elif step == "retry" and self.retry_policy:
                retry = self.retry_policy
                inner = current_func

                async def retry_func(
                    _inner: Callable[..., Awaitable[T]] = inner,
                    _retry: RetryPolicy | None = retry,
                ) -> T:
                    assert _retry is not None  # noqa: S101  # closure default captures step arg
                    return await _retry.execute(_inner)

                current_func = retry_func

        start = ambient_clock.monotonic()
        # record which patterns were enabled and the configured order
        patterns = dict.fromkeys(
            ["retry", "circuit_breaker", "bulkhead", "timeout"], False
        )
        if self.retry_policy:
            patterns["retry"] = True
        if self.circuit_breaker:
            patterns["circuit_breaker"] = True
        if self.bulkhead:
            patterns["bulkhead"] = True
        if self.timeout_config:
            patterns["timeout"] = True

        logger.debug(
            "Starting resilience pipeline execution",
            extra={"extra_data": {"order": self.order, **patterns}},
        )
        try:
            result = await current_func()
        except TimeoutError as e:
            from lexigram.resilience.exceptions import ResilienceTimeoutError

            raise ResilienceTimeoutError(
                f"Operation timed out after {self.timeout_config.timeout}s",  # type: ignore[union-attr]
            ) from e
        except Exception as e:
            duration = ambient_clock.monotonic() - start
            logger.exception(
                "Resilience pipeline execution failed",
                extra={
                    "extra_data": {
                        "duration": round(duration, 3),
                        "error": str(e),
                        **patterns,
                    },
                },
            )
            raise
        else:
            duration = ambient_clock.monotonic() - start
            logger.info(
                "Resilience pipeline execution succeeded",
                extra={"extra_data": {"duration": round(duration, 3), **patterns}},
            )
            return result


__all__ = [
    "ResiliencePipeline",
]
