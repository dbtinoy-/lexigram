"""Azure Service Bus queue backend."""

from __future__ import annotations

import asyncio
from contextlib import nullcontext as _nullcontext
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID

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


class AzureServiceBusQueue:
    """Azure Service Bus queue backend.

    Requires: pip install lexigram-queue[azure]

    Establishes one long-lived ``ServiceBusClient`` context during
    ``connect()``.  Each ``publish()`` call uses a short-lived sender
    context; the background poll loop uses a short-lived receiver context
    per batch so ``complete_message`` / ``abandon_message`` are always
    called while that receiver is still open.

    Attributes:
        _connection_str: Azure Service Bus connection string.
        _queue_name: Name of the Service Bus queue.
        _max_message_count: Maximum messages to fetch per poll batch.
        _max_wait_time: Receive wait time in seconds per poll batch.
        _max_in_flight: Backpressure limit for concurrent in-flight messages.
        _client: Long-lived async ServiceBusClient.
        _tasks: Set of background polling tasks.
        _tracer: Optional tracer for W3C distributed trace propagation.
    """

    def __init__(
        self,
        connection_str: str = "",
        queue_name: str = "",
        max_message_count: int = 10,
        max_wait_time: float = 5.0,
        max_in_flight: int = 100,
        tracer: TracerProtocol | None = None,
    ) -> None:
        """Initialise Azure Service Bus queue.

        Args:
            connection_str: Azure Service Bus connection string.
            queue_name: Target queue name.
            max_message_count: Maximum messages fetched per receive call.
            max_wait_time: Maximum wait time (seconds) for receive calls.
            max_in_flight: Maximum concurrent in-flight messages before
                backpressure is applied.
            tracer: Optional tracer for distributed tracing (W3C traceparent).
        """
        self._connection_str = connection_str
        self._queue_name = queue_name
        self._max_message_count = max_message_count
        self._max_wait_time = max_wait_time
        self._max_in_flight = max_in_flight
        self._tracer = tracer
        self._client: Any = None
        self._tasks: set[asyncio.Task[None]] = set()
        self._in_flight: int = 0
        self._hooks: HookRegistryProtocol | None = None

    # ------------------------------------------------------------------
    # Wiring helpers (called by provider after DI boot)
    # ------------------------------------------------------------------

    def set_tracer(self, tracer: TracerProtocol | None) -> None:
        """Attach an optional tracer after provider boot wiring.

        Args:
            tracer: Tracer to attach, or None to clear.
        """
        self._tracer = tracer

    def set_hook_registry(self, hooks: HookRegistryProtocol | None) -> None:
        """Attach an optional hook registry after provider boot wiring."""
        self._hooks = hooks

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _message_type(message: BusMessage) -> str:
        """Return the payload type label for lifecycle hooks."""
        return type(message.payload).__name__

    async def _emit_action(self, hook_name: str, payload: object) -> None:
        """Emit a queue action hook when a registry is available."""
        if self._hooks is None:
            return
        await self._hooks.call_action(hook_name, payload=payload)

    def _decrement_in_flight(self) -> None:
        """Decrement the in-flight counter (floor 0)."""
        self._in_flight = max(0, self._in_flight - 1)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """Open a long-lived Azure Service Bus client connection.

        Raises:
            ImportError: If ``azure-servicebus`` is not installed.
        """
        try:
            from azure.servicebus.aio import (
                ServiceBusClient,
            )
        except ImportError as exc:
            raise ImportError(
                "azure-servicebus required: pip install lexigram-queue[azure]"
            ) from exc

        self._client = ServiceBusClient.from_connection_string(self._connection_str)
        await self._client.__aenter__()
        logger.info(
            "azure_servicebus_connected",
            queue_name=self._queue_name,
        )

    async def close(self) -> None:
        """Cancel background tasks and close the Service Bus client."""
        for task in list(self._tasks):
            if not task.done():
                task.cancel()
        self._tasks.clear()

        if self._client is not None:
            await self._client.__aexit__(None, None, None)
            self._client = None

        logger.info("azure_servicebus_closed")

    # ------------------------------------------------------------------
    # Publish
    # ------------------------------------------------------------------

    async def publish(self, topic: str, message: BusMessage) -> None:
        """Publish a message to the configured Service Bus queue.

        Injects W3C trace context into the message body headers when a
        tracer is configured.

        Args:
            topic: Logical topic name (used only for hook/log metadata;
                the physical destination is ``queue_name``).
            message: Message to publish.

        Raises:
            RuntimeError: If not connected.
        """
        if self._client is None:
            raise RuntimeError("AzureServiceBusQueue not connected")

        from azure.servicebus import (
            ServiceBusMessage as AzMsg,
        )

        span = (
            self._tracer.start_span(
                f"queue.publish {topic}",
                attributes={
                    "messaging.destination": topic,
                    "messaging.system": "azure_servicebus",
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

                merged_headers: dict[str, str] = {**(message.headers or {}), **trace_headers}

                body = json.dumps(
                    {
                        "id": message.id,
                        "topic": message.topic,
                        "payload": message.payload,
                        "headers": merged_headers,
                    }
                )

                az_msg = AzMsg(
                    body,
                    application_properties=cast(
                        "dict[str | bytes, int | float | bytes | bool | str | UUID]",
                        merged_headers,
                    ),
                )

                async with self._client.get_queue_sender(
                    queue_name=self._queue_name
                ) as sender:
                    await sender.send_messages(az_msg)

                await self._emit_action(
                    "message.published",
                    MessagePublishedHook(
                        queue_name=topic,
                        message_type=self._message_type(message),
                    ),
                )
        except Exception as exc:  # noqa: BLE001 — observability catch; records span status then re-raises
            if span:
                span.record_exception(exc)
                span.set_status("error")
            raise

    # ------------------------------------------------------------------
    # Subscribe
    # ------------------------------------------------------------------

    async def subscribe(self, topic: str, handler: Any) -> None:
        """Start a background poll loop that delivers messages to ``handler``.

        Extracts W3C trace context from message body headers when a tracer
        is configured.  Applies backpressure by limiting the batch size to
        the remaining in-flight capacity.

        Each batch is fetched inside a short-lived receiver context so that
        ``complete_message`` / ``abandon_message`` are always called while
        that receiver is open.  Handlers for a batch run concurrently via
        ``asyncio.gather``.

        Args:
            topic: Logical topic name (used for hook/log metadata only;
                the physical source is ``queue_name``).
            handler: Async callable invoked per message.

        Raises:
            RuntimeError: If not connected.
        """
        if self._client is None:
            raise RuntimeError("AzureServiceBusQueue not connected")

        async def _handle_message(raw_msg: Any, receiver: Any) -> None:
            """Process one Service Bus message."""
            try:
                body_str = str(raw_msg)
                data: dict[str, Any] = json.loads(body_str)
            except (ValueError, TypeError):
                # Fall back to raw string body if not JSON
                data = {"topic": topic, "payload": str(raw_msg), "headers": {}}

            from lexigram.contracts.queue.types import BusMessage as BusMsg

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
                        "messaging.system": "azure_servicebus",
                    },
                    context=extracted_context,
                )

            try:
                with span if span is not None else _nullcontext():
                    await handler(msg)
                    await receiver.complete_message(raw_msg)

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
                try:
                    await receiver.abandon_message(raw_msg)
                except Exception as abandon_exc:  # noqa: BLE001 — infrastructure cleanup
                    logger.error(
                        "azure_servicebus_abandon_failed",
                        error=str(abandon_exc),
                    )
                raise
            finally:
                self._decrement_in_flight()

        async def _poll() -> None:
            while True:
                try:
                    capacity = max(0, self._max_in_flight - self._in_flight)
                    if capacity == 0:
                        logger.warning(
                            "azure_servicebus_backpressure_applied",
                            in_flight=self._in_flight,
                            limit=self._max_in_flight,
                        )
                        await asyncio.sleep(0.5)
                        continue

                    batch_size = min(capacity, self._max_message_count)

                    async with self._client.get_queue_receiver(
                        queue_name=self._queue_name,
                        max_wait_time=self._max_wait_time,
                    ) as receiver:
                        messages = await receiver.receive_messages(
                            max_message_count=batch_size,
                            max_wait_time=self._max_wait_time,
                        )
                        if messages:
                            self._in_flight += len(messages)
                            await asyncio.gather(
                                *[_handle_message(msg, receiver) for msg in messages],
                                return_exceptions=True,
                            )
                        else:
                            # Brief backoff when the queue is empty so that
                            # fast-returning mocks in tests (or a genuinely
                            # empty queue) don't spin the event loop at 100%.
                            await asyncio.sleep(0.05)

                except asyncio.CancelledError:
                    break
                except Exception as exc:  # noqa: BLE001 — resilience boundary
                    logger.error("azure_servicebus_poll_error", error=str(exc))
                    await asyncio.sleep(5)

        create_tracked_task(_poll(), self._tasks, name="asb_queue_poll")
        logger.debug("azure_servicebus_subscribed", queue_name=self._queue_name)

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Check Azure Service Bus connectivity by peeking at the queue.

        Args:
            timeout: Unused; provided for interface consistency.

        Returns:
            HealthCheckResult with status.
        """
        if self._client is None:
            return HealthCheckResult(
                component="azure_servicebus",
                status=HealthStatus.UNHEALTHY,
                details={"error": "not connected"},
            )
        try:
            async with self._client.get_queue_receiver(
                queue_name=self._queue_name,
            ) as receiver:
                await receiver.peek_messages(max_message_count=1)
            return HealthCheckResult(
                component="azure_servicebus",
                status=HealthStatus.HEALTHY,
                details={"queue_name": self._queue_name},
            )
        except Exception as exc:  # noqa: BLE001 — best-effort
            return HealthCheckResult(
                component="azure_servicebus",
                status=HealthStatus.UNHEALTHY,
                details={"error": str(exc)},
            )


__all__ = ["AzureServiceBusQueue"]
