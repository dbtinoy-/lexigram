"""RabbitMQ queue backend."""

from __future__ import annotations

from contextlib import nullcontext as _nullcontext
from typing import TYPE_CHECKING, Any

from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.contracts.observability.tracing import TracerProtocol
from lexigram.logging import get_logger
from lexigram.queue.hooks import MessageConsumedHook, MessagePublishedHook
import lexigram.serialization as json

if TYPE_CHECKING:
    from lexigram.contracts.core import HookRegistryProtocol
    from lexigram.contracts.queue.types import BusMessage

logger = get_logger(__name__)


class RabbitMQQueue:
    """RabbitMQ queue backend.

    Requires: pip install lexigram-queue[rabbitmq]

    Attributes:
        _url: RabbitMQ connection URL.
        _exchange: Exchange name.
        _prefetch_count: Consumer prefetch count.
        _connection: RabbitMQ async connection.
    """

    def __init__(
        self,
        url: str = "amqp://guest:guest@localhost/",
        exchange: str = "lexigram",
        prefetch_count: int = 10,
    ) -> None:
        """Initialize RabbitMQ queue.

        Args:
            url: RabbitMQ connection URL.
            exchange: Exchange name.
            prefetch_count: Consumer prefetch count.
        """
        self._url = url
        self._exchange = exchange
        self._prefetch_count = prefetch_count
        self._connection: Any = None
        self._channel: Any = None
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
        """Establish connection to RabbitMQ."""
        try:
            import aio_pika
        except ImportError as exc:
            raise ImportError(
                "aio_pika required: pip install lexigram-queue[rabbitmq]"
            ) from exc

        self._connection = await aio_pika.connect_robust(self._url)
        self._channel = await self._connection.channel()
        await self._channel.set_qos(prefetch_count=self._prefetch_count)
        logger.info("rabbitmq_queue_connected", url=self._url, exchange=self._exchange)

    async def close(self) -> None:
        """Close connection and clean up resources."""
        if self._connection:
            await self._connection.close()
            self._connection = None
            self._channel = None
        logger.info("rabbitmq_queue_closed")

    async def publish(self, topic: str, message: BusMessage) -> None:
        """Publish a message to a topic.

        Injects W3C trace context into message headers when a tracer is configured.

        Args:
            topic: Destination topic (routing key).
            message: Message to publish.

        Raises:
            RuntimeError: If not connected.
        """
        if not self._channel:
            raise RuntimeError("RabbitMQQueue not connected")

        from aio_pika import Message

        span = (
            self._tracer.start_span(
                f"queue.publish {topic}",
                attributes={
                    "messaging.destination": topic,
                    "messaging.system": "rabbitmq",
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

                exchange = await self._channel.get_exchange(self._exchange)
                msg = Message(payload)
                await exchange.publish(msg, routing_key=topic)
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
            topic: Topic (queue name) to subscribe to.
            handler: Async callable invoked per message.

        Raises:
            RuntimeError: If not connected.
        """
        if not self._channel:
            raise RuntimeError("RabbitMQQueue not connected")

        queue = await self._channel.declare_queue(topic, durable=True)

        async def _on_message(raw_message: Any) -> None:
            msg: BusMessage | None = None

            async with raw_message.process():
                data = json.loads(raw_message.body.decode())
                from lexigram.contracts.queue.types import BusMessage as BusMsg

                record_headers: dict[str, str] = data.get("headers") or {}
                msg = BusMsg(
                    id=data.get("id", ""),
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
                            "messaging.system": "rabbitmq",
                        },
                        context=context,
                    )
                    if self._tracer
                    else None
                )
                try:
                    with span if span is not None else _nullcontext():
                        await handler(msg)
                except Exception as exc:
                    if span:
                        span.record_exception(exc)
                        span.set_status("error")
                    raise

            if msg is not None:
                await self._emit_action(
                    "message.consumed",
                    MessageConsumedHook(
                        queue_name=topic,
                        message_type=self._message_type(msg),
                    ),
                )

        await queue.consume(_on_message)
        logger.debug("rabbitmq_queue_subscribed", topic=topic)

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Check RabbitMQ connectivity.

        Args:
            timeout: Timeout in seconds (unused for RabbitMQ).

        Returns:
            HealthCheckResult with status.
        """
        if not self._connection:
            return HealthCheckResult(
                component="rabbitmq",
                status=HealthStatus.UNHEALTHY,
                details={"error": "not connected"},
            )
        try:
            if self._connection.is_closed:
                return HealthCheckResult(
                    component="rabbitmq",
                    status=HealthStatus.UNHEALTHY,
                    details={"error": "connection closed"},
                )
            return HealthCheckResult(
                component="rabbitmq",
                status=HealthStatus.HEALTHY,
                details={"url": self._url},
            )
        except Exception as exc:  # noqa: BLE001 — best-effort
            return HealthCheckResult(
                component="rabbitmq",
                status=HealthStatus.UNHEALTHY,
                details={"error": str(exc)},
            )
