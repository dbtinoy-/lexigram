"""Tests for GCPPubSubQueue backend."""

from __future__ import annotations

import asyncio
import json
import sys
import types
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.contracts.core.health import HealthStatus
from lexigram.contracts.queue.types import BusMessage


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_received_message(
    payload: dict[str, Any], ack_id: str = "ack-001"
) -> MagicMock:
    """Build a fake Pub/Sub ReceivedMessage."""
    rm = MagicMock()
    rm.ack_id = ack_id
    rm.message = MagicMock()
    rm.message.data = json.dumps(payload).encode()
    return rm


def _make_queue(**kwargs: Any) -> Any:
    from lexigram.queue.backends.gcp_pubsub import GCPPubSubQueue

    return GCPPubSubQueue(
        project_id="my-project",
        topic_id="my-topic",
        subscription_id="my-sub",
        **kwargs,
    )


def _make_clients() -> tuple[MagicMock, MagicMock]:
    """Return (mock_publisher, mock_subscriber) with standard defaults."""
    publisher = MagicMock()
    publisher.topic_path = MagicMock(
        return_value="projects/my-project/topics/my-topic"
    )
    pub_future = MagicMock()
    pub_future.result = MagicMock(return_value="msg-id-1")
    publisher.publish = MagicMock(return_value=pub_future)
    publisher.get_topic = MagicMock(return_value=MagicMock())
    publisher.close = MagicMock()

    subscriber = MagicMock()
    subscriber.subscription_path = MagicMock(
        return_value="projects/my-project/subscriptions/my-sub"
    )
    empty_response = MagicMock()
    empty_response.received_messages = []
    subscriber.pull = MagicMock(return_value=empty_response)
    subscriber.acknowledge = MagicMock()
    subscriber.get_subscription = MagicMock(return_value=MagicMock())
    subscriber.close = MagicMock()

    return publisher, subscriber


