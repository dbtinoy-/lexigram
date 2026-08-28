"""Queue driver registry — registry-based dispatch of queue backends."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from lexigram.queue.backends import (
    InMemoryQueue,
    KafkaQueue,
    RabbitMQQueue,
    RedisQueue,
    SQSQueue,
)
from lexigram.queue.config import (
    KafkaDriverConfig,
    NamedQueueConfig,
    RabbitMQDriverConfig,
    RedisDriverConfig,
    SQSDriverConfig,
)

QueueBuilder = Callable[[NamedQueueConfig], Any]


class QueueDriverRegistry:
    """Registry of queue-backend builders, keyed by driver name.

    A driver name maps to a builder that constructs the corresponding queue
    backend from a :class:`~lexigram.queue.config.NamedQueueConfig`. Unknown
    driver names raise ``ValueError`` to match the historical provider
    behavior.

    Usage::

        registry = QueueDriverRegistry.with_defaults()
        queue = registry.create_backend("redis", entry)
    """

    def __init__(self) -> None:
        """Initialise an empty driver registry."""
        self._builders: dict[str, QueueBuilder] = {}

    @classmethod
    def with_defaults(cls) -> QueueDriverRegistry:
        """Return a registry populated with the built-in queue drivers.

        Returns:
            A :class:`QueueDriverRegistry` pre-registered for memory, redis,
            rabbitmq, kafka, and sqs.
        """
        registry = cls()

        def _memory(_entry: NamedQueueConfig) -> Any:
            return InMemoryQueue()

        def _redis(entry: NamedQueueConfig) -> Any:
            cfg = entry.redis or RedisDriverConfig()
            return RedisQueue(
                url=cfg.url or "redis://localhost:6379/0",
                max_connections=cfg.max_connections,
            )

        def _rabbitmq(entry: NamedQueueConfig) -> Any:
            cfg = entry.rabbitmq or RabbitMQDriverConfig()
            return RabbitMQQueue(
                url=cfg.url or "amqp://guest:guest@localhost/",
                exchange=cfg.exchange,
                prefetch_count=cfg.prefetch_count,
            )

        def _kafka(entry: NamedQueueConfig) -> Any:
            cfg = entry.kafka or KafkaDriverConfig()
            return KafkaQueue(
                bootstrap_servers=cfg.bootstrap_servers or "localhost:9092",
                client_id=cfg.client_id,
                group_id=cfg.group_id,
                auto_offset_reset=cfg.auto_offset_reset,
            )

        def _sqs(entry: NamedQueueConfig) -> Any:
            cfg = entry.sqs or SQSDriverConfig()
            return SQSQueue(
                region=cfg.region,
                queue_url=cfg.queue_url or "",
                visibility_timeout=cfg.visibility_timeout,
            )

        registry.register("memory", _memory)
        registry.register("redis", _redis)
        registry.register("rabbitmq", _rabbitmq)
        registry.register("kafka", _kafka)
        registry.register("sqs", _sqs)
        return registry

    def register(self, driver: str, builder: QueueBuilder) -> None:
        """Register a builder under a driver name.

        Args:
            driver: Driver name (e.g. ``"redis"``).
            builder: Callable ``(NamedQueueConfig) -> Any``.
        """
        self._builders[driver] = builder

    def create_backend(self, driver: str, entry: NamedQueueConfig) -> Any:
        """Build a queue backend for a driver name.

        Args:
            driver: Driver name to dispatch on.
            entry: Config entry used to construct the backend.

        Returns:
            An instantiated queue backend.

        Raises:
            ValueError: If *driver* is not a registered driver.
        """
        builder = self._builders.get(driver)
        if builder is None:
            raise ValueError(f"Unsupported queue driver: {driver!r}")
        return builder(entry)

    def drivers(self) -> list[str]:
        """Return the registered driver names.

        Returns:
            List of driver names in registration order.
        """
        return list(self._builders.keys())

    def __contains__(self, driver: str) -> bool:
        return driver in self._builders


__all__ = ["QueueBuilder", "QueueDriverRegistry"]
