"""Tests for QueueDriverRegistry."""

from __future__ import annotations

import pytest

from lexigram.queue.backends import (
    InMemoryQueue,
    KafkaQueue,
    RabbitMQQueue,
    RedisQueue,
    SQSQueue,
)
from lexigram.queue.config import NamedQueueConfig
from lexigram.queue.drivers.registry import QueueDriverRegistry


def test_registry_has_all_default_drivers() -> None:
    """with_defaults registers the five built-in queue drivers."""
    registry = QueueDriverRegistry.with_defaults()
    assert set(registry.drivers()) == {"memory", "redis", "rabbitmq", "kafka", "sqs"}


def test_create_backend_resolves_expected_classes() -> None:
    """Each driver name dispatches to the matching queue backend."""
    registry = QueueDriverRegistry.with_defaults()
    cases: list[tuple[str, type]] = [
        ("memory", InMemoryQueue),
        ("redis", RedisQueue),
        ("rabbitmq", RabbitMQQueue),
        ("kafka", KafkaQueue),
        ("sqs", SQSQueue),
    ]
    for driver, expected_cls in cases:
        backend = registry.create_backend(
            driver, NamedQueueConfig(name=driver, driver=driver)
        )
        assert isinstance(backend, expected_cls), driver


def test_create_backend_unknown_driver_raises() -> None:
    """An unsupported driver name raises ValueError with the existing message."""
    registry = QueueDriverRegistry.with_defaults()
    with pytest.raises(ValueError, match=r"Unsupported queue driver: 'bogus'"):
        registry.create_backend("bogus", NamedQueueConfig(name="bogus", driver="bogus"))
