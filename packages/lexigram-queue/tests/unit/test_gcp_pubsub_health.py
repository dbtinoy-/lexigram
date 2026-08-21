"""GCP Pub/Sub health-check and misc tests."""

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
