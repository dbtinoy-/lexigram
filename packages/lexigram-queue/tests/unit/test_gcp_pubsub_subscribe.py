"""GCP Pub/Sub subscribe delivery, ack, and backpressure tests."""

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
    publisher.topic_path = MagicMock(return_value="projects/my-project/topics/my-topic")
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

        envelope = {"id": "m1", "topic": "jobs", "payload": {"n": 7}, "headers": {}}
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
        subscriber.acknowledge = MagicMock(
            side_effect=lambda **kw: ack_calls.append(kw)
        )

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

