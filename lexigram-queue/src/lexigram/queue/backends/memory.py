"""In-memory queue backend for development and testing."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from contextlib import nullcontext as _nullcontext
from dataclasses import replace
from typing import TYPE_CHECKING, Any

from lexigram.concurrency.task_utils import create_tracked_task
from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.contracts.observability.tracing import TracerProtocol
from lexigram.queue.hooks import MessageConsumedHook, MessagePublishedHook

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

    from lexigram.contracts.core import HookRegistryProtocol
    from lexigram.contracts.queue.types import BusMessage


class InMemoryQueue:
    """In-memory pub/sub queue implementation.

    Stores subscriptions and publishes messages to all subscribers
    of a topic using asyncio tasks. Suitable for development,
    testing, and single-process scenarios.
    """

    def __init__(self) -> None:
        """Initialize InMemoryQueue."""
        self._connected: bool = False
        self._subscribers: dict[
            str, list[Callable[[BusMessage], Coroutine[Any, Any, None]]]
        ] = defaultdict(list)
        self._tasks: set[asyncio.Task[Any]] = set()
        self._tracer: TracerProtocol | None = None
        self._hooks: HookRegistryProtocol | None = None

    def set_tracer(self, tracer: TracerProtocol | None) -> None:
        """Attach an optional tracer after provider boot wiring.

        Args:
            tracer: Tracer to attach, or None to clear.
        """
        self._tracer = tracer

    def set_hook_registry(self, hooks: HookRegistryProtocol | None) -> None:
        """Attach an optional hook registry after provider boot wiring."""
        self._hooks = hooks

    @staticmethod
    def _message_type(message: BusMessage) -> str:
        """Return the payload type label for lifecycle hooks."""
        return type(message.payload).__name__

    async def _emit_action(self, hook_name: str, payload: object) -> None:
        """Emit a queue action hook when a registry is available."""
        if self._hooks is None:
            return

        await self._hooks.call_action(hook_name, payload=payload)

    async def connect(self) -> None:
        """Establish connection (no-op for in-memory backend)."""
        self._connected = True

    async def close(self) -> None:
        """Close connection and clean up resources."""
        # Cancel all pending tasks
        for task in self._tasks:
            if not task.done():
                task.cancel()

        # Wait for cancellation to complete
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

        # Clear subscribers
        self._subscribers.clear()
        self._tasks.clear()
        self._connected = False

    async def publish(self, topic: str, message: BusMessage) -> BusMessage:
        """Publish a message to a topic.

        Injects W3C trace context into message headers when a tracer is configured.

        Args:
            topic: Destination topic.
            message: The message to publish.

        Returns:
            The message with injected headers (may be a new instance).
        """
        span = (
            self._tracer.start_span(
                f"queue.publish {topic}",
                attributes={
                    "messaging.destination": topic,
                    "messaging.system": "memory",
                },
            )
            if self._tracer
            else None
        )
        with span if span is not None else _nullcontext():
            trace_headers: dict[str, str] = {}
            if self._tracer and span:
                self._tracer.inject_context(trace_headers, context=span.context)  # type: ignore[attr-defined]

            merged_headers = {**(message.headers or {}), **trace_headers}
            message = replace(message, headers=merged_headers)

            handlers = self._subscribers.get(topic, [])
            for i, handler in enumerate(handlers):
                create_tracked_task(
                    handler(message),
                    self._tasks,
                    name=f"mem_queue_msg_{id(message)}_{i}",
                )

            await self._emit_action(
                "message.published",
                MessagePublishedHook(
                    queue_name=topic,
                    message_type=self._message_type(message),
                ),
            )

            return message

    async def subscribe(
        self,
        topic: str,
        handler: Callable[[BusMessage], Coroutine[Any, Any, None]],
    ) -> None:
        """Subscribe a handler to a topic.

        Wraps handler execution in a queue.receive span, extracting trace context
        from message headers when a tracer is configured.

        Args:
            topic: Topic to subscribe to.
            handler: Async callable invoked per message.
        """

        async def wrapped_handler(message: BusMessage) -> None:
            context = (
                self._tracer.extract_context(message.headers or {})
                if self._tracer
                else None
            )
            span = (
                self._tracer.start_span(
                    f"queue.receive {topic}",
                    attributes={
                        "messaging.destination": topic,
                        "messaging.system": "memory",
                    },
                    context=context,
                )
                if self._tracer
                else None
            )
            try:
                with span if span is not None else _nullcontext():
                    await handler(message)

                await self._emit_action(
                    "message.consumed",
                    MessageConsumedHook(
                        queue_name=topic,
                        message_type=self._message_type(message),
                    ),
                )
            except Exception as exc:
                if span:
                    span.record_exception(exc)
                    span.set_status("error")
                raise

        self._subscribers[topic].append(wrapped_handler)

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Check broker health.

        Args:
            timeout: Timeout in seconds (unused for in-memory backend).

        Returns:
            HealthCheckResult with HEALTHY if connected, UNHEALTHY otherwise.
        """
        status = HealthStatus.HEALTHY if self._connected else HealthStatus.UNHEALTHY
        return HealthCheckResult(
            component="queue",
            status=status,
            message="In-memory queue OK",
        )


__all__ = ["InMemoryQueue"]
