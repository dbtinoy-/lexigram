"""Advanced unit tests for RabbitMQQueue — publish and subscribe mocks."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from lexigram.queue.backends.rabbitmq import RabbitMQQueue
from lexigram.contracts.queue.types import BusMessage


@pytest.mark.asyncio
class TestRabbitMQQueueAdvanced:
    @pytest.fixture
    def mock_aio_pika(self):
        mock_ap = MagicMock()
        mock_connect = AsyncMock()
        mock_connection = AsyncMock()
        mock_channel = AsyncMock()
        
        mock_ap.connect_robust = mock_connect
        # Mock Message to store the body passed to its constructor
        def mock_message_init(body):
            m = MagicMock()
            m.body = body
            return m
            
        mock_ap.Message.side_effect = mock_message_init
        mock_connect.return_value = mock_connection
        mock_connection.channel.return_value = mock_channel
        
        with patch.dict("sys.modules", {"aio_pika": mock_ap}):
            yield mock_connect, mock_connection, mock_channel

    async def test_connect_lifecycle(self, mock_aio_pika) -> None:
        mock_connect, mock_connection, mock_channel = mock_aio_pika
        queue = RabbitMQQueue(url="amqp://test", exchange="extest")
        
        await queue.connect()
        mock_connect.assert_called_with("amqp://test")
        mock_channel.set_qos.assert_called_with(prefetch_count=10)
        
        await queue.close()
        mock_connection.close.assert_called_once()

    async def test_publish_success(self, mock_aio_pika) -> None:
        _, _, mock_channel = mock_aio_pika
        queue = RabbitMQQueue()
        await queue.connect()
        
        mock_exchange = AsyncMock()
        mock_channel.get_exchange.return_value = mock_exchange
        
        msg = BusMessage(id="msg-1", topic="t1", payload={"foo": "bar"})
        await queue.publish("t1", msg)
        
        mock_exchange.publish.assert_called_once()
        sent_msg = mock_exchange.publish.call_args[0][0]
        assert b"msg-1" in sent_msg.body

    async def test_subscribe_success(self, mock_aio_pika) -> None:
        _, _, mock_channel = mock_aio_pika
        queue = RabbitMQQueue()
        await queue.connect()
        
        mock_rmq_queue = AsyncMock()
        mock_channel.declare_queue.return_value = mock_rmq_queue
        
        handler = AsyncMock()
        await queue.subscribe("t1", handler)
        
        mock_channel.declare_queue.assert_called_with("t1", durable=True)
        mock_rmq_queue.consume.assert_called_once()

    async def test_health_check_states(self, mock_aio_pika) -> None:
        _, mock_connection, _ = mock_aio_pika
        queue = RabbitMQQueue()
        
        # Not connected
        hc = await queue.health_check()
        assert hc.status == "unhealthy"
        
        await queue.connect()
        
        # Healthy
        mock_connection.is_closed = False
        hc = await queue.health_check()
        assert hc.status == "healthy"
        
        # Closed
        mock_connection.is_closed = True
        hc = await queue.health_check()
        assert hc.status == "unhealthy"
