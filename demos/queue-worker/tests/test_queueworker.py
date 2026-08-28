"""HTTP tests for the real QueueModule + MessageConsumer composition."""

from __future__ import annotations

import asyncio

import httpx
import pytest


class TestQueueOperations:
    """Test publish/subscribe behavior rather than a fake pull queue."""

    @pytest.mark.asyncio
    async def test_publish_message(self, client: httpx.AsyncClient) -> None:
        response = await client.post(
            "/api/queue/publish",
            json={"payload": {"order_id": "123"}},
        )
        assert response.status_code == 200
        data = response.json()
        assert "message_id" in data
        assert data["topic"] == "tasks"
        assert data["delivery"] == "at_least_once"
        assert data["max_retries"] == 3

        # InMemoryQueue dispatches handlers as tracked asyncio tasks.
        await asyncio.sleep(0.01)
        processed = await client.get("/api/queue/processed")
        assert processed.json()["count"] == 1

    @pytest.mark.asyncio
    async def test_publish_missing_topic(self, client: httpx.AsyncClient) -> None:
        response = await client.post(
            "/api/queue/publish",
            json={"topic": ""},
        )
        assert response.status_code == 200
        assert "error" in response.json()

    @pytest.mark.asyncio
    async def test_worker_rejects_other_topics(self, client: httpx.AsyncClient) -> None:
        response = await client.post(
            "/api/queue/publish",
            json={"topic": "orders", "payload": {}},
        )
        assert "error" in response.json()
        assert "tasks" in response.json()["error"]

    @pytest.mark.asyncio
    async def test_get_processed_messages(self, client: httpx.AsyncClient) -> None:
        await client.post(
            "/api/queue/publish",
            json={"payload": {"index": 1}},
        )
        await asyncio.sleep(0.01)
        response = await client.get("/api/queue/processed")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["results"][0]["payload"]["index"] == 1


class TestHealth:
    """Test worker readiness."""

    @pytest.mark.asyncio
    async def test_health(self, client: httpx.AsyncClient) -> None:
        response = await client.get("/api/queue/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["topic"] == "tasks"
        assert data["consumer_running"] is True
