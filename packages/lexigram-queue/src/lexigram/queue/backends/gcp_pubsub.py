"""Google Cloud Pub/Sub queue backend."""

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


class GCPPubSubQueue:
    """Google Cloud Pub/Sub queue backend.

    Requires: pip install lexigram-queue[gcp]

    Uses the synchronous ``google.cloud.pubsub_v1`` clients wrapped in
    ``asyncio.to_thread`` so the event loop is never blocked.  The
    subscriber's ``pull()`` method performs a synchronous blocking pull
    with a configurable timeout; the background poll loop re-issues the
    call in a loop, acknowledging successful messages and leaving failed
    ones to be redelivered after the ack deadline.

    Attributes:
        _project_id: GCP project ID.
        _topic_id: Pub/Sub topic ID.
        _subscription_id: Pub/Sub subscription ID.
        _max_messages: Maximum messages to fetch per pull call.
        _max_wait_time: gRPC timeout (seconds) for each synchronous pull.
        _max_in_flight: Backpressure limit for concurrent in-flight messages.
        _publisher: google-cloud-pubsub PublisherClient.
        _subscriber: google-cloud-pubsub SubscriberClient.
        _topic_path: Fully-qualified topic resource path.
        _subscription_path: Fully-qualified subscription resource path.
        _tasks: Set of background polling tasks.
        _tracer: Optional tracer for W3C distributed trace propagation.
    """

    def __init__(
        self,
        project_id: str = "",
        topic_id: str = "",
        subscription_id: str = "",
        max_messages: int = 10,
        max_wait_time: float = 5.0,
        max_in_flight: int = 100,
        tracer: TracerProtocol | None = None,
    ) -> None:
        """Initialise GCP Pub/Sub queue.

        Args:
            project_id: GCP project ID.
            topic_id: Pub/Sub topic ID.
            subscription_id: Pub/Sub subscription ID for consuming messages.
            max_messages: Maximum messages fetched per pull call.
            max_wait_time: gRPC call timeout in seconds for pull requests.
            max_in_flight: Maximum concurrent in-flight messages before
                backpressure is applied.
            tracer: Optional tracer for distributed tracing (W3C traceparent).
        """
        self._project_id = project_id
        self._topic_id = topic_id
        self._subscription_id = subscription_id
        self._max_messages = max_messages
        self._max_wait_time = max_wait_time
        self._max_in_flight = max_in_flight
        self._tracer = tracer
        self._publisher: Any = None
        self._subscriber: Any = None
        self._topic_path: str = ""
        self._subscription_path: str = ""
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
        """Create GCP Pub/Sub publisher and subscriber clients.

        Raises:
            ImportError: If ``google-cloud-pubsub`` is not installed.
        """
        try:
            from google.cloud import pubsub_v1
        except ImportError as exc:
            raise ImportError(
                "google-cloud-pubsub required: pip install lexigram-queue[gcp]"
            ) from exc

        self._publisher = pubsub_v1.PublisherClient()
        self._subscriber = pubsub_v1.SubscriberClient()
        self._topic_path = self._publisher.topic_path(self._project_id, self._topic_id)
        self._subscription_path = self._subscriber.subscription_path(
            self._project_id, self._subscription_id
        )
        logger.info(
            "gcp_pubsub_connected",
            project_id=self._project_id,
            topic_id=self._topic_id,
            subscription_id=self._subscription_id,
        )

    async def close(self) -> None:
        """Cancel background tasks and close GCP Pub/Sub clients."""
        for task in list(self._tasks):
            if not task.done():
                task.cancel()
        self._tasks.clear()

        if self._publisher is not None:
            await asyncio.to_thread(self._publisher.close)
            self._publisher = None
        if self._subscriber is not None:
            await asyncio.to_thread(self._subscriber.close)
            self._subscriber = None

        logger.info("gcp_pubsub_closed")

    # ------------------------------------------------------------------
    # Publish
    # ------------------------------------------------------------------

    async def publish(self, topic: str, message: BusMessage) -> None:
        """Publish a message to the configured Pub/Sub topic.

        Injects W3C trace context into the message body headers when a
        tracer is configured.  The ``publish()`` call is run in a thread
        executor to avoid blocking the event loop.

        Args:
            topic: Logical topic name (used for hook/log metadata only;
                the physical destination is the configured ``topic_id``).
            message: Message to publish.

        Raises:
            RuntimeError: If not connected.
        """
        if self._publisher is None:
            raise RuntimeError("GCPPubSubQueue not connected")

        span = (
            self._tracer.start_span(
                f"queue.publish {topic}",
                attributes={
                    "messaging.destination": topic,
                    "messaging.system": "gcp_pubsub",
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

                body = json.dumps(
                    {
                        "id": message.id,
                        "topic": message.topic,
                        "payload": message.payload,
                        "headers": merged_headers,
                    }
                )

                # google-cloud-pubsub attributes must be string->string
                str_attrs = {k: str(v) for k, v in merged_headers.items()}

                future = await asyncio.to_thread(
                    self._publisher.publish,
                    self._topic_path,
                    body,
                    **str_attrs,
                )
                # Block until the publish is confirmed (runs in executor)
                await asyncio.to_thread(future.result)

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

    # ------------------------------------------------------------------
    # Subscribe
    # ------------------------------------------------------------------

    async def subscribe(self, topic: str, handler: Any) -> None:
        """Start a background poll loop that delivers messages to ``handler``.

        Extracts W3C trace context from message body headers when a tracer
        is configured.  Applies backpressure by limiting the pull batch
        size to the remaining in-flight capacity.  Acknowledged only on
        successful handler execution; failed messages are left for
        redelivery after the ack deadline.

        Args:
            topic: Logical topic name (used for hook/log metadata only;
                the physical source is the configured ``subscription_id``).
            handler: Async callable invoked per message.

        Raises:
            RuntimeError: If not connected.
        """
        if self._subscriber is None:
            raise RuntimeError("GCPPubSubQueue not connected")

        async def _handle_message(received: Any) -> None:
            """Process one received Pub/Sub message."""
            try:
                data: dict[str, Any] = json.loads(received.message.data.decode())
            except (ValueError, AttributeError):
                data = {"topic": topic, "payload": None, "headers": {}}

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
                        "messaging.system": "gcp_pubsub",
                    },
                    context=extracted_context,
                )

            try:
                with span if span is not None else _nullcontext():
                    await handler(msg)
                    await asyncio.to_thread(
                        self._subscriber.acknowledge,
                        subscription=self._subscription_path,
                        ack_ids=[received.ack_id],
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
                    capacity = max(0, self._max_in_flight - self._in_flight)
                    if capacity == 0:
                        logger.warning(
                            "gcp_pubsub_backpressure_applied",
                            in_flight=self._in_flight,
                            limit=self._max_in_flight,
                        )
                        await asyncio.sleep(0.5)
                        continue

                    batch_size = min(capacity, self._max_messages)

                    response = await asyncio.to_thread(
                        self._subscriber.pull,
                        subscription=self._subscription_path,
                        max_messages=batch_size,
                        timeout=self._max_wait_time,
                    )

                    received_messages = getattr(response, "received_messages", [])
                    if received_messages:
                        self._in_flight += len(received_messages)
                        for received in received_messages:
                            create_tracked_task(
                                _handle_message(received),
                                self._tasks,
                                name="gcp_pubsub_handle_message",
                            )
                    else:
                        # Brief backoff when the subscription is empty so that
                        # fast-returning mocks in tests (or a genuinely empty
                        # subscription) don't spin the event loop at 100%.
                        await asyncio.sleep(0.05)

                except asyncio.CancelledError:
                    break
                except Exception as exc:  # noqa: BLE001 — resilience boundary
                    # DeadlineExceeded is expected when no messages arrive;
                    # log all other errors and back off.
                    exc_name = type(exc).__name__
                    if (
                        "DeadlineExceeded" in exc_name
                        or "ServiceUnavailable" in exc_name
                    ):
                        await asyncio.sleep(0.1)
                    else:
                        logger.error("gcp_pubsub_poll_error", error=str(exc))
                        await asyncio.sleep(5)

        create_tracked_task(_poll(), self._tasks, name="gcp_pubsub_poll")
        logger.debug(
            "gcp_pubsub_subscribed",
            subscription_path=self._subscription_path,
        )

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Check GCP Pub/Sub connectivity by fetching the subscription metadata.

        Args:
            timeout: gRPC call timeout in seconds.

        Returns:
            HealthCheckResult with status.
        """
        if self._subscriber is None:
            return HealthCheckResult(
                component="gcp_pubsub",
                status=HealthStatus.UNHEALTHY,
                details={"error": "not connected"},
            )
        try:
            await asyncio.to_thread(
                self._subscriber.get_subscription,
                subscription=self._subscription_path,
                timeout=timeout,
            )
            return HealthCheckResult(
                component="gcp_pubsub",
                status=HealthStatus.HEALTHY,
                details={
                    "project_id": self._project_id,
                    "subscription_id": self._subscription_id,
                },
            )
        except Exception as exc:  # noqa: BLE001 — best-effort
            return HealthCheckResult(
                component="gcp_pubsub",
                status=HealthStatus.UNHEALTHY,
                details={"error": str(exc)},
            )


__all__ = ["GCPPubSubQueue"]
