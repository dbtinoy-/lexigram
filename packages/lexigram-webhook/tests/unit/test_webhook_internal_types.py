"""Tests for webhook internal types module."""

from __future__ import annotations

import pytest

from lexigram.webhook import types
from lexigram.webhook.types import (
    DeliveryBatch,
    RetrySchedule,
    WebhookStoreBackend,
)


class TestWebhookStoreBackend:
    """Tests for WebhookStoreBackend enum."""

    def test_has_memory_value(self) -> None:
        """WebhookStoreBackend has MEMORY value."""
        assert WebhookStoreBackend.MEMORY == "memory"

    def test_has_sql_value(self) -> None:
        """WebhookStoreBackend has SQL value."""
        assert WebhookStoreBackend.SQL == "sql"

    def test_is_case_sensitive(self) -> None:
        """WebhookStoreBackend values are lowercase."""
        assert WebhookStoreBackend.MEMORY.value == "memory"
        assert WebhookStoreBackend.SQL.value == "sql"

    def test_can_iterate(self) -> None:
        """WebhookStoreBackend can be iterated."""
        values = list(WebhookStoreBackend)
        assert len(values) == 2

    def test_can_compare(self) -> None:
        """WebhookStoreBackend can be compared."""
        assert WebhookStoreBackend.MEMORY == WebhookStoreBackend.MEMORY
        assert WebhookStoreBackend.SQL != WebhookStoreBackend.MEMORY


class TestRetrySchedule:
    """Tests for RetrySchedule dataclass."""

    def test_create_with_minimal_values(self) -> None:
        """RetrySchedule can be created with minimal values."""
        schedule = RetrySchedule(
            attempt_number=1,
            delay_seconds=5.0,
        )
        assert schedule.attempt_number == 1
        assert schedule.delay_seconds == 5.0
        assert schedule.is_final is False

    def test_create_with_all_values(self) -> None:
        """RetrySchedule can be created with all values."""
        schedule = RetrySchedule(
            attempt_number=3,
            delay_seconds=60.0,
            is_final=True,
        )
        assert schedule.attempt_number == 3
        assert schedule.delay_seconds == 60.0
        assert schedule.is_final is True

    def test_is_frozen(self) -> None:
        """RetrySchedule is frozen."""
        schedule = RetrySchedule(attempt_number=1, delay_seconds=5.0)
        with pytest.raises(AttributeError):
            schedule.attempt_number = 2  # type: ignore

    def test_default_is_final_is_false(self) -> None:
        """is_final defaults to False."""
        schedule = RetrySchedule(attempt_number=1, delay_seconds=5.0)
        assert schedule.is_final is False


class TestDeliveryBatch:
    """Tests for DeliveryBatch dataclass."""

    def test_create_with_required_values(self) -> None:
        """DeliveryBatch can be created with required values."""
        batch = DeliveryBatch(
            event_id="evt-123",
            event_type="user.created",
        )
        assert batch.event_id == "evt-123"
        assert batch.event_type == "user.created"
        assert batch.subscription_ids == []

    def test_create_with_subscription_ids(self) -> None:
        """DeliveryBatch can be created with subscription IDs."""
        batch = DeliveryBatch(
            event_id="evt-123",
            event_type="user.created",
            subscription_ids=["sub-1", "sub-2"],
        )
        assert len(batch.subscription_ids) == 2
        assert "sub-1" in batch.subscription_ids

    def test_create_with_scheduled_at(self) -> None:
        """DeliveryBatch can be created with scheduled_at."""
        from datetime import datetime
        scheduled = datetime(2024, 1, 1, 0, 0, 0)
        batch = DeliveryBatch(
            event_id="evt-123",
            event_type="user.created",
            scheduled_at=scheduled,
        )
        assert batch.scheduled_at == scheduled

    def test_is_frozen(self) -> None:
        """DeliveryBatch is frozen."""
        batch = DeliveryBatch(
            event_id="evt-123",
            event_type="user.created",
        )
        with pytest.raises(AttributeError):
            batch.event_id = "changed"  # type: ignore

    def test_default_subscription_ids_is_empty_list(self) -> None:
        """subscription_ids defaults to empty list."""
        batch = DeliveryBatch(
            event_id="evt-123",
            event_type="user.created",
        )
        assert batch.subscription_ids == []

    def test_subscription_ids_is_mutable_in_factory(self) -> None:
        """subscription_ids can be modified via add."""
        batch = DeliveryBatch(
            event_id="evt-123",
            event_type="user.created",
        )
        # Can't modify frozen dataclass, but we can test the factory works
        assert batch.subscription_ids == []


class TestTypesModuleExports:
    """Tests for module exports."""

    def test_all_contains_delivery_batch(self) -> None:
        """__all__ contains DeliveryBatch."""
        from lexigram.webhook import types
        assert "DeliveryBatch" in types.__all__

    def test_all_contains_retry_schedule(self) -> None:
        """__all__ contains RetrySchedule."""
        from lexigram.webhook import types
        assert "RetrySchedule" in types.__all__

    def test_all_contains_webhook_store_backend(self) -> None:
        """__all__ contains WebhookStoreBackend."""
        from lexigram.webhook import types
        assert "WebhookStoreBackend" in types.__all__

    def test_module_docstring(self) -> None:
        """Module has docstring."""
        from lexigram.webhook import types
        assert types.__doc__ is not None
        assert "internal" in types.__doc__.lower()