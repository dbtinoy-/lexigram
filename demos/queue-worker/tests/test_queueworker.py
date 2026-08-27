"""Tests — real composition root, no mocks.

Every test boots a real Application with the actual DI container.
Services are tested through their public API, not by mocking internals.
"""

from __future__ import annotations

import pytest
import httpx


class TestQueueOperations:
    """Test queue publish and process operations."""

    @pytest.mark.asyncio
    async def test_publish_message(self, client: httpx.AsyncClient) -> None:
        """POST /api/queue/publish publishes a message."""
        resp = await client.post(
            "/api/queue/publish",
            json={"topic": "orders", "payload": {"order_id": "123"}},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "message_id" in data
        assert data["topic"] == "orders"

    @pytest.mark.asyncio
    async def test_publish_missing_topic(self, client: httpx.AsyncClient) -> None:
        """POST /api/queue/publish with empty topic returns error."""
        resp = await client.post(
            "/api/queue/publish",
            json={"topic": ""},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "error" in data

    @pytest.mark.asyncio
    async def test_process_message(self, client: httpx.AsyncClient) -> None:
        """POST /api/queue/process processes a message."""
        # First publish a message
        await client.post(
            "/api/queue/publish",
            json={"topic": "orders", "payload": {"order_id": "456"}},
        )

        # Then process it
        resp = await client.post(
            "/api/queue/process",
            json={"topic": "orders"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "message_id" in data

    @pytest.mark.asyncio
    async def test_process_empty_queue(self, client: httpx.AsyncClient) -> None:
        """POST /api/queue/process with empty queue returns no messages."""
        resp = await client.post(
            "/api/queue/process",
            json={"topic": "empty_topic"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "message" in data

    @pytest.mark.asyncio
    async def test_process_batch(self, client: httpx.AsyncClient) -> None:
        """POST /api/queue/process/batch processes multiple messages."""
        # Publish multiple messages
        for i in range(5):
            await client.post(
                "/api/queue/publish",
                json={"topic": "batch_topic", "payload": {"index": i}},
            )

        # Process batch
        resp = await client.post(
            "/api/queue/process/batch",
            json={"topic": "batch_topic", "batch_size": 3},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["processed"] == 3

    @pytest.mark.asyncio
    async def test_get_size(self, client: httpx.AsyncClient) -> None:
        """GET /api/queue/size returns queue size."""
        # Publish some messages
        for _ in range(3):
            await client.post(
                "/api/queue/publish",
                json={"topic": "size_topic", "payload": {}},
            )

        resp = await client.get("/api/queue/size?topic=size_topic")
        assert resp.status_code == 200
        data = resp.json()
        assert data["size"] == 3


class TestHealth:
    """Test health endpoint."""

    @pytest.mark.asyncio
    async def test_health(self, client: httpx.AsyncClient) -> None:
        """GET /api/queue/health returns ok."""
        resp = await client.get("/api/queue/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
