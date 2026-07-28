"""Apache Kafka queue backend."""

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


class KafkaQueue:
    """Apache Kafka queue backend.

    Requires: pip install lexigram-queue[kafka]

    Attributes:
        _bootstrap_servers: Kafka bootstrap servers.
        _client_id: Kafka client ID.
        _group_id: Consumer group ID.
        _auto_offset_reset: Consumer offset reset strategy.
        _max_in_flight: Backpressure limit for concurrent in-flight messages.
        _producer: Kafka async producer.
        _consumer: Kafka async consumer.
        _tasks: Set of background consumer tasks.
        _tracer: Optional tracer for W3C distributed trace propagation.
    """

    def __init__(
        self,
        bootstrap_servers: str = "localhost:9092",
        client_id: str = "lexigram",
        group_id: str = "lexigram-consumers",
        auto_offset_reset: str = "latest",
        max_in_flight: int = 100,
        tracer: TracerProtocol | None = None,
    ) -> None:
        """Initialize Kafka queue.

        Args:
            bootstrap_servers: Kafka bootstrap servers.
            client_id: Kafka client ID.
            group_id: Consumer group ID.
            auto_offset_reset: Consumer offset reset strategy.
            max_in_flight: Maximum concurrent in-flight messages before backpressure kicks in.
            tracer: Optional tracer for distributed tracing (W3C traceparent propagation).
        """
        self._bootstrap_servers = bootstrap_servers
        self._client_id = client_id
        self._group_id = group_id
        self._auto_offset_reset = auto_offset_reset
        self._max_in_flight = max_in_flight
        self._tracer = tracer
        self._producer: Any = None
        self._consumer: Any = None
        self._tasks: set[asyncio.Task[None]] = set()
        self._in_flight: int = 0
        self._paused: bool = False
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
        """Establish connection to Kafka."""
        try:
            from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
        except ImportError as exc:
            raise ImportError(
                "aiokafka required: pip install lexigram-queue[kafka]"
            ) from exc

        self._producer = AIOKafkaProducer(
            bootstrap_servers=self._bootstrap_servers,
            client_id=self._client_id,
        )
        await self._producer.start()

        self._consumer = AIOKafkaConsumer(
            bootstrap_servers=self._bootstrap_servers,
            client_id=self._client_id,
            group_id=self._group_id,
            auto_offset_reset=self._auto_offset_reset,
        )
        await self._consumer.start()

        logger.info(
            "kafka_queue_connected",
            bootstrap_servers=self._bootstrap_servers,
            group_id=self._group_id,
        )

    async def close(self) -> None:
        """Close connection and clean up resources."""
        for task in list(self._tasks):
            if not task.done():
                task.cancel()
        self._tasks.clear()

        if self._producer:
            await self._producer.stop()
            self._producer = None
        if self._consumer:
            await self._consumer.stop()
            self._consumer = None
        logger.info("kafka_queue_closed")

    async def publish(self, topic: str, message: BusMessage) -> None:
        """Publish a message to a topic.

        Injects W3C trace context into message headers when a tracer is configured.

        Args:
            topic: Destination topic.
            message: Message to publish.

        Raises:
            RuntimeError: If not connected.
        """
        if not self._producer:
            raise RuntimeError("KafkaQueue not connected")

        span = (
            self._tracer.start_span(
                f"queue.publish {topic}",
                attributes={
                    "messaging.destination": topic,
                    "messaging.system": "kafka",
                },
            )
            if self._tracer
            else None
        )

        try:
            with span if span is not None else _nullcontext():
                # Inject W3C trace context from the publish span
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

                await self._producer.send_and_wait(
                    topic,
                    value=payload,
                    headers=[
                        (k, v.encode() if isinstance(v, str) else v)
                        for k, v in merged_headers.items()
                    ],
                )
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

        Extracts W3C trace context from message headers when a tracer is configured.
        Applies backpressure if ``max_in_flight`` is reached.

        Args:
            topic: Topic to subscribe to.
            handler: Async callable invoked per message.

        Raises:
            RuntimeError: If not connected.
        """
        if not self._consumer:
            raise RuntimeError("KafkaQueue not connected")

        self._consumer.subscribe([topic])

        async def _handle_record(data: dict[str, Any]) -> None:
            from lexigram.contracts.queue.types import BusMessage as BusMsg

            # Extract W3C trace context from message headers
            record_headers = data.get("headers") or {}
            msg = BusMsg(
                topic=data.get("topic", topic),
                payload=data.get("payload"),
                headers=record_headers,
            )
            span = None
            if self._tracer and isinstance(record_headers, dict):
                extracted_context = self._tracer.extract_context(record_headers)
                span = self._tracer.start_span(
                    f"queue.receive {topic}",
                    attributes={
                        "messaging.destination": topic,
                        "messaging.system": "kafka",
                    },
                    context=extracted_context,
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
            finally:
                self._decrement_in_flight()

        async def _listen() -> None:
            async for record in self._consumer:
                # Backpressure: pause when at limit, resume when below
                if self._in_flight >= self._max_in_flight:
                    logger.warning(
                        "kafka_backpressure_applied",
                        in_flight=self._in_flight,
                        limit=self._max_in_flight,
                    )
                    await self._consumer.pause(self._consumer.assignment())
                    self._paused = True
                    while self._in_flight >= self._max_in_flight:
                        await asyncio.sleep(0.1)
                    await self._consumer.resume(self._consumer.assignment())
                    self._paused = False

                data = json.loads(record.value.decode())
                if record.headers:
                    data["headers"] = {
                        key: value.decode()
                        for key, value in record.headers
                        if value is not None
                    }
                self._in_flight += 1
                create_tracked_task(
                    _handle_record(data),
                    self._tasks,
                    name=f"kafka_handle_{topic}",
                )
                # _decrement_in_flight() is called inside _handle_record's finally block

        create_tracked_task(_listen(), self._tasks, name=f"kafka_listen_{topic}")
        logger.debug("kafka_queue_subscribed", topic=topic)

    def _decrement_in_flight(self) -> None:
        """Decrement the in-flight counter (floor 0)."""
        self._in_flight = max(0, self._in_flight - 1)

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Check Kafka connectivity.

        Args:
            timeout: Timeout in seconds (unused for Kafka).

        Returns:
            HealthCheckResult with status.
        """
        if not self._producer or not self._consumer:
            return HealthCheckResult(
                component="queue.kafka",
                status=HealthStatus.UNHEALTHY,
                details={"error": "not connected"},
            )
        try:
            # Check if producer is still alive
            if self._producer._closed:
                return HealthCheckResult(
                    component="queue.kafka",
                    status=HealthStatus.UNHEALTHY,
                    details={"error": "producer closed"},
                )
            return HealthCheckResult(
                component="queue.kafka",
                status=HealthStatus.HEALTHY,
                details={"bootstrap_servers": self._bootstrap_servers},
            )
        except Exception as exc:  # noqa: BLE001 — best-effort
            return HealthCheckResult(
                component="queue.kafka",
                status=HealthStatus.UNHEALTHY,
                details={"error": str(exc)},
            )


__all__ = ["KafkaQueue"]
