"""lexigram-queue leaf exceptions."""

from __future__ import annotations

from typing import Any

from lexigram.contracts.queue.errors import QueueError


class RedisQueueError(QueueError):
    """Redis queue failure."""

    _code = "LEX_ERR_QUEUE_002"

    def __init__(self, message: str = "Redis queue error", **kwargs: Any) -> None:
        super().__init__(message, backend="redis", **kwargs)


class RabbitMQQueueError(QueueError):
    """RabbitMQ queue failure."""

    _code = "LEX_ERR_QUEUE_003"

    def __init__(self, message: str = "RabbitMQ error", **kwargs: Any) -> None:
        super().__init__(message, backend="rabbitmq", **kwargs)


class KafkaQueueError(QueueError):
    """Kafka queue failure."""

    _code = "LEX_ERR_QUEUE_004"

    def __init__(self, message: str = "Kafka error", **kwargs: Any) -> None:
        super().__init__(message, backend="kafka", **kwargs)


class SQSQueueError(QueueError):
    """SQS queue failure."""

    _code = "LEX_ERR_QUEUE_005"

    def __init__(self, message: str = "SQS error", **kwargs: Any) -> None:
        super().__init__(message, backend="sqs", **kwargs)


class AzureServiceBusQueueError(QueueError):
    """Azure Service Bus queue failure."""

    _code = "LEX_ERR_QUEUE_006"

    def __init__(self, message: str = "Azure Service Bus error", **kwargs: Any) -> None:
        super().__init__(message, backend="azure_servicebus", **kwargs)


class GCPPubSubQueueError(QueueError):
    """GCP Pub/Sub queue failure."""

    _code = "LEX_ERR_QUEUE_007"

    def __init__(self, message: str = "GCP Pub/Sub error", **kwargs: Any) -> None:
        super().__init__(message, backend="gcp_pubsub", **kwargs)


__all__ = [
    "AzureServiceBusQueueError",
    "GCPPubSubQueueError",
    "KafkaQueueError",
    "RabbitMQQueueError",
    "RedisQueueError",
    "SQSQueueError",
]
