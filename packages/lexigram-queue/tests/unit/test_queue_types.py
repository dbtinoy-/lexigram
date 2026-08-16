"""Unit tests for queue types."""

from __future__ import annotations

import time
import uuid
from unittest.mock import patch

import pytest

from lexigram.queue.types import BusMessage, DeliveryGuarantee


class TestDeliveryGuarantee:
    """Tests for DeliveryGuarantee enum."""

    def test_enum_values(self) -> None:
        """Verify enum member values."""
        assert DeliveryGuarantee.AT_MOST_ONCE.value == "at_most_once"
        assert DeliveryGuarantee.AT_LEAST_ONCE.value == "at_least_once"
        assert DeliveryGuarantee.EXACTLY_ONCE.value == "exactly_once"

    def test_enum_is_strenum(self) -> None:
        """Verify enum inherits from StrEnum."""
        assert isinstance(DeliveryGuarantee.AT_LEAST_ONCE, str)

    def test_enum_members(self) -> None:
        """Verify all expected members exist."""
        members = list(DeliveryGuarantee)
        assert len(members) == 3
        assert DeliveryGuarantee.AT_MOST_ONCE in members
        assert DeliveryGuarantee.AT_LEAST_ONCE in members
        assert DeliveryGuarantee.EXACTLY_ONCE in members


class TestBusMessage:
    """Tests for BusMessage dataclass."""

    def test_default_values(self) -> None:
        """Verify default field values."""
        msg = BusMessage(topic="test-topic", payload={"key": "value"})
        assert msg.id is not None
        assert isinstance(msg.id, str)
        uuid.UUID(msg.id)  # Valid UUID
        assert msg.topic == "test-topic"
        assert msg.payload == {"key": "value"}
        assert msg.headers == {}
        assert msg.timestamp is not None
        assert msg.ttl is None
        assert msg.priority == 0
        assert msg.delivery_guarantee == DeliveryGuarantee.AT_LEAST_ONCE
        assert msg.retry_count == 0
        assert msg.max_retries == 3

    def test_custom_values(self) -> None:
        """Verify custom field values."""
        msg = BusMessage(
            id="custom-id",
            topic="custom-topic",
            payload={"data": 123},
            headers={"x-correlation-id": "abc123"},
            timestamp=1000.0,
            ttl=60.0,
            priority=5,
            delivery_guarantee=DeliveryGuarantee.EXACTLY_ONCE,
            retry_count=2,
            max_retries=10,
        )
        assert msg.id == "custom-id"
        assert msg.topic == "custom-topic"
        assert msg.payload == {"data": 123}
        assert msg.headers == {"x-correlation-id": "abc123"}
        assert msg.timestamp == 1000.0
        assert msg.ttl == 60.0
        assert msg.priority == 5
        assert msg.delivery_guarantee == DeliveryGuarantee.EXACTLY_ONCE
        assert msg.retry_count == 2
        assert msg.max_retries == 10

    def test_is_expired_no_ttl(self) -> None:
        """Verify is_expired returns False when ttl is None."""
        msg = BusMessage(topic="test", ttl=None)
        assert msg.is_expired() is False

    def test_is_expired_not_expired(self) -> None:
        """Verify is_expired returns False when TTL not elapsed."""
        msg = BusMessage(topic="test", timestamp=time.time(), ttl=3600.0)
        assert msg.is_expired() is False

    def test_is_expired_expired(self) -> None:
        """Verify is_expired returns True when TTL elapsed."""
        msg = BusMessage(topic="test", timestamp=0.0, ttl=1.0)
        assert msg.is_expired() is True

    def test_should_retry_false_when_max_retries_exceeded(self) -> None:
        """Verify should_retry returns False when retry_count >= max_retries."""
        msg = BusMessage(topic="test", retry_count=5, max_retries=3)
        assert msg.should_retry() is False

    def test_should_retry_false_when_expired(self) -> None:
        """Verify should_retry returns False when message is expired."""
        msg = BusMessage(topic="test", timestamp=0.0, ttl=1.0, retry_count=0, max_retries=3)
        assert msg.should_retry() is False

    def test_should_retry_true(self) -> None:
        """Verify should_retry returns True when valid."""
        msg = BusMessage(topic="test", retry_count=0, max_retries=3, ttl=None)
        assert msg.should_retry() is True

    def test_id_is_uuid(self) -> None:
        """Verify default ID is a valid UUID."""
        msg = BusMessage(topic="test")
        uuid.UUID(msg.id)  # Raises if invalid

    def test_headers_default_is_dict(self) -> None:
        """Verify headers default is a mutable dict that doesn't share state."""
        msg1 = BusMessage(topic="test1")
        msg2 = BusMessage(topic="test2")
        msg1.headers["new"] = "value"
        assert "new" not in msg2.headers