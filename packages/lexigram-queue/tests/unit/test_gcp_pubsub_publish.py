"""GCP Pub/Sub publish tests."""

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

