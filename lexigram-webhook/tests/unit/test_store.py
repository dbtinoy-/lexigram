"""Tests for InMemoryWebhookStore."""

from __future__ import annotations
from enum import Enum

from datetime import UTC, datetime, timedelta

import pytest

from lexigram.contracts.webhook.types import (
    DeliveryAttempt,
    DeliveryStatus,
    WebhookSubscription,
)
from lexigram.webhook.store.memory import InMemoryWebhookStore


def _make_sub(
    sub_id: str = "sub-1",
    url: str = "https://example.com/webhook",
    active: bool = True,
    event_types: frozenset[str] | None = None,
    tenant_id: str | None = None,
) -> WebhookSubscription:
    return WebhookSubscription(
        subscription_id=sub_id,
        url=url,
        secret="secret",
        event_types=event_types,
        active=active,
        tenant_id=tenant_id,
    )


def _make_attempt(
    attempt_id: str = "att-1",
    sub_id: str = "sub-1",
    event_id: str = "evt-1",
    status: DeliveryStatus = DeliveryStatus.DELIVERED,
    attempted_at: datetime | None = None,
) -> DeliveryAttempt:
    return DeliveryAttempt(
        attempt_id=attempt_id,
        subscription_id=sub_id,
        event_id=event_id,
        event_type="user.created",
        status=status,
        attempted_at=attempted_at or datetime.now(UTC),
    )


class TestInMemoryWebhookStore:
    """Tests for InMemoryWebhookStore."""

    @pytest.mark.asyncio
    async def test_create_and_get(self, store: InMemoryWebhookStore) -> None:
        """create() then get() returns the same subscription."""
        sub = _make_sub("sub-1")
        await store.create(sub)
        result = await store.get("sub-1")
        assert result is not None
        assert result.subscription_id == "sub-1"

    @pytest.mark.asyncio
    async def test_get_missing_returns_none(
        self, store: InMemoryWebhookStore
    ) -> None:
        """get() returns None for unknown subscription_id."""
        assert await store.get("nonexistent") is None

    @pytest.mark.asyncio
    async def test_list_active_only(self, store: InMemoryWebhookStore) -> None:
        """list() with active_only=True excludes inactive subscriptions."""
        await store.create(_make_sub("s1", active=True))
        await store.create(_make_sub("s2", active=False))
        results = await store.list(active_only=True)
        ids = {r.subscription_id for r in results}
        assert "s1" in ids
        assert "s2" not in ids

    @pytest.mark.asyncio
    async def test_list_all_when_active_only_false(
        self, store: InMemoryWebhookStore
    ) -> None:
        """list() with active_only=False returns all subscriptions."""
        await store.create(_make_sub("s1", active=True))
        await store.create(_make_sub("s2", active=False))
        results = await store.list(active_only=False)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_list_filter_by_event_type(
        self, store: InMemoryWebhookStore
    ) -> None:
        """list() event_type filter excludes non-matching subscriptions."""
        await store.create(_make_sub("s1", event_types=frozenset({"user.created"})))
        await store.create(_make_sub("s2", event_types=frozenset({"order.placed"})))
        await store.create(_make_sub("s3"))  # None = all events

        results = await store.list(event_type="user.created")
        ids = {r.subscription_id for r in results}
        assert "s1" in ids
        assert "s2" not in ids
        assert "s3" in ids  # None event_types matches everything

    @pytest.mark.asyncio
    async def test_list_filter_by_tenant(
        self, store: InMemoryWebhookStore
    ) -> None:
        """list() tenant_id filter returns only matching subscriptions."""
        await store.create(_make_sub("s1", tenant_id="tenant-a"))
        await store.create(_make_sub("s2", tenant_id="tenant-b"))
        results = await store.list(tenant_id="tenant-a")
        ids = {r.subscription_id for r in results}
        assert "s1" in ids
        assert "s2" not in ids

    @pytest.mark.asyncio
    async def test_update(self, store: InMemoryWebhookStore) -> None:
        """update() replaces the stored subscription."""
        sub = _make_sub("s1", active=True)
        await store.create(sub)
        updated = WebhookSubscription(
            subscription_id="s1",
            url=sub.url,
            secret=sub.secret,
            active=False,
        )
        await store.update(updated)
        result = await store.get("s1")
        assert result is not None
        assert result.active is False

    @pytest.mark.asyncio
    async def test_delete(self, store: InMemoryWebhookStore) -> None:
        """delete() removes the subscription."""
        await store.create(_make_sub("s1"))
        await store.delete("s1")
        assert await store.get("s1") is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_is_noop(
        self, store: InMemoryWebhookStore
    ) -> None:
        """delete() on unknown id does not raise."""
        await store.delete("nonexistent")  # should not raise

    # --- Delivery attempts ---

    @pytest.mark.asyncio
    async def test_record_and_get_attempts(
        self, store: InMemoryWebhookStore
    ) -> None:
        """record_attempt() then get_attempts() returns the attempt."""
        attempt = _make_attempt("att-1", status=DeliveryStatus.DELIVERED)
        await store.record_attempt(attempt)
        results = await store.get_attempts()
        assert len(results) == 1
        assert results[0].attempt_id == "att-1"

    @pytest.mark.asyncio
    async def test_get_attempts_filter_by_status(
        self, store: InMemoryWebhookStore
    ) -> None:
        """get_attempts() status filter works."""
        await store.record_attempt(_make_attempt("a1", status=DeliveryStatus.DELIVERED))
        await store.record_attempt(_make_attempt("a2", status=DeliveryStatus.FAILED))
        results = await store.get_attempts(status=DeliveryStatus.FAILED)
        assert all(r.status == DeliveryStatus.FAILED for r in results)
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_get_dead_letters(self, store: InMemoryWebhookStore) -> None:
        """get_dead_letters() returns only DEAD_LETTER attempts."""
        await store.record_attempt(
            _make_attempt("a1", status=DeliveryStatus.DEAD_LETTER)
        )
        await store.record_attempt(_make_attempt("a2", status=DeliveryStatus.FAILED))
        results = await store.get_dead_letters()
        assert len(results) == 1
        assert results[0].status == DeliveryStatus.DEAD_LETTER

    @pytest.mark.asyncio
    async def test_count_recent_failures(self, store: InMemoryWebhookStore) -> None:
        """count_recent_failures() counts FAILED attempts within the time window."""
        now = datetime.now(UTC)
        old = now - timedelta(hours=48)
        recent = now - timedelta(minutes=30)

        await store.record_attempt(
            _make_attempt("a1", status=DeliveryStatus.FAILED, attempted_at=recent)
        )
        await store.record_attempt(
            _make_attempt("a2", status=DeliveryStatus.FAILED, attempted_at=old)
        )
        await store.record_attempt(
            _make_attempt("a3", status=DeliveryStatus.DELIVERED, attempted_at=recent)
        )

        since = now - timedelta(hours=1)
        count = await store.count_recent_failures("sub-1", since=since)
        assert count == 1
