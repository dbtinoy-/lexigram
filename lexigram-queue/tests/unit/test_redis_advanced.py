"""Advanced unit tests for RedisQueue — publish and subscribe mocks."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from lexigram.queue.backends.redis import RedisQueue
from lexigram.contracts.queue.types import BusMessage


@pytest.mark.asyncio
class TestRedisQueueAdvanced:
    @pytest.fixture
    def mock_redis(self):
        mock_aioredis = MagicMock()
        mock_redis_root = MagicMock()
        mock_client = MagicMock()
        
        # Async methods
        mock_client.ping = AsyncMock()
        mock_client.publish = AsyncMock()
        mock_client.aclose = AsyncMock()
        
        mock_aioredis.from_url.return_value = mock_client
        mock_redis_root.asyncio = mock_aioredis
        
        with patch.dict("sys.modules", {
            "redis": mock_redis_root,
            "redis.asyncio": mock_aioredis
        }):
            yield mock_aioredis.from_url, mock_client

    async def test_connect_lifecycle(self, mock_redis) -> None:
        mock_from_url, mock_client = mock_redis
        queue = RedisQueue(url="redis://test")
        
        await queue.connect()
        mock_from_url.assert_called_with("redis://test", max_connections=10)
        mock_client.ping.assert_called_once()
        
        await queue.close()
        mock_client.aclose.assert_called_once()

    async def test_publish_success(self, mock_redis) -> None:
        _, mock_client = mock_redis
        queue = RedisQueue()
        await queue.connect()
        
        msg = BusMessage(id="msg-1", topic="t1", payload={"foo": "bar"})
        await queue.publish("t1", msg)
        
        mock_client.publish.assert_called_once()
        args = mock_client.publish.call_args[0]
        assert args[0] == "t1"
        assert b'"id":"msg-1"' in args[1] or b'"id": "msg-1"' in args[1]

    async def test_subscribe_success(self, mock_redis) -> None:
        _, mock_client = mock_redis
        queue = RedisQueue()
        await queue.connect()
        
        mock_pubsub = MagicMock()
        mock_pubsub.subscribe = AsyncMock()
        mock_pubsub.listen = MagicMock() # Will be called as async for
        
        mock_client.pubsub.return_value = mock_pubsub
        
        handler = AsyncMock()
        await queue.subscribe("t1", handler)
        
        mock_pubsub.subscribe.assert_called_with("t1")
        assert len(queue._tasks) == 1

    async def test_health_check_states(self, mock_redis) -> None:
        _, mock_client = mock_redis
        queue = RedisQueue()
        
        # Not connected
        hc = await queue.health_check()
        assert hc.status == "unhealthy"
        
        await queue.connect()
        
        # Healthy
        hc = await queue.health_check()
        assert hc.status == "healthy"
        
        # Connection error
        mock_client.ping.side_effect = OSError("boom")
        hc = await queue.health_check()
        assert hc.status == "unhealthy"
        assert "boom" in hc.details["error"]
