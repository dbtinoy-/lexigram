from __future__ import annotations

"""Kafka queue provider lifecycle integration tests."""

import pytest

from lexigram.testing.integration.fixtures import kafka_producer  # noqa: F401

pytestmark = [pytest.mark.integration, pytest.mark.requires_kafka]


class TestKafkaProviderLifecycle:
    """Verify QueueProvider can be created and configured for Kafka."""

    async def test_provider_can_be_created(self) -> None:
        """QueueProvider can be instantiated without errors."""
        from lexigram.queue.di.provider import QueueProvider

        provider = QueueProvider()
        assert provider is not None
        assert provider.name == "queue"

    async def test_provider_with_explicit_config(self) -> None:
        """QueueProvider accepts an explicit QueueConfig."""
        from lexigram.queue.config import QueueConfig
        from lexigram.queue.di.provider import QueueProvider

        config = QueueConfig()
        provider = QueueProvider(config=config)
        assert provider is not None

    async def test_kafka_producer_fixture_is_functional(
        self, kafka_producer: object
    ) -> None:
        """kafka_producer fixture yields a live AIOKafkaProducer."""
        assert kafka_producer is not None

    async def test_kafka_producer_can_send(self, kafka_producer: object) -> None:
        """Sending a message via the live Kafka producer succeeds."""
        await kafka_producer.send_and_wait(  # type: ignore[union-attr]
            "lexigram-test-lifecycle",
            b"ping",
        )
