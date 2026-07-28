"""Tests for SQS queue backend."""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
import sys

# Mock aiobotocore before it's used
mock_aiobotocore = MagicMock()
sys.modules["aiobotocore"] = mock_aiobotocore
sys.modules["aiobotocore.session"] = mock_aiobotocore.session

from lexigram.queue.backends.sqs import SQSQueue
from lexigram.contracts.queue.types import BusMessage


@pytest.mark.asyncio
async def test_sqs_queue_connect_disconnect():
    """Test connect and close."""
    mock_session = mock_aiobotocore.session.get_session.return_value
    mock_client = AsyncMock()
    mock_session.client.return_value = mock_client
    
    queue = SQSQueue(queue_url="https://sqs.us-east-1.amazonaws.com/123/test")
    await queue.connect()
    
    mock_session.client.assert_called_with("sqs", region_name="us-east-1")
    
    await queue.close()
    # close calls __aexit__
    mock_client.__aexit__.assert_called_once()

@pytest.mark.asyncio
async def test_sqs_queue_publish():
    """Test publishing a message."""
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    
    queue = SQSQueue(queue_url="url")
    queue._client = mock_client
    
    msg = BusMessage(topic="test", payload={"data": "hi"})
    await queue.publish("test", msg)
    
    mock_client.send_message.assert_called_once()
    args, kwargs = mock_client.send_message.call_args
    assert kwargs["QueueUrl"] == "url"
    # payload is bytes, so we check for bytes or decode it
    body = kwargs["MessageBody"]
    if isinstance(body, bytes):
        body = body.decode("utf-8")
    assert '"payload":{"data":"hi"}' in body.replace(" ", "")

@pytest.mark.asyncio
async def test_sqs_queue_subscribe():
    """Test subscribing and receiving a message."""
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    
    # Mock receive_message
    # First call returns a message, second call hangs until cancelled to simulate background polling
    async def receive_side_effect(*args, **kwargs):
        if receive_side_effect.called:
            await asyncio.sleep(10) # Simulate long poll
            return {}
        receive_side_effect.called = True
        return {"Messages": [{"Body": '{"payload": "msg1", "topic": "test"}', "ReceiptHandle": "rh1"}]}
    
    receive_side_effect.called = False
    mock_client.receive_message.side_effect = receive_side_effect
    
    queue = SQSQueue(queue_url="url")
    queue._client = mock_client
    
    handler_called = asyncio.Event()
    async def handler(msg):
        if msg.payload == "msg1":
            handler_called.set()
        
    await queue.subscribe("test", handler)
    
    # Wait for background task to process the message
    await asyncio.wait_for(handler_called.wait(), timeout=2.0)
    
    # delete_message should be called
    mock_client.delete_message.assert_called_with(QueueUrl="url", ReceiptHandle="rh1")
    
    # Cleanup
    await queue.close()

@pytest.mark.asyncio
async def test_sqs_queue_health_check():
    """Test health check."""
    queue = SQSQueue(queue_url="url")
    # Not connected
    result = await queue.health_check()
    assert result.status == "unhealthy"
    
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    
    queue._client = mock_client
    result = await queue.health_check()
    assert result.status == "healthy"
    
    mock_client.get_queue_attributes.side_effect = Exception("aws error")
    result = await queue.health_check()
    assert result.status == "unhealthy"
