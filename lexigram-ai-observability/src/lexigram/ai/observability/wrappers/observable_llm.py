"""Observability wrapper for LLM clients.

Wraps any :class:`~lexigram.contracts.ai.LLMClientProtocol` with tracing and metrics
so that every ``complete()`` / ``stream_chat()`` call is automatically
instrumented without touching individual provider implementations.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from lexigram.logging import (
    get_logger,
)

if TYPE_CHECKING:
    from lexigram.ai.observability.metrics import AIMetrics
    from lexigram.ai.observability.tracing import AITracer
    from lexigram.contracts.ai import LLMClientProtocol
    from lexigram.contracts.ai.governance import AIAuditStoreProtocol
    from lexigram.contracts.core import HealthCheckResult

logger = get_logger(__name__)

__all__ = ["ObservableLLMClient"]


class ObservableLLMClient:
    """Decorator that adds tracing and metrics to any LLMClientProtocol.

    Wraps the delegate client so callers interact with the same
    :class:`~lexigram.contracts.ai.LLMClientProtocol` protocol while every
    ``complete()`` and ``stream_chat()`` call is:

    - **Traced** via :class:`~lexigram.ai.observability.tracing.AITracer`
    - **Metered** via :class:`~lexigram.ai.observability.metrics.AIMetrics`

    Either dependency may be ``None`` (e.g. when the monitoring module is not
    installed), in which case the wrapper transparently delegates to the
    underlying client.

    Example:
        >>> from lexigram.ai.observability.observable_llm import ObservableLLMClient
        >>> client = ObservableLLMClient(raw_client, provider="openai",
        ...                              model="gpt-4o", tracer=tracer,
        ...                              metrics=metrics)
        >>> response = await client.complete(messages)
    """

    def __init__(
        self,
        delegate: LLMClientProtocol,
        *,
        provider: str,
        model: str,
        tracer: AITracer | None = None,
        metrics: AIMetrics | None = None,
        audit_store: AIAuditStoreProtocol | None = None,
    ) -> None:
        self._delegate = delegate
        self._provider = provider
        self._model = model
        self._tracer = tracer
        self._metrics = metrics
        self._audit_store = audit_store

    async def complete(self, messages: list[Any], **kwargs: Any) -> Any:
        """Complete with tracing and metrics."""
        labels = {"provider": self._provider, "model": self._model}
        start = time.perf_counter()

        if self._metrics:
            self._metrics.llm_active_requests.increment(labels=labels)
            self._metrics.llm_requests_total.increment(
                labels={**labels, "status": "started"}
            )

        try:
            if self._tracer:
                with self._tracer.trace_llm_call(self._provider, self._model):
                    result = await self._delegate.complete(messages, **kwargs)
            else:
                result = await self._delegate.complete(messages, **kwargs)
        except (
            Exception
        ) as e:  # observability wrapper must not interfere with LLM failures
            elapsed = time.perf_counter() - start
            logger.debug(
                "llm_infrastructure_error",
                provider=self._provider,
                model=self._model,
                error=str(e),
            )
            if self._metrics:
                self._metrics.llm_requests_total.increment(
                    labels={**labels, "status": "error"}
                )
            self._emit_audit(
                status="error",
                latency_ms=elapsed * 1000,
            )
            raise
        else:
            if result.is_err():
                elapsed = time.perf_counter() - start
                if self._metrics:
                    self._metrics.llm_requests_total.increment(
                        labels={**labels, "status": "error"}
                    )
                self._emit_audit(status="error", latency_ms=elapsed * 1000)
            else:
                completion = result.unwrap()
                if self._metrics:
                    self._metrics.llm_requests_total.increment(
                        labels={**labels, "status": "success"}
                    )
                    usage = getattr(completion, "usage", None)
                    if usage:
                        total_tokens = getattr(usage, "total_tokens", None)
                        if total_tokens:
                            self._metrics.llm_tokens_total.increment(
                                amount=total_tokens, labels=labels
                            )
                    cost = getattr(completion, "cost", None)
                    if cost:
                        self._metrics.llm_cost_dollars.increment(
                            amount=cost, labels=labels
                        )

                elapsed = time.perf_counter() - start
                usage = getattr(completion, "usage", None)
                tokens = getattr(usage, "total_tokens", None) if usage else None
                cost_val = getattr(completion, "cost", None)
                self._emit_audit(
                    status="success",
                    tokens=tokens,
                    cost=cost_val,
                    latency_ms=elapsed * 1000,
                )
            return result
        finally:
            elapsed = time.perf_counter() - start
            if self._metrics:
                self._metrics.llm_duration_seconds.observe(value=elapsed, labels=labels)
                self._metrics.llm_active_requests.decrement(labels=labels)

    def stream_chat(self, messages: list[Any], **kwargs: Any) -> Any:
        """Stream with tracing — returns ``AsyncStream`` directly.

        The stream is established lazily when iteration begins. Tracing
        context is captured synchronously and applied during iteration.
        """
        from lexigram.contracts.ai.exceptions import LLMError
        from lexigram.contracts.infra import AsyncStream

        # Get the delegate stream once — do not create duplicate streams
        delegate_stream = self._delegate.stream_chat(messages, **kwargs)

        async def _traced_stream() -> Any:
            """Async generator that applies tracing during stream iteration."""
            if self._tracer:
                with self._tracer.trace_llm_call(
                    self._provider, self._model, streaming=True
                ):
                    async for chunk in delegate_stream:
                        yield chunk
                    # Re-raise any stored error from the delegate stream
                    if delegate_stream.failed:
                        raise delegate_stream.error  # type: ignore[misc]
            else:
                async for chunk in delegate_stream:
                    yield chunk
                if delegate_stream.failed:
                    raise delegate_stream.error  # type: ignore[misc]

        # Return AsyncStream wrapping our traced generator
        # Preserve LLMError type through the wrapper
        return AsyncStream(
            _traced_stream(),
            error_adapter=lambda e: e if isinstance(e, LLMError) else LLMError(str(e)),
        )

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Delegate health check."""
        return await self._delegate.health_check(timeout=timeout)

    async def close(self) -> None:
        """Delegate close."""
        await self._delegate.close()

    def _emit_audit(
        self,
        *,
        status: str,
        tokens: int | None = None,
        cost: float | None = None,
        latency_ms: float | None = None,
    ) -> None:
        """Fire-and-forget audit event for an LLM call."""
        if self._audit_store is None:
            return

        from lexigram.contracts.ai.governance import AIAuditEvent, AuditEventType

        event = AIAuditEvent(
            event_type=AuditEventType.LLM_CALL,
            model=self._model,
            provider=self._provider,
            status=status,
            tokens=tokens,
            cost=cost,
            latency_ms=latency_ms,
        )

        import asyncio

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return

        task = loop.create_task(self._audit_store.record(event))
        self._background_tasks: set[asyncio.Task[object]] = getattr(
            self, "_background_tasks", set()
        )
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
