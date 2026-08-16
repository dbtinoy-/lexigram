"""Tests for queue configuration."""
from __future__ import annotations

import pytest

from lexigram.queue.config import (
    AzureServiceBusDriverConfig,
    GCPPubSubDriverConfig,
    KafkaDriverConfig,
    NamedQueueConfig,
    QueueConfig,
    RabbitMQDriverConfig,
    RedisDriverConfig,
    SQSDriverConfig,
)


class TestRedisDriverConfig:
    """Test RedisDriverConfig."""

    def test_defaults(self) -> None:
        """Test default values."""
        cfg = RedisDriverConfig()
        assert cfg.url is None
        assert cfg.max_connections == 10
        assert cfg.socket_timeout == 5.0

    def test_with_url(self) -> None:
        """Test with Redis URL."""
        cfg = RedisDriverConfig()
        cfg.url = "redis://localhost:6379/0"
        assert cfg.url == "redis://localhost:6379/0"


class TestRabbitMQDriverConfig:
    """Test RabbitMQDriverConfig."""

    def test_defaults(self) -> None:
        """Test default values."""
        cfg = RabbitMQDriverConfig()
        assert cfg.url is None
        assert cfg.exchange == "lexigram"
        assert cfg.prefetch_count == 10

    def test_with_url(self) -> None:
        """Test with RabbitMQ URL."""
        cfg = RabbitMQDriverConfig()
        cfg.url = "amqp://guest:guest@localhost:5672/"
        assert cfg.url == "amqp://guest:guest@localhost:5672/"


class TestKafkaDriverConfig:
    """Test KafkaDriverConfig."""

    def test_defaults(self) -> None:
        """Test default values."""
        cfg = KafkaDriverConfig()
        assert cfg.bootstrap_servers is None
        assert cfg.client_id == "lexigram"
        assert cfg.group_id == "lexigram-consumers"
        assert cfg.auto_offset_reset == "latest"

    def test_with_servers(self) -> None:
        """Test with bootstrap servers."""
        cfg = KafkaDriverConfig()
        cfg.bootstrap_servers = "localhost:9092,localhost:9093"
        assert cfg.bootstrap_servers == "localhost:9092,localhost:9093"


class TestSQSDriverConfig:
    """Test SQSDriverConfig."""

    def test_defaults(self) -> None:
        """Test default values."""
        cfg = SQSDriverConfig()
        assert cfg.region == "us-east-1"
        assert cfg.queue_url is None
        assert cfg.visibility_timeout == 30


class TestAzureServiceBusDriverConfig:
    """Test AzureServiceBusDriverConfig."""

    def test_defaults(self) -> None:
        """Test default values."""
        cfg = AzureServiceBusDriverConfig()
        assert cfg.connection_str is None
        assert cfg.queue_name == ""
        assert cfg.max_message_count == 10
        assert cfg.max_wait_time == 5.0

    def test_with_connection_string(self) -> None:
        """Test with connection string."""
        cfg = AzureServiceBusDriverConfig()
        cfg.connection_str = "Endpoint=sb://test.servicebus.windows.net/;SharedAccessKeyName=RootManageSharedAccessKey;SharedAccessKey=abc123"
        assert cfg.connection_str == "Endpoint=sb://test.servicebus.windows.net/;SharedAccessKeyName=RootManageSharedAccessKey;SharedAccessKey=abc123"


class TestGCPPubSubDriverConfig:
    """Test GCPPubSubDriverConfig."""

    def test_defaults(self) -> None:
        """Test default values."""
        cfg = GCPPubSubDriverConfig()
        assert cfg.project_id is None
        assert cfg.topic_id == ""
        assert cfg.subscription_id == ""
        assert cfg.max_messages == 10
        assert cfg.max_wait_time == 5.0

    def test_with_project(self) -> None:
        """Test with GCP project."""
        cfg = GCPPubSubDriverConfig()
        cfg.project_id = "my-project"
        cfg.topic_id = "my-topic"
        cfg.subscription_id = "my-subscription"
        assert cfg.project_id == "my-project"
        assert cfg.topic_id == "my-topic"
        assert cfg.subscription_id == "my-subscription"


