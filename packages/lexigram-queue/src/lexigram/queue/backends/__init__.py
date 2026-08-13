"""Backend module initialization."""

from __future__ import annotations

from lexigram.queue.backends.azure_servicebus import AzureServiceBusQueue
from lexigram.queue.backends.gcp_pubsub import GCPPubSubQueue
from lexigram.queue.backends.kafka import KafkaQueue
from lexigram.queue.backends.memory import InMemoryQueue
from lexigram.queue.backends.rabbitmq import RabbitMQQueue
from lexigram.queue.backends.redis import RedisQueue
from lexigram.queue.backends.sqs import SQSQueue

__all__ = [
    "AzureServiceBusQueue",
    "GCPPubSubQueue",
    "InMemoryQueue",
    "KafkaQueue",
    "RabbitMQQueue",
    "RedisQueue",
    "SQSQueue",
]
