"""Tests for queue exceptions."""
from __future__ import annotations

import pytest

from lexigram.contracts.queue.errors import QueueError
from lexigram.queue.exceptions import (
    AzureServiceBusQueueError,
    GCPPubSubQueueError,
    KafkaQueueError,
    RabbitMQQueueError,
    RedisQueueError,
    SQSQueueError,
)


class TestQueueError:
    """Test base QueueError."""

    def test_defaults(self) -> None:
        """Test default values."""
        err = QueueError("test error")
        assert err.message == "test error"
        assert err.backend == "unknown"
        assert err.topic == "unknown"

    def test_with_backend(self) -> None:
        """Test with backend."""
        err = QueueError("test error", backend="redis")
        assert err.backend == "redis"

    def test_with_topic(self) -> None:
        """Test with topic."""
        err = QueueError("test error", topic="my-queue")
        assert err.topic == "my-queue"

    def test_with_details(self) -> None:
        """Test with details."""
        err = QueueError("test error", details={"key": "value"})
        assert err.details["backend"] == "unknown"
        assert err.details["topic"] == "unknown"
        assert err.details["key"] == "value"


class TestRedisQueueError:
    """Test RedisQueueError."""

    def test_defaults(self) -> None:
        """Test default values."""
        err = RedisQueueError()
        assert err.backend == "redis"
        assert err._code == "LEX_ERR_QUEUE_002"

    def test_custom_message(self) -> None:
        """Test custom message."""
        err = RedisQueueError("Redis connection failed")
        assert "Redis connection failed" in err.message


class TestRabbitMQQueueError:
    """Test RabbitMQQueueError."""

    def test_defaults(self) -> None:
        """Test default values."""
        err = RabbitMQQueueError()
        assert err.backend == "rabbitmq"
        assert err._code == "LEX_ERR_QUEUE_003"

    def test_custom_message(self) -> None:
        """Test custom message."""
        err = RabbitMQQueueError("RabbitMQ channel closed")
        assert "RabbitMQ channel closed" in err.message


class TestKafkaQueueError:
    """Test KafkaQueueError."""

    def test_defaults(self) -> None:
        """Test default values."""
        err = KafkaQueueError()
        assert err.backend == "kafka"
        assert err._code == "LEX_ERR_QUEUE_004"

    def test_custom_message(self) -> None:
        """Test custom message."""
        err = KafkaQueueError("Kafka producer error")
        assert "Kafka producer error" in err.message


class TestSQSQueueError:
    """Test SQSQueueError."""

    def test_defaults(self) -> None:
        """Test default values."""
        err = SQSQueueError()
        assert err.backend == "sqs"
        assert err._code == "LEX_ERR_QUEUE_005"

    def test_custom_message(self) -> None:
        """Test custom message."""
        err = SQSQueueError("SQS message deletion failed")
        assert "SQS message deletion failed" in err.message


class TestAzureServiceBusQueueError:
    """Test AzureServiceBusQueueError."""

    def test_defaults(self) -> None:
        """Test default values."""
        err = AzureServiceBusQueueError()
        assert err.backend == "azure_servicebus"
        assert err._code == "LEX_ERR_QUEUE_006"

    def test_custom_message(self) -> None:
        """Test custom message."""
        err = AzureServiceBusQueueError("Azure Service Bus error")
        assert "Azure Service Bus error" in err.message


class TestGCPPubSubQueueError:
    """Test GCPPubSubQueueError."""

    def test_defaults(self) -> None:
        """Test default values."""
        err = GCPPubSubQueueError()
        assert err.backend == "gcp_pubsub"
        assert err._code == "LEX_ERR_QUEUE_007"

    def test_custom_message(self) -> None:
        """Test custom message."""
        err = GCPPubSubQueueError("GCP Pub/Sub pull failed")
        assert "GCP Pub/Sub pull failed" in err.message


__all__ = []