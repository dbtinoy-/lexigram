"""AWS SQS queue backend."""

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


class SQSQueue:
    """AWS SQS queue backend.

    Requires: pip install lexigram-queue[sqs]

    Attributes:
        _region: AWS region.
        _queue_url: SQS queue URL.
        _visibility_timeout: Message visibility timeout in seconds.
        _max_in_flight: Backpressure limit for concurrent in-flight messages.
        _client: Async SQS client.
        _tasks: Set of background polling tasks.
        _tracer: Optional tracer for W3C distributed trace propagation.
    """

    def __init__(
        self,
        region: str = "us-east-1",
        queue_url: str = "",
        visibility_timeout: int = 30,
        max_in_flight: int = 100,
        tracer: TracerProtocol | None = None,
    ) -> None:
        """Initialize SQS queue.

        Args:
            region: AWS region.
            queue_url: SQS queue URL.
            visibility_timeout: Message visibility timeout in seconds.
            max_in_flight: Maximum concurrent in-flight messages before backpressure kicks in.
            tracer: Optional tracer for distributed tracing (W3C traceparent propagation).
        """
        self._region = region
        self._queue_url = queue_url
        self._visibility_timeout = visibility_timeout
        self._max_in_flight = max_in_flight
        self._tracer = tracer
        self._client: Any = None
        self._tasks: set[asyncio.Task[None]] = set()
        self._in_flight: int = 0
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
        """Establish connection to SQS."""
        try:
            import aiobotocore.session  # type: ignore[import-not-found]
        except ImportError as exc:
            raise ImportError(
                "aiobotocore required: pip install lexigram-queue[sqs]"
            ) from exc

        session = aiobotocore.session.get_session()
        self._client = session.client("sqs", region_name=self._region)
        logger.info(
            "sqs_queue_connected", region=self._region, queue_url=self._queue_url
        )

    async def close(self) -> None:
        """Close connection and clean up resources."""
        for task in list(self._tasks):
            if not task.done():
                task.cancel()
        self._tasks.clear()

        if self._client:
            await self._client.__aexit__(None, None, None)
            self._client = None
        logger.info("sqs_queue_closed")

    async def publish(self, topic: str, message: BusMessage) -> None:
        """Publish a message to a topic (SQS queue).

        Injects W3C trace context into the message body headers when a tracer
        is configured.

        Args:
            topic: Destination queue name (ignored; uses configured queue_url).
            message: Message to publish.

        Raises:
            RuntimeError: If not connected.
        """
        if not self._client:
            raise RuntimeError("SQSQueue not connected")

        span = (
            self._tracer.start_span(
                f"queue.publish {topic}",
                attributes={"messaging.destination": topic, "messaging.system": "sqs"},
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

                async with self._client as client:
                    await client.send_message(
                        QueueUrl=self._queue_url, MessageBody=payload
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

    def _decrement_in_flight(self) -> None:
        """Decrement the in-flight counter (floor 0)."""
        self._in_flight = max(0, self._in_flight - 1)

    async def subscribe(self, topic: str, handler: Any) -> None:
        """Subscribe a handler to receive messages from the queue.

        Extracts W3C trace context from message body headers when a tracer is
        configured.  Applies backpressure by limiting ``MaxNumberOfMessages``
        to the remaining capacity below ``max_in_flight``.

        Args:
            topic: Topic (unused for SQS; uses configured queue_url).
            handler: Async callable invoked per message.

        Raises:
            RuntimeError: If not connected.
        """
        if not self._client:
            raise RuntimeError("SQSQueue not connected")

        async def _handle_message(raw_msg: dict[str, Any]) -> None:
            data = json.loads(raw_msg["Body"])
            from lexigram.contracts.queue.types import BusMessage as BusMsg

            # Extract W3C trace context from message headers stored in body
            record_headers: dict[str, str] = data.get("headers") or {}
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
                        "messaging.system": "sqs",
                    },
                    context=extracted_context,
                )

            try:
                with span if span is not None else _nullcontext():
                    await handler(msg)
                    async with self._client as client:
                        await client.delete_message(
                            QueueUrl=self._queue_url,
                            ReceiptHandle=raw_msg["ReceiptHandle"],
                        )

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

        async def _poll() -> None:
            while True:
                try:
                    # Backpressure: only fetch as many messages as capacity allows
                    capacity = max(0, self._max_in_flight - self._in_flight)
                    if capacity == 0:
                        logger.warning(
                            "sqs_backpressure_applied",
                            in_flight=self._in_flight,
                            limit=self._max_in_flight,
                        )
                        await asyncio.sleep(0.5)
                        continue

                    batch = min(capacity, 10)  # SQS max is 10 per request
                    async with self._client as client:
                        response = await client.receive_message(
                            QueueUrl=self._queue_url,
                            MaxNumberOfMessages=batch,
                            VisibilityTimeout=self._visibility_timeout,
                            WaitTimeSeconds=20,
                        )
                        messages = response.get("Messages", [])
                        for raw_msg in messages:
                            self._in_flight += 1
                            create_tracked_task(
                                _handle_message(raw_msg),
                                self._tasks,
                                name="sqs_handle_message",
                            )
                            # _decrement_in_flight() is called inside _handle_message's finally block
                except asyncio.CancelledError:
                    break
                except Exception as exc:  # noqa: BLE001 — resilience boundary
                    logger.error("sqs_queue_poll_error", error=str(exc))
                    await asyncio.sleep(5)

        create_tracked_task(_poll(), self._tasks, name="sqs_queue_poll")
        logger.debug("sqs_queue_subscribed", queue_url=self._queue_url)

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Check SQS connectivity.

        Args:
            timeout: Timeout in seconds.

        Returns:
            HealthCheckResult with status.
        """
        if not self._client:
            return HealthCheckResult(
                component="queue.sqs",
                status=HealthStatus.UNHEALTHY,
                details={"error": "not connected"},
            )
        try:
            async with self._client as client:
                await client.get_queue_attributes(
                    QueueUrl=self._queue_url,
                    AttributeNames=["ApproximateNumberOfMessages"],
                )
            return HealthCheckResult(
                component="queue.sqs",
                status=HealthStatus.HEALTHY,
                details={"region": self._region, "queue_url": self._queue_url},
            )
        except Exception as exc:  # noqa: BLE001 — best-effort
            return HealthCheckResult(
                component="queue.sqs",
                status=HealthStatus.UNHEALTHY,
                details={"error": str(exc)},
            )
