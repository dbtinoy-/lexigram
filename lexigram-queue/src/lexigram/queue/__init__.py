"""lexigram-queue — message bus/queue with Named DI multi-backend support."""

from __future__ import annotations

from lexigram.contracts.queue.errors import QueueError
from lexigram.contracts.queue.protocols import QueueProtocol
from lexigram.contracts.queue.types import BusMessage
from lexigram.queue.consumers.consumer import MessageConsumer
from lexigram.queue.core.batch_publisher import BatchedPublisher
from lexigram.queue.core.dlq import DeadLetterQueue
from lexigram.queue.core.pipeline import MessagePipeline, MiddlewareBase
from lexigram.queue.events import (
    ConsumerRegisteredEvent,
    MessageConsumedEvent,
    MessageDeadLetteredEvent,
)
from lexigram.queue.exceptions import (
    AzureServiceBusQueueError,
    GCPPubSubQueueError,
    KafkaQueueError,
    RabbitMQQueueError,
    RedisQueueError,
    SQSQueueError,
)
from lexigram.queue.hooks import (
    MessageConsumedHook,
    MessagePublishedHook,
    QueueDrainedHook,
)
from lexigram.queue.module import QueueModule

__all__ = [
    "AzureServiceBusQueueError",
    "BatchedPublisher",
    "BusMessage",
    "ConsumerRegisteredEvent",
    "DeadLetterQueue",
    "GCPPubSubQueueError",
    "KafkaQueueError",
    "MessageConsumedEvent",
    "MessageConsumedHook",
    "MessageConsumer",
    "MessageDeadLetteredEvent",
    "MessagePipeline",
    "MessagePublishedHook",
    "MiddlewareBase",
    "QueueDrainedHook",
    "QueueError",
    "QueueModule",
    "QueueProtocol",
    "RabbitMQQueueError",
    "RedisQueueError",
    "SQSQueueError",
]
