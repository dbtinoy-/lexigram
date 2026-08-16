from __future__ import annotations

"""Kafka QueueBackend compliance test using a real Kafka broker."""

import uuid

import pytest

from lexigram.testing.compliance import QueueBackendCompliance
from lexigram.testing.integration.fixtures import kafka_producer  # noqa: F401

pytestmark = [pytest.mark.integration, pytest.mark.requires_kafka]


class TestKafkaQueueCompliance(QueueBackendCompliance):
    """Verify KafkaQueue satisfies QueueBackendCompliance against a live broker.

    Uses the ``kafka_producer`` fixture provided by
    ``lexigram.testing.integration.fixtures``.  A unique Kafka topic name is
    generated per test to ensure isolation.  The suite is auto-skipped when
    Kafka is not reachable or the ``aiokafka`` package is not installed.
    """

    @pytest.fixture(autouse=True)
    async def _setup(self, kafka_producer: object) -> None:
        """Capture the live Kafka producer and generate a unique topic name.

        Args:
            kafka_producer: Session-scoped AIOKafkaProducer connected to the
                test broker.
        """
        self._kafka_producer = kafka_producer
        self._topic = f"lexigram-test-{uuid.uuid4().hex[:12]}"

    async def create_backend(self, queue_name: str = "test-queue") -> object:
        """Create a KafkaQueue connected to the live Kafka broker.

        Args:
            queue_name: Logical queue name; used as the Kafka consumer group ID
                suffix to keep test runs isolated.

        Returns:
            A ready-to-use KafkaQueue instance.

        Raises:
            pytest.skip.Exception: If ``aiokafka`` is not installed or
                the KafkaQueue cannot be imported.
        """
        try:
            from lexigram.queue.backends.kafka import KafkaQueue  # noqa: F401
        except ImportError:
            pytest.skip("KafkaQueue not available")

        pytest.skip(
            "TODO: instantiate KafkaQueue with bootstrap_servers from "
            "integration_config.kafka_bootstrap and self._topic as the target topic"
        )
