"""GCP Pub/Sub connect/close lifecycle tests."""

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


    @pytest.mark.asyncio
    async def test_connect_raises_import_error_without_sdk(self) -> None:
        """connect() raises ImportError when google-cloud-pubsub is absent."""
        queue = _make_queue()
        saved = {
            k: sys.modules.pop(k)
            for k in list(sys.modules)
            if k.startswith("google.cloud.pubsub_v1") or k == "google.cloud.pubsub_v1"
        }
        # Evict leaked namespace stubs (e.g. from firestore tests) so the
        # `from google.cloud import pubsub_v1` import fails loudly.
        for _parent in ("google", "google.cloud"):
            _prev = sys.modules.pop(_parent, None)
            if _prev is not None:
                saved[_parent] = _prev
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