class TestNamedQueueConfig:
    """Test NamedQueueConfig."""

    def test_defaults(self) -> None:
        """Test default values."""
        cfg = NamedQueueConfig(name="events", driver="memory")
        assert cfg.name == "events"
        assert cfg.primary is False
        assert cfg.driver == "memory"
        assert cfg.redis is None
        assert cfg.kafka is None
        assert cfg.rabbitmq is None
        assert cfg.sqs is None
        assert cfg.delivery_guarantee == "at_least_once"
        assert cfg.max_retries == 3

    def test_primary_flag(self) -> None:
        """Test primary backend flag."""
        cfg = NamedQueueConfig(name="main", driver="redis", primary=True)
        assert cfg.name == "main"
        assert cfg.driver == "redis"
        assert cfg.primary is True

    def test_with_redis_config(self) -> None:
        """Test with Redis driver config."""
        redis_cfg = RedisDriverConfig(url="redis://localhost:6379")
        cfg = NamedQueueConfig(
            name="cache_queue",
            driver="redis",
            redis=redis_cfg,
        )
        assert cfg.name == "cache_queue"
        assert cfg.driver == "redis"
        assert cfg.redis is not None
        assert cfg.redis.url == "redis://localhost:6379"

    def test_with_kafka_config(self) -> None:
        """Test with Kafka driver config."""
        kafka_cfg = KafkaDriverConfig(bootstrap_servers="localhost:9092")
        cfg = NamedQueueConfig(
            name="events",
            driver="kafka",
            primary=True,
            kafka=kafka_cfg,
        )
        assert cfg.name == "events"
        assert cfg.primary is True
        assert cfg.kafka is not None
        assert cfg.kafka.bootstrap_servers == "localhost:9092"

    def test_with_azure_servicebus_config(self) -> None:
        """Test with Azure Service Bus driver config."""
        azure_cfg = AzureServiceBusDriverConfig(
            connection_str="Endpoint=sb://test.servicebus.windows.net/;SharedAccessKeyName=key;SharedAccessKey=secret",
            queue_name="my-queue",
        )
        cfg = NamedQueueConfig(
            name="azure_queue",
            driver="azure_servicebus",
            azure_servicebus=azure_cfg,
        )
        assert cfg.name == "azure_queue"
        assert cfg.driver == "azure_servicebus"
        assert cfg.azure_servicebus is not None
        assert cfg.azure_servicebus.queue_name == "my-queue"

    def test_with_gcp_pubsub_config(self) -> None:
        """Test with GCP Pub/Sub driver config."""
        gcp_cfg = GCPPubSubDriverConfig(
            project_id="my-project",
            topic_id="my-topic",
            subscription_id="my-subscription",
        )
        cfg = NamedQueueConfig(
            name="gcp_queue",
            driver="gcp_pubsub",
            gcp_pubsub=gcp_cfg,
        )
        assert cfg.name == "gcp_queue"
        assert cfg.driver == "gcp_pubsub"
        assert cfg.gcp_pubsub is not None
        assert cfg.gcp_pubsub.project_id == "my-project"


class TestQueueConfig:
    """Test QueueConfig."""

    def test_empty(self) -> None:
        """Test empty config."""
        cfg = QueueConfig()
        assert cfg.backends == []

    def test_multi_backend(self) -> None:
        """Test multi-backend configuration."""
        # Create individual configs
        mem_cfg = NamedQueueConfig(name="test", driver="memory")

        kafka_cfg = NamedQueueConfig(
            name="events",
            driver="kafka",
            primary=True,
        )

        redis_cfg = NamedQueueConfig(name="jobs", driver="redis")

        # Create queue config with multiple backends
        cfg = QueueConfig(backends=[kafka_cfg, redis_cfg, mem_cfg])

        assert len(cfg.backends) == 3
        assert cfg.backends[0].primary is True
        assert cfg.backends[0].name == "events"
        assert cfg.backends[1].name == "jobs"
        assert cfg.backends[2].name == "test"

    def test_from_named_backend(self) -> None:
        """Test creating config from named backend."""
        named = NamedQueueConfig(
            name="events",
            driver="kafka",
            primary=True,
        )

        cfg = QueueConfig.from_named_backend(named)
        assert len(cfg.backends) == 1
        assert cfg.backends[0].name == "events"
        assert cfg.backends[0].primary is True


__all__ = []