def _inject_clients(queue: Any) -> tuple[MagicMock, MagicMock]:
    """Inject mock clients directly into the queue without going through connect()."""
    publisher, subscriber = _make_clients()
    queue._publisher = publisher
    queue._subscriber = subscriber
    queue._topic_path = "projects/my-project/topics/my-topic"
    queue._subscription_path = "projects/my-project/subscriptions/my-sub"
    return publisher, subscriber


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGCPPubSubQueue:
    """Unit tests for GCPPubSubQueue.

    The google-cloud-pubsub SDK is never installed; all SDK objects are
    replaced with MagicMock (sync, for use inside asyncio.to_thread).
    """

    # ------------------------------------------------------------------
    # connect / close
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_connect_raises_import_error_without_sdk(self) -> None:
        """connect() raises ImportError when google-cloud-pubsub is absent."""
        queue = _make_queue()
        saved = {
            k: sys.modules.pop(k)
            for k in list(sys.modules)
            if k.startswith("google.cloud.pubsub_v1") or k == "google.cloud.pubsub_v1"
        }
        # Also block the top-level import path
        fake_cloud = types.ModuleType("google.cloud")
        # No pubsub_v1 attribute → import fails
        sys.modules["google.cloud.pubsub_v1"] = None  # type: ignore[assignment]
        try:
            with pytest.raises((ImportError, TypeError)):
                await queue.connect()
        finally:
            sys.modules.pop("google.cloud.pubsub_v1", None)
            sys.modules.update(saved)

    @pytest.mark.asyncio
    async def test_connect_builds_topic_and_subscription_paths(self) -> None:
        """connect() should populate _topic_path and _subscription_path."""
        queue = _make_queue()
        publisher, subscriber = _make_clients()

        fake_pubsub_v1 = types.ModuleType("google.cloud.pubsub_v1")
        fake_pubsub_v1.PublisherClient = MagicMock(return_value=publisher)  # type: ignore[attr-defined]
        fake_pubsub_v1.SubscriberClient = MagicMock(return_value=subscriber)  # type: ignore[attr-defined]

        saved = sys.modules.get("google.cloud.pubsub_v1")
        sys.modules["google.cloud.pubsub_v1"] = fake_pubsub_v1

        try:
            # Patch the import inside connect() by injecting the fake module
            import importlib
            import lexigram.queue.backends.gcp_pubsub as _mod  # noqa: F401

            # connect() does `from google.cloud import pubsub_v1`; feed the fake
            fake_cloud = types.ModuleType("google.cloud")
            fake_cloud.pubsub_v1 = fake_pubsub_v1  # type: ignore[attr-defined]
            sys.modules["google.cloud"] = fake_cloud

            await queue.connect()
        finally:
            if saved is None:
                sys.modules.pop("google.cloud.pubsub_v1", None)
            else:
                sys.modules["google.cloud.pubsub_v1"] = saved

        assert queue._topic_path == "projects/my-project/topics/my-topic"
        assert queue._subscription_path == "projects/my-project/subscriptions/my-sub"

    @pytest.mark.asyncio
    async def test_close_cancels_tasks_and_closes_clients(self) -> None:
        """close() cancels background tasks and calls close() on both clients."""
        queue = _make_queue()
        publisher, subscriber = _inject_clients(queue)

        done_task: asyncio.Task[None] = asyncio.create_task(asyncio.sleep(0))
        await asyncio.sleep(0)
        queue._tasks.add(done_task)

        await queue.close()

        publisher.close.assert_called_once()
        subscriber.close.assert_called_once()
        assert queue._publisher is None
        assert queue._subscriber is None

    # ------------------------------------------------------------------
    # publish
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_publish_raises_when_not_connected(self) -> None:
        """publish() raises RuntimeError when publisher is None."""
        queue = _make_queue()
        with pytest.raises(RuntimeError, match="not connected"):
            await queue.publish("t", BusMessage(topic="t", payload={}))

    @pytest.mark.asyncio
    async def test_publish_calls_publisher_with_encoded_body(self) -> None:
        """publish() calls publisher.publish with the correct topic path and JSON body."""
        queue = _make_queue()
        publisher, _ = _inject_clients(queue)

        msg = BusMessage(topic="jobs", payload={"task": "ingest"})
        await queue.publish("jobs", msg)

        publisher.publish.assert_called_once()
        call_args, _ = publisher.publish.call_args
        assert call_args[0] == "projects/my-project/topics/my-topic"
        data = json.loads(call_args[1].decode())
        assert data["topic"] == "jobs"
        assert data["payload"] == {"task": "ingest"}

    @pytest.mark.asyncio
    async def test_publish_waits_for_future_result(self) -> None:
        """publish() calls future.result() to confirm delivery."""
        queue = _make_queue()
        publisher, _ = _inject_clients(queue)

        await queue.publish("t", BusMessage(topic="t", payload="hi"))

        future = publisher.publish.return_value
        future.result.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_emits_hook(self) -> None:
        """publish() fires message.published hook with correct queue_name."""
        queue = _make_queue()
        publisher, _ = _inject_clients(queue)

        mock_hooks = AsyncMock()
        queue.set_hook_registry(mock_hooks)

        await queue.publish("jobs", BusMessage(topic="jobs", payload=42))

        mock_hooks.call_action.assert_awaited_once()
        _, call_kwargs = mock_hooks.call_action.call_args
        hook = call_kwargs["payload"]
        assert hook.queue_name == "jobs"

    @pytest.mark.asyncio
    async def test_publish_injects_trace_headers_as_attributes(self) -> None:
        """publish() injects W3C traceparent as a Pub/Sub message attribute."""
        from lexigram.testing.fakes import FakeTracer

        queue = _make_queue()
        publisher, _ = _inject_clients(queue)
        queue.set_tracer(FakeTracer())

        await queue.publish("t", BusMessage(topic="t", payload="x"))

        _, call_kwargs = publisher.publish.call_args
        assert "traceparent" in call_kwargs

    # ------------------------------------------------------------------
    # subscribe
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_subscribe_raises_when_not_connected(self) -> None:
        """subscribe() raises RuntimeError when subscriber is None."""
        queue = _make_queue()

        async def handler(msg: BusMessage) -> None:
            pass

        with pytest.raises(RuntimeError, match="not connected"):
            await queue.subscribe("t", handler)

    @pytest.mark.asyncio
    async def test_subscribe_delivers_message_to_handler(self) -> None:
        """Poll loop deserialises the JSON envelope and calls the handler once."""
        queue = _make_queue(max_wait_time=0.1)
        _, subscriber = _inject_clients(queue)

        envelope = {
            "id": "m1", "topic": "jobs", "payload": {"n": 7}, "headers": {}
        }
        received_msg = _make_received_message(envelope, ack_id="ack-1")

        delivered = asyncio.Event()
        received: list[BusMessage] = []
        call_count = 0

        def fake_pull(
            subscription: str, max_messages: int = 10, timeout: float = 5.0
        ) -> MagicMock:
            nonlocal call_count
            resp = MagicMock()
            if call_count == 0:
                call_count += 1
                resp.received_messages = [received_msg]
            else:
                resp.received_messages = []
            return resp

        subscriber.pull = MagicMock(side_effect=fake_pull)

        async def handler(msg: BusMessage) -> None:
            received.append(msg)
            delivered.set()

        await queue.subscribe("jobs", handler)
        await asyncio.wait_for(delivered.wait(), timeout=5.0)

        assert len(received) == 1
        assert received[0].payload == {"n": 7}

        for task in list(queue._tasks):
            task.cancel()

    @pytest.mark.asyncio
    async def test_subscribe_acknowledges_on_success(self) -> None:
        """Poll loop calls subscriber.acknowledge after the handler succeeds."""
        queue = _make_queue(max_wait_time=0.1)
        _, subscriber = _inject_clients(queue)

        envelope = {"id": "m2", "topic": "t", "payload": "ok", "headers": {}}
        received_msg = _make_received_message(envelope, ack_id="ack-99")

        acked = asyncio.Event()
        ack_calls: list[Any] = []

        def fake_acknowledge(**kw: Any) -> None:
            ack_calls.append(kw)
            acked.set()

        subscriber.acknowledge = MagicMock(side_effect=fake_acknowledge)

        call_count = 0

        def fake_pull(
            subscription: str, max_messages: int = 10, timeout: float = 5.0
        ) -> MagicMock:
            nonlocal call_count
            resp = MagicMock()
            if call_count == 0:
                call_count += 1
                resp.received_messages = [received_msg]
            else:
                resp.received_messages = []
            return resp

        subscriber.pull = MagicMock(side_effect=fake_pull)

        async def handler(msg: BusMessage) -> None:
            pass

        await queue.subscribe("t", handler)
        await asyncio.wait_for(acked.wait(), timeout=5.0)

        assert len(ack_calls) == 1
        assert ack_calls[0]["ack_ids"] == ["ack-99"]

        for task in list(queue._tasks):
            task.cancel()

    @pytest.mark.asyncio
    async def test_subscribe_does_not_ack_on_handler_failure(self) -> None:
        """Failed handler must NOT acknowledge the message (implicit nack)."""
        queue = _make_queue(max_wait_time=0.1)
        _, subscriber = _inject_clients(queue)

        envelope = {"id": "m3", "topic": "t", "payload": "fail", "headers": {}}
        received_msg = _make_received_message(envelope, ack_id="ack-fail")

        handler_ran = asyncio.Event()
        call_count = 0

        def fake_pull(
            subscription: str, max_messages: int = 10, timeout: float = 5.0
        ) -> MagicMock:
            nonlocal call_count
            resp = MagicMock()
            if call_count == 0:
                call_count += 1
                resp.received_messages = [received_msg]
            else:
                resp.received_messages = []
            return resp

        subscriber.pull = MagicMock(side_effect=fake_pull)
        ack_calls: list[Any] = []
        subscriber.acknowledge = MagicMock(side_effect=lambda **kw: ack_calls.append(kw))

        async def bad_handler(msg: BusMessage) -> None:
            handler_ran.set()
            raise ValueError("deliberate fail")

        await queue.subscribe("t", bad_handler)
        await asyncio.wait_for(handler_ran.wait(), timeout=5.0)
        # Give a brief moment for any erroneous ack to fire
        await asyncio.sleep(0.1)

        assert len(ack_calls) == 0

        for task in list(queue._tasks):
            task.cancel()

    @pytest.mark.asyncio
    async def test_subscribe_applies_backpressure(self) -> None:
        """Poll loop skips pull() when in-flight messages fill the limit."""
        queue = _make_queue(max_messages=5, max_in_flight=2)
        _, subscriber = _inject_clients(queue)

        # Simulate already at limit
        queue._in_flight = 2

        pull_calls: list[int] = []

        def fake_pull(
            subscription: str, max_messages: int = 10, timeout: float = 5.0
        ) -> MagicMock:
            pull_calls.append(max_messages)
            resp = MagicMock()
            resp.received_messages = []
            return resp

        subscriber.pull = MagicMock(side_effect=fake_pull)

        async def handler(msg: BusMessage) -> None:
            pass

        await queue.subscribe("t", handler)
        # Give the loop time to run — it should sleep (0.5s) due to backpressure
        await asyncio.sleep(0.2)

        assert len(pull_calls) == 0

        for task in list(queue._tasks):
            task.cancel()

    @pytest.mark.asyncio
    async def test_subscribe_emits_consumed_hook(self) -> None:
        """Poll loop emits message.consumed hook after successful handling."""
        queue = _make_queue(max_wait_time=0.1)
        _, subscriber = _inject_clients(queue)

        envelope = {"id": "h1", "topic": "t", "payload": "p", "headers": {}}
        received_msg = _make_received_message(envelope, ack_id="ack-hook")
        hook_fired = asyncio.Event()

        mock_hooks = AsyncMock()

        async def tracking_call_action(name: str, **kwargs: Any) -> None:
            if name == "message.consumed":
                hook_fired.set()

        mock_hooks.call_action = MagicMock(side_effect=tracking_call_action)
        queue.set_hook_registry(mock_hooks)

        call_count = 0

        def fake_pull(
            subscription: str, max_messages: int = 10, timeout: float = 5.0
        ) -> MagicMock:
            nonlocal call_count
            resp = MagicMock()
            if call_count == 0:
                call_count += 1
                resp.received_messages = [received_msg]
            else:
                resp.received_messages = []
            return resp

        subscriber.pull = MagicMock(side_effect=fake_pull)

        async def handler(msg: BusMessage) -> None:
            pass

        await queue.subscribe("t", handler)
        await asyncio.wait_for(hook_fired.wait(), timeout=5.0)

        for task in list(queue._tasks):
            task.cancel()

    # ------------------------------------------------------------------
    # health_check
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_health_check_unhealthy_when_not_connected(self) -> None:
        """health_check() returns UNHEALTHY when subscriber is None."""
        queue = _make_queue()
        result = await queue.health_check()
        assert result.status == HealthStatus.UNHEALTHY
        assert "not connected" in result.details["error"]

    @pytest.mark.asyncio
    async def test_health_check_healthy_on_get_subscription_success(self) -> None:
        """health_check() returns HEALTHY when get_subscription succeeds."""
        queue = _make_queue()
        _, subscriber = _inject_clients(queue)

        result = await queue.health_check()

        assert result.status == HealthStatus.HEALTHY
        assert result.details["project_id"] == "my-project"
        assert result.details["subscription_id"] == "my-sub"

    @pytest.mark.asyncio
    async def test_health_check_unhealthy_on_exception(self) -> None:
        """health_check() returns UNHEALTHY when get_subscription raises."""
        queue = _make_queue()
        _, subscriber = _inject_clients(queue)
        subscriber.get_subscription = MagicMock(
            side_effect=ConnectionError("gRPC unavailable")
        )

        result = await queue.health_check()

        assert result.status == HealthStatus.UNHEALTHY
        assert "gRPC unavailable" in result.details["error"]

    # ------------------------------------------------------------------
    # Wiring helpers
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_set_tracer_stores_and_clears(self) -> None:
        """set_tracer(None) clears the tracer."""
        from lexigram.testing.fakes import FakeTracer

        queue = _make_queue()
        tracer = FakeTracer()
        queue.set_tracer(tracer)
        assert queue._tracer is tracer
        queue.set_tracer(None)
        assert queue._tracer is None

    @pytest.mark.asyncio
    async def test_set_hook_registry_stores(self) -> None:
        """set_hook_registry stores the provided registry."""
        queue = _make_queue()
        mock_hooks = AsyncMock()
        queue.set_hook_registry(mock_hooks)
        assert queue._hooks is mock_hooks

    @pytest.mark.asyncio
    async def test_decrement_in_flight_floors_at_zero(self) -> None:
        """_decrement_in_flight must never go below 0."""
        queue = _make_queue()
        queue._in_flight = 0
        queue._decrement_in_flight()
        assert queue._in_flight == 0


__all__: list[str] = []
