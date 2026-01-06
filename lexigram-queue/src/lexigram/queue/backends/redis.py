"""Redis Pub/Sub queue backend."""

from __future__ import annotations

import asyncio
from contextlib import nullcontext as _nullcontext
from typing import TYPE_CHECKING, Any

from lexigram.concurrency.task_utils import create_tracked_task
from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.contracts.observability.tracing import TracerProtocol
from lexigram.logging import get_logger
from lexigram.queue.hooks import MessageConsumedHook, MessagePublishedHook
import lexigram.serialization as json

if TYPE_CHECKING:
    from lexigram.contracts.core import HookRegistryProtocol
    from lexigram.contracts.queue.types import BusMessage

logger = get_logger(__name__)


class RedisQueue:
    """Redis Pub/Sub queue backend.

    Requires: pip install lexigram-queue[redis]

    Attributes:
        _url: Redis connection URL.
        _max_connections: Maximum connection pool size.
        _client: Redis async client.
        _tasks: Set of background tasks for subscribers.
    """

    def __init__(
        self, url: str = "redis://localhost:6379/0", max_connections: int = 10
    ) -> None:
        """Initialize Redis queue.

        Args:
            url: Redis connection URL.
            max_connections: Maximum connection pool size.
        """
        self._url = url
        self._max_connections = max_connections
        self._client: Any = None
        self._tasks: set[asyncio.Task[None]] = set()
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
        """Establish connection to Redis."""
        try:
            import redis.asyncio as aioredis
        except ImportError as exc:
            raise ImportError(
                "redis[asyncio] required: pip install lexigram-queue[redis]"
            ) from exc
        self._client = aioredis.from_url(
            self._url, max_connections=self._max_connections
        )
        await self._client.ping()
        logger.info("redis_queue_connected", url=self._url)

    async def close(self) -> None:
        """Close connection and clean up resources."""
        for task in list(self._tasks):
            if not task.done():
                task.cancel()
        self._tasks.clear()
        if self._client:
            await self._client.aclose()
            self._client = None
        logger.info("redis_queue_closed")

    async def publish(self, topic: str, message: BusMessage) -> None:
        """Publish a message to a topic.

        Injects W3C trace context into message headers when a tracer is configured.

        Args:
            topic: Destination topic.
            message: Message to publish.

        Raises:
            RuntimeError: If not connected.
        """
        if self._client is None:
            raise RuntimeError("RedisQueue not connected")

        span = (
            self._tracer.start_span(
                f"queue.publish {topic}",
                attributes={
                    "messaging.destination": topic,
                    "messaging.system": "redis",
                },
            )
            if self._tracer
            else None
        )

        try:
            with span if span is not None else _nullcontext():
                trace_headers: dict[str, str] = {}
                if self._tracer and span:
                    self._tracer.inject_context(trace_headers, context=span.context)  # type: ignore[attr-defined]

                merged_headers = {**(message.headers or {}), **trace_headers}

                payload = json.dumps(
                    {
                        "id": message.id,
                        "topic": message.topic,
                        "payload": message.payload,
                        "headers": merged_headers,
                    }
                )

                await self._client.publish(topic, payload)
                await self._emit_action(
                    "message.published",
                    MessagePublishedHook(
                        queue_name=topic,
                        message_type=self._message_type(message),
                    ),
                )
        except Exception as exc:
            if span:
                span.record_exception(exc)
                span.set_status("error")
            raise

    async def subscribe(self, topic: str, handler: Any) -> None:
        """Subscribe a handler to a topic.

        Args:
            topic: Topic to subscribe to.
            handler: Async callable invoked per message.

        Raises:
            RuntimeError: If not connected.
        """
        if self._client is None:
            raise RuntimeError("RedisQueue not connected")
        pubsub = self._client.pubsub()
        await pubsub.subscribe(topic)

        async def _listen() -> None:
            async for raw in pubsub.listen():
                if raw["type"] == "message":
                    data = json.loads(raw["data"])
                    from lexigram.contracts.queue.types import BusMessage as BusMsg

                    record_headers: dict[str, str] = data.get("headers") or {}
                    msg = BusMsg(
                        topic=data.get("topic", topic),
                        payload=data.get("payload"),
                        headers=record_headers,
                    )
                    context = (
                        self._tracer.extract_context(record_headers)
                        if self._tracer
                        else None
                    )
                    span = (
                        self._tracer.start_span(
                            f"queue.receive {topic}",
                            attributes={
                                "messaging.destination": topic,
                                "messaging.system": "redis",
                            },
                            context=context,
                        )
                        if self._tracer
                        else None
                    )
                    try:
                        with span if span is not None else _nullcontext():
                            await handler(msg)

                        await self._emit_action(
                            "message.consumed",
                            MessageConsumedHook(
                                queue_name=topic,
                                message_type=self._message_type(msg),
                            ),
                        )
                    except Exception as exc:
                        if span:
                            span.record_exception(exc)
                            span.set_status("error")
                        raise

        task = create_tracked_task(
            _listen(), self._tasks, name=f"redis_queue_msg_{topic}"
        )
        logger.debug("redis_queue_subscribed", topic=topic)

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Check Redis connectivity.

        Args:
            timeout: Timeout in seconds (unused for Redis).

        Returns:
            HealthCheckResult with status.
        """
        if self._client is None:
            return HealthCheckResult(
                component="redis",
                status=HealthStatus.UNHEALTHY,
                details={"error": "not connected"},
            )
        try:
            await self._client.ping()
            return HealthCheckResult(
                component="redis",
                status=HealthStatus.HEALTHY,
                details={"url": self._url},
            )
        except OSError as exc:
            return HealthCheckResult(
                component="redis",
                status=HealthStatus.UNHEALTHY,
                details={"error": str(exc)},
            )


__all__ = ["RedisQueue"]
