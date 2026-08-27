"""QueueConfig following the config-system standard."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from lexigram.config.base import BaseConfig
from lexigram.contracts.core.config import Environment
from lexigram.domain import DomainModel
from lexigram.queue.constants import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_VISIBILITY_TIMEOUT,
)
from lexigram.validation import ConfigDict, Field


@dataclass(init=False)
class RedisDriverConfig(DomainModel):
    """Redis queue driver configuration."""

    url: str | None = Field(
        default=None,
        description="Redis connection URL (redis://host:port/db)",
    )
    max_connections: int = Field(
        default=10,
        ge=1,
        description="Maximum connection pool size",
    )
    socket_timeout: float = Field(
        default=5.0,
        gt=0.0,
        description="Socket timeout in seconds",
    )


@dataclass(init=False)
class RabbitMQDriverConfig(DomainModel):
    """RabbitMQ queue driver configuration."""

    url: str | None = Field(
        default=None,
        description="RabbitMQ connection URL (amqp://user:pass@host:port/)",
    )
    exchange: str = Field(
        default="lexigram",
        description="RabbitMQ exchange name",
    )
    prefetch_count: int = Field(
        default=10,
        ge=1,
        description="Consumer prefetch count",
    )


@dataclass(init=False)
class KafkaDriverConfig(DomainModel):
    """Kafka queue driver configuration."""

    bootstrap_servers: str | None = Field(
        default=None,
        description="Kafka bootstrap servers (comma-separated: host:port,host:port)",
    )
    client_id: str = Field(
        default="lexigram",
        description="Kafka client ID",
    )
    group_id: str = Field(
        default="lexigram-consumers",
        description="Kafka consumer group ID",
    )
    auto_offset_reset: str = Field(
        default="latest",
        description="Consumer offset reset strategy (earliest or latest)",
    )


@dataclass(init=False)
class SQSDriverConfig(DomainModel):
    """AWS SQS queue driver configuration."""

    region: str = Field(
        default="us-east-1",
        description="AWS region",
    )
    queue_url: str | None = Field(
        default=None,
        description="SQS queue URL",
    )
    visibility_timeout: int = Field(
        default=DEFAULT_VISIBILITY_TIMEOUT,
        ge=0,
        description="Message visibility timeout in seconds",
    )


@dataclass(init=False)
class AzureServiceBusDriverConfig(DomainModel):
    """Azure Service Bus queue driver configuration."""

    connection_str: str | None = Field(
        default=None,
        description="Azure Service Bus connection string",
    )
    queue_name: str = Field(
        default="",
        description="Azure Service Bus queue name",
    )
    max_message_count: int = Field(
        default=10,
        ge=1,
        description="Maximum messages fetched per receive call",
    )
    max_wait_time: float = Field(
        default=5.0,
        gt=0.0,
        description="Maximum wait time in seconds per receive call",
    )


@dataclass(init=False)
class GCPPubSubDriverConfig(DomainModel):
    """Google Cloud Pub/Sub queue driver configuration."""

    project_id: str | None = Field(
        default=None,
        description="GCP project ID",
    )
    topic_id: str = Field(
        default="",
        description="Pub/Sub topic ID",
    )
    subscription_id: str = Field(
        default="",
        description="Pub/Sub subscription ID for consuming messages",
    )
    max_messages: int = Field(
        default=10,
        ge=1,
        description="Maximum messages fetched per pull call",
    )
    max_wait_time: float = Field(
        default=5.0,
        gt=0.0,
        description="gRPC call timeout in seconds for pull requests",
    )


@dataclass(init=False)
class NamedQueueConfig(DomainModel):
    """Configuration for a single named queue backend.

    Used in QueueConfig.backends to declare multiple queue backends
    that the framework registers as named DI bindings.

    Example:
        backends:
          - name: events
            driver: kafka
            primary: true
            kafka:
              bootstrap_servers: localhost:9092

    Args:
        name: Unique backend identifier. Used as the Named() DI key.
        primary: Whether this is the primary backend. Primary backends
            also receive the unnamed QueueProtocol binding.
        driver: Queue driver. One of 'memory', 'redis', 'rabbitmq', 'kafka', 'sqs',
            'azure_servicebus', 'gcp_pubsub'.
        delivery_guarantee: Delivery semantics for messages. Default is 'at_least_once'.
        max_retries: Maximum retries before routing to DLQ.
        redis: Redis-specific config.
        rabbitmq: RabbitMQ-specific config.
        kafka: Kafka-specific config.
        sqs: SQS-specific config.
        azure_servicebus: Azure Service Bus-specific config.
        gcp_pubsub: GCP Pub/Sub-specific config.
    """

    name: str = Field(..., description="Unique backend name used as the Named() DI key")
    primary: bool = Field(
        default=False,
        description="Also register under unnamed QueueProtocol binding",
    )
    driver: str = Field(default="memory", description="Queue driver name")
    delivery_guarantee: str = Field(
        default="at_least_once",
        description="Delivery guarantee strategy",
    )
    max_retries: int = Field(
        default=DEFAULT_MAX_RETRIES,
        ge=0,
        description="Maximum retries before DLQ",
    )
    redis: RedisDriverConfig | None = Field(
        default=None,
        description="Redis driver config",
    )
    rabbitmq: RabbitMQDriverConfig | None = Field(
        default=None,
        description="RabbitMQ driver config",
    )
    kafka: KafkaDriverConfig | None = Field(
        default=None,
        description="Kafka driver config",
    )
    sqs: SQSDriverConfig | None = Field(
        default=None,
        description="SQS driver config",
    )
    azure_servicebus: AzureServiceBusDriverConfig | None = Field(
        default=None,
        description="Azure Service Bus driver config",
    )
    gcp_pubsub: GCPPubSubDriverConfig | None = Field(
        default=None,
        description="GCP Pub/Sub driver config",
    )


@dataclass(init=False)
class QueueConfig(BaseConfig):
    """Top-level queue configuration.

    Loaded from the ``queue:`` key in application.yaml, with environment
    variable overrides via ``LEX_QUEUE__*`` prefix.
    """

    config_section: ClassVar[str] = "queue"

    model_config: ClassVar[ConfigDict] = ConfigDict(
        extra="ignore",
    )

    name: str = "queue"
    enabled: bool = True
    env: Environment | None = Field(None, description="Deployment environment")

    backends: list[NamedQueueConfig] = Field(
        default_factory=list,
        description=(
            "Named queue backends for multi-backend support. "
            "When non-empty, the provider registers each backend under "
            "Annotated[QueueProtocol, Named(entry.name)]. "
            "The first entry (or the one with primary=True) also receives "
            "the unnamed QueueProtocol binding for backward compatibility."
        ),
    )

    @classmethod
    def from_named_backend(cls, entry: NamedQueueConfig) -> QueueConfig:
        """Build a single-backend QueueConfig from a NamedQueueConfig entry.

        Used internally by QueueProvider to create per-backend configs
        from a multi-backend declaration.

        Args:
            entry: The named queue backend entry to materialise.

        Returns:
            A QueueConfig configured for the single named queue backend.
        """
        return cls(backends=[entry])


__all__ = [
    "AzureServiceBusDriverConfig",
    "GCPPubSubDriverConfig",
    "KafkaDriverConfig",
    "NamedQueueConfig",
    "QueueConfig",
    "RabbitMQDriverConfig",
    "RedisDriverConfig",
    "SQSDriverConfig",
]
