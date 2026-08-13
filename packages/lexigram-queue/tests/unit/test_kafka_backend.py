"""Tests for Kafka queue backend."""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
import sys

# Setup sys.modules for aiokafka
mock_aiokafka = MagicMock()
sys.modules["aiokafka"] = mock_aiokafka

from lexigram.queue.backends.kafka import KafkaQueue
from lexigram.contracts.queue.types import BusMessage
from lexigram.contracts.core.health import HealthStatus


@pytest.fixture
def mock_producer():
    """Fixture for a mocked Kafka producer."""
    producer = AsyncMock()
    producer.start = AsyncMock()
    producer.stop = AsyncMock()
    producer.send_and_wait = AsyncMock()
    producer._closed = False
    return producer


@pytest.fixture
def mock_consumer():
    """Fixture for a mocked Kafka consumer."""
    # We use a regular MagicMock because we want to control __aiter__ manually
    consumer = MagicMock()
    consumer.start = AsyncMock()
    consumer.stop = AsyncMock()
    consumer.subscribe = MagicMock()
    consumer.pause = AsyncMock()
    consumer.resume = AsyncMock()
    consumer.assignment = MagicMock(return_value=[])
    
    return consumer


@pytest.mark.asyncio
async def test_kafka_queue_connect_disconnect(mock_producer, mock_consumer):
    """Test connect and close."""
    mock_aiokafka.AIOKafkaProducer.return_value = mock_producer
    mock_aiokafka.AIOKafkaConsumer.return_value = mock_consumer
    
    queue = KafkaQueue(bootstrap_servers="localhost:9092")
    await queue.connect()
    
    mock_producer.start.assert_called_once()
    mock_consumer.start.assert_called_once()
    
    await queue.close()
    mock_producer.stop.assert_called_once()
    mock_consumer.stop.assert_called_once()


@pytest.mark.asyncio
async def test_kafka_queue_publish(mock_producer):
    """Test publishing a message."""
    mock_aiokafka.AIOKafkaProducer.return_value = mock_producer
    
    queue = KafkaQueue()
    await queue.connect()
    
    msg = BusMessage(topic="test", payload={"data": "hi"})
    await queue.publish("test", msg)
    
    mock_producer.send_and_wait.assert_called_once()
    call_args = mock_producer.send_and_wait.call_args
    assert call_args[0][0] == "test"
    # value is encoded JSON
    assert b"hi" in call_args[1]["value"]


@pytest.mark.asyncio
async def test_kafka_queue_subscribe(mock_consumer):
    """Test subscribing and receiving a message."""
    mock_aiokafka.AIOKafkaConsumer.return_value = mock_consumer
    
    # Mock a single record
    mock_record = MagicMock()
    mock_record.value = b'{"id": "msg-123", "payload": "msg1", "topic": "t1"}'
    mock_record.headers = []
    
    # Setup async iterator
    async def async_iter():
        yield mock_record
        # Stay alive but don't yield more
        while True:
            await asyncio.sleep(0.1)
            
    mock_consumer.__aiter__.side_effect = lambda: async_iter()
    
    queue = KafkaQueue()
    await queue.connect()
    
    handler_called = asyncio.Event()
    async def handler(msg):
        if msg.payload == "msg1":
            handler_called.set()
        
    await queue.subscribe("t1", handler)
    
    # Wait for background task to process the message
    await asyncio.wait_for(handler_called.wait(), timeout=2.0)
    assert handler_called.is_set()
    
    # Cleanup
    await queue.close()


@pytest.mark.asyncio
async def test_kafka_queue_health_check(mock_producer, mock_consumer):
    """Test health check."""
    mock_aiokafka.AIOKafkaProducer.return_value = mock_producer
    mock_aiokafka.AIOKafkaConsumer.return_value = mock_consumer
    
    queue = KafkaQueue()
    # Not connected
    result = await queue.health_check()
    assert result.status == HealthStatus.UNHEALTHY
    
    await queue.connect()
    mock_producer._closed = False
    result = await queue.health_check()
    assert result.status == HealthStatus.HEALTHY
    
    mock_producer._closed = True
    result = await queue.health_check()
    assert result.status == HealthStatus.UNHEALTHY
