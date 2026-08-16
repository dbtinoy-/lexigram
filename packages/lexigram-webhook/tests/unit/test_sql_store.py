"""Unit tests for SqlWebhookSubscriptionStore and SqlWebhookDeliveryStore."""

from __future__ import annotations
from enum import Enum

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.contracts.data.sql.database import DatabaseProviderProtocol, QueryResult
from lexigram.contracts.webhook.types import (
    DeliveryAttempt,
    DeliveryStatus,
    WebhookSubscription,
)
from lexigram.webhook.store.sql import (
    SqlWebhookDeliveryStore,
    SqlWebhookSubscriptionStore,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_db(rows: list[dict[str, Any]] | None = None, *, success: bool = True) -> MagicMock:
    """Build a mock DatabaseProviderProtocol with configurable query result."""
    db = MagicMock(spec=DatabaseProviderProtocol)
    result = QueryResult(rows=rows or [], row_count=len(rows or []), execution_time=0.0, success=success)
    db.execute_query = AsyncMock(return_value=result)
    return db


def _sample_subscription(**kwargs: Any) -> WebhookSubscription:
    return WebhookSubscription(
        subscription_id=kwargs.get("subscription_id", "sub-1"),
        url=kwargs.get("url", "https://example.com/hook"),
        secret=kwargs.get("secret", "s3cr3t"),
        event_types=kwargs.get("event_types", frozenset({"user.created", "user.deleted"})),
        active=kwargs.get("active", True),
        description=kwargs.get("description", "Test webhook"),
        tenant_id=kwargs.get("tenant_id"),
        created_at=kwargs.get("created_at", datetime(2024, 1, 1, tzinfo=UTC)),
        metadata=kwargs.get("metadata", {}),
    )


def _sample_attempt(**kwargs: Any) -> DeliveryAttempt:
    return DeliveryAttempt(
        attempt_id=kwargs.get("attempt_id", "att-1"),
        subscription_id=kwargs.get("subscription_id", "sub-1"),
        event_id=kwargs.get("event_id", "evt-1"),
        event_type=kwargs.get("event_type", "user.created"),
        status=kwargs.get("status", DeliveryStatus.DELIVERED),
        status_code=kwargs.get("status_code", 200),
        attempt_number=kwargs.get("attempt_number", 1),
        attempted_at=kwargs.get("attempted_at", datetime(2024, 1, 1, tzinfo=UTC)),
        next_retry_at=kwargs.get("next_retry_at"),
        error_message=kwargs.get("error_message"),
        duration_ms=kwargs.get("duration_ms", 42.0),
    )


def _sub_row(subscription: WebhookSubscription) -> dict[str, Any]:
    """Build a DB row dict matching the subscription schema."""
    import json

    return {
        "subscription_id": subscription.subscription_id,
        "url": subscription.url,
        "secret": subscription.secret,
        "event_types": (
            json.dumps(sorted(subscription.event_types))
            if subscription.event_types is not None
            else None
        ),
        "active": 1 if subscription.active else 0,
        "description": subscription.description,
        "tenant_id": subscription.tenant_id,
        "created_at": subscription.created_at.isoformat(),
        "metadata": json.dumps(subscription.metadata),
    }


def _attempt_row(attempt: DeliveryAttempt) -> dict[str, Any]:
    return {
        "attempt_id": attempt.attempt_id,
        "subscription_id": attempt.subscription_id,
        "event_id": attempt.event_id,
        "event_type": attempt.event_type,
        "status": attempt.status.value,
        "status_code": attempt.status_code,
        "attempt_number": attempt.attempt_number,
        "attempted_at": attempt.attempted_at.isoformat(),
        "next_retry_at": attempt.next_retry_at.isoformat() if attempt.next_retry_at else None,
        "error_message": attempt.error_message,
        "duration_ms": attempt.duration_ms,
    }


# ---------------------------------------------------------------------------
# SqlWebhookSubscriptionStore
# ---------------------------------------------------------------------------


class TestSqlWebhookSubscriptionStoreInitialize:
    """Tests for SqlWebhookSubscriptionStore.initialize()."""

    @pytest.mark.asyncio
    async def test_initialize_executes_ddl(self) -> None:
        """initialize() should execute at least one DDL statement."""
        db = _make_db()
        store = SqlWebhookSubscriptionStore(db=db)

        await store.initialize()

        assert db.execute_query.await_count >= 1
        first_call_sql: str = db.execute_query.call_args_list[0][0][0]
        assert "webhook_subscriptions" in first_call_sql

    @pytest.mark.asyncio
    async def test_initialize_creates_indexes(self) -> None:
        """initialize() should create the expected indexes."""
        db = _make_db()
        store = SqlWebhookSubscriptionStore(db=db)

        await store.initialize()

        all_sqls = " ".join(call[0][0] for call in db.execute_query.call_args_list)
        assert "idx_ws_active" in all_sqls
        assert "idx_ws_tenant" in all_sqls


class TestSqlWebhookSubscriptionStoreCreate:
    """Tests for SqlWebhookSubscriptionStore.create()."""

    @pytest.mark.asyncio
    async def test_create_inserts_row(self) -> None:
        """create() should execute an INSERT statement."""
        db = _make_db()
        store = SqlWebhookSubscriptionStore(db=db)
        sub = _sample_subscription()

        await store.create(sub)

        db.execute_query.assert_awaited_once()
        sql: str = db.execute_query.call_args[0][0]
        assert "INSERT INTO webhook_subscriptions" in sql

    @pytest.mark.asyncio
    async def test_create_includes_subscription_id_in_params(self) -> None:
        """create() params should contain the subscription_id."""
        db = _make_db()
        store = SqlWebhookSubscriptionStore(db=db)
        sub = _sample_subscription(subscription_id="sub-xyz")

        await store.create(sub)

        params: list[Any] = db.execute_query.call_args[0][1]
        assert "sub-xyz" in params

    @pytest.mark.asyncio
    async def test_create_serializes_event_types_as_json(self) -> None:
        """create() should JSON-serialize event_types."""
        import json

        db = _make_db()
        store = SqlWebhookSubscriptionStore(db=db)
        sub = _sample_subscription(event_types=frozenset({"a.b", "c.d"}))

        await store.create(sub)

        params: list[Any] = db.execute_query.call_args[0][1]
        event_types_param = params[3]
        assert isinstance(event_types_param, str)
        parsed = json.loads(event_types_param)
        assert set(parsed) == {"a.b", "c.d"}

    @pytest.mark.asyncio
    async def test_create_none_event_types_stored_as_none(self) -> None:
        """create() should store None when event_types is None."""
        db = _make_db()
        store = SqlWebhookSubscriptionStore(db=db)
        sub = _sample_subscription(event_types=None)

        await store.create(sub)

        params: list[Any] = db.execute_query.call_args[0][1]
        assert params[3] is None


class TestSqlWebhookSubscriptionStoreGet:
    """Tests for SqlWebhookSubscriptionStore.get()."""

    @pytest.mark.asyncio
    async def test_get_returns_subscription(self) -> None:
        """get() should return a WebhookSubscription when a row is found."""
        sub = _sample_subscription()
        db = _make_db(rows=[_sub_row(sub)])
        store = SqlWebhookSubscriptionStore(db=db)

        result = await store.get("sub-1")

        assert result is not None
        assert result.subscription_id == "sub-1"
        assert result.url == sub.url

    @pytest.mark.asyncio
    async def test_get_returns_none_when_not_found(self) -> None:
        """get() should return None when no row is found."""
        db = _make_db(rows=[])
        store = SqlWebhookSubscriptionStore(db=db)

        result = await store.get("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_passes_id_as_param(self) -> None:
        """get() should pass subscription_id as a query parameter."""
        db = _make_db(rows=[])
        store = SqlWebhookSubscriptionStore(db=db)

        await store.get("sub-42")

        params: list[Any] = db.execute_query.call_args[0][1]
        assert "sub-42" in params


class TestSqlWebhookSubscriptionStoreList:
    """Tests for SqlWebhookSubscriptionStore.list()."""

    @pytest.mark.asyncio
    async def test_list_builds_active_only_where_clause(self) -> None:
        """list(active_only=True) should include active = ? in WHERE."""
        db = _make_db(rows=[])
        store = SqlWebhookSubscriptionStore(db=db)

        await store.list(active_only=True)

        sql: str = db.execute_query.call_args[0][0]
        params: list[Any] = db.execute_query.call_args[0][1]
        assert "active = ?" in sql
        assert 1 in params

    @pytest.mark.asyncio
    async def test_list_filters_by_tenant_id(self) -> None:
        """list() should include tenant_id = ? when tenant_id is provided."""
        db = _make_db(rows=[])
        store = SqlWebhookSubscriptionStore(db=db)

        await store.list(tenant_id="tenant-99")

        sql: str = db.execute_query.call_args[0][0]
        params: list[Any] = db.execute_query.call_args[0][1]
        assert "tenant_id = ?" in sql
        assert "tenant-99" in params

    @pytest.mark.asyncio
    async def test_list_filters_by_event_type(self) -> None:
        """list() should include a LIKE filter when event_type is provided."""
        db = _make_db(rows=[])
        store = SqlWebhookSubscriptionStore(db=db)

        await store.list(event_type="user.created", active_only=False)

        sql: str = db.execute_query.call_args[0][0]
        params: list[Any] = db.execute_query.call_args[0][1]
        assert "event_types LIKE ?" in sql
        assert '%"user.created"%' in params

    @pytest.mark.asyncio
    async def test_list_applies_limit_and_offset(self) -> None:
        """list() should pass limit and offset as the last two params."""
        db = _make_db(rows=[])
        store = SqlWebhookSubscriptionStore(db=db)

        await store.list(limit=20, offset=5, active_only=False)

        params: list[Any] = db.execute_query.call_args[0][1]
        assert params[-2] == 20
        assert params[-1] == 5

    @pytest.mark.asyncio
    async def test_list_returns_empty_on_db_failure(self) -> None:
        """list() should return [] when DB result is not successful."""
        db = _make_db(success=False)
        store = SqlWebhookSubscriptionStore(db=db)

        results = await store.list()

        assert results == []

    @pytest.mark.asyncio
    async def test_list_maps_rows_to_subscriptions(self) -> None:
        """list() should deserialize DB rows into WebhookSubscription objects."""
        sub = _sample_subscription()
        db = _make_db(rows=[_sub_row(sub)])
        store = SqlWebhookSubscriptionStore(db=db)

        results = await store.list(active_only=False)

        assert len(results) == 1
        assert results[0].subscription_id == sub.subscription_id


class TestSqlWebhookSubscriptionStoreUpdate:
    """Tests for SqlWebhookSubscriptionStore.update()."""

    @pytest.mark.asyncio
    async def test_update_executes_update_sql(self) -> None:
        """update() should execute an UPDATE statement."""
        db = _make_db()
        store = SqlWebhookSubscriptionStore(db=db)
        sub = _sample_subscription()

        await store.update(sub)

        sql: str = db.execute_query.call_args[0][0]
        assert "UPDATE webhook_subscriptions" in sql
        assert "WHERE subscription_id = ?" in sql

    @pytest.mark.asyncio
    async def test_update_passes_subscription_id_last(self) -> None:
        """update() should place subscription_id as the last WHERE param."""
        db = _make_db()
        store = SqlWebhookSubscriptionStore(db=db)
        sub = _sample_subscription(subscription_id="sub-upd")

        await store.update(sub)

        params: list[Any] = db.execute_query.call_args[0][1]
        assert params[-1] == "sub-upd"


class TestSqlWebhookSubscriptionStoreDelete:
    """Tests for SqlWebhookSubscriptionStore.delete()."""

    @pytest.mark.asyncio
    async def test_delete_executes_delete_sql(self) -> None:
        """delete() should execute a DELETE statement."""
        db = _make_db()
        store = SqlWebhookSubscriptionStore(db=db)

        await store.delete("sub-del")

        sql: str = db.execute_query.call_args[0][0]
        params: list[Any] = db.execute_query.call_args[0][1]
        assert "DELETE FROM webhook_subscriptions" in sql
        assert "sub-del" in params


# ---------------------------------------------------------------------------
# SqlWebhookDeliveryStore
# ---------------------------------------------------------------------------


class TestSqlWebhookDeliveryStoreInitialize:
    """Tests for SqlWebhookDeliveryStore.initialize()."""

    @pytest.mark.asyncio
    async def test_initialize_executes_ddl(self) -> None:
        """initialize() should execute at least one DDL statement."""
        db = _make_db()
        store = SqlWebhookDeliveryStore(db=db)

        await store.initialize()

        assert db.execute_query.await_count >= 1
        first_sql: str = db.execute_query.call_args_list[0][0][0]
        assert "webhook_delivery_attempts" in first_sql

    @pytest.mark.asyncio
    async def test_initialize_creates_indexes(self) -> None:
        """initialize() should create the expected indexes."""
        db = _make_db()
        store = SqlWebhookDeliveryStore(db=db)

        await store.initialize()

        all_sqls = " ".join(call[0][0] for call in db.execute_query.call_args_list)
        assert "idx_wda_sub" in all_sqls
        assert "idx_wda_status" in all_sqls


class TestSqlWebhookDeliveryStoreRecordAttempt:
    """Tests for SqlWebhookDeliveryStore.record_attempt()."""

    @pytest.mark.asyncio
    async def test_record_attempt_inserts_row(self) -> None:
        """record_attempt() should execute an INSERT statement."""
        db = _make_db()
        store = SqlWebhookDeliveryStore(db=db)
        attempt = _sample_attempt()

        await store.record_attempt(attempt)

        db.execute_query.assert_awaited_once()
        sql: str = db.execute_query.call_args[0][0]
        assert "INSERT INTO webhook_delivery_attempts" in sql

    @pytest.mark.asyncio
    async def test_record_attempt_serializes_status_value(self) -> None:
        """record_attempt() should store the status enum value string."""
        db = _make_db()
        store = SqlWebhookDeliveryStore(db=db)
        attempt = _sample_attempt(status=DeliveryStatus.FAILED)

        await store.record_attempt(attempt)

        params: list[Any] = db.execute_query.call_args[0][1]
        assert "failed" in params

    @pytest.mark.asyncio
    async def test_record_attempt_next_retry_at_none(self) -> None:
        """record_attempt() should store None when next_retry_at is not set."""
        db = _make_db()
        store = SqlWebhookDeliveryStore(db=db)
        attempt = _sample_attempt(next_retry_at=None)

        await store.record_attempt(attempt)

        params: list[Any] = db.execute_query.call_args[0][1]
        # next_retry_at is at index 8
        assert params[8] is None


class TestSqlWebhookDeliveryStoreGetAttempts:
    """Tests for SqlWebhookDeliveryStore.get_attempts()."""

    @pytest.mark.asyncio
    async def test_get_attempts_filters_by_subscription(self) -> None:
        """get_attempts() should filter by subscription_id."""
        attempt = _sample_attempt()
        db = _make_db(rows=[_attempt_row(attempt)])
        store = SqlWebhookDeliveryStore(db=db)

        results = await store.get_attempts(subscription_id="sub-1")

        sql: str = db.execute_query.call_args[0][0]
        params: list[Any] = db.execute_query.call_args[0][1]
        assert "subscription_id = ?" in sql
        assert "sub-1" in params
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_get_attempts_filters_by_event_id(self) -> None:
        """get_attempts() should filter by event_id."""
        db = _make_db(rows=[])
        store = SqlWebhookDeliveryStore(db=db)

        await store.get_attempts(event_id="evt-99")

        sql: str = db.execute_query.call_args[0][0]
        params: list[Any] = db.execute_query.call_args[0][1]
        assert "event_id = ?" in sql
        assert "evt-99" in params

    @pytest.mark.asyncio
    async def test_get_attempts_filters_by_status(self) -> None:
        """get_attempts() should filter by status value."""
        db = _make_db(rows=[])
        store = SqlWebhookDeliveryStore(db=db)

        await store.get_attempts(status=DeliveryStatus.FAILED)

        sql: str = db.execute_query.call_args[0][0]
        params: list[Any] = db.execute_query.call_args[0][1]
        assert "status = ?" in sql
        assert "failed" in params

    @pytest.mark.asyncio
    async def test_get_attempts_applies_limit_and_offset(self) -> None:
        """get_attempts() should include limit and offset as final params."""
        db = _make_db(rows=[])
        store = SqlWebhookDeliveryStore(db=db)

        await store.get_attempts(limit=10, offset=3)

        params: list[Any] = db.execute_query.call_args[0][1]
        assert params[-2] == 10
        assert params[-1] == 3

    @pytest.mark.asyncio
    async def test_get_attempts_returns_empty_on_failure(self) -> None:
        """get_attempts() should return [] when DB result is unsuccessful."""
        db = _make_db(success=False)
        store = SqlWebhookDeliveryStore(db=db)

        results = await store.get_attempts()

        assert results == []

    @pytest.mark.asyncio
    async def test_get_attempts_maps_rows_to_delivery_attempts(self) -> None:
        """get_attempts() should deserialize rows into DeliveryAttempt objects."""
        attempt = _sample_attempt()
        db = _make_db(rows=[_attempt_row(attempt)])
        store = SqlWebhookDeliveryStore(db=db)

        results = await store.get_attempts()

        assert len(results) == 1
        assert results[0].attempt_id == attempt.attempt_id
        assert results[0].status == DeliveryStatus.DELIVERED


class TestSqlWebhookDeliveryStoreGetDeadLetters:
    """Tests for SqlWebhookDeliveryStore.get_dead_letters()."""

    @pytest.mark.asyncio
    async def test_get_dead_letters_delegates(self) -> None:
        """get_dead_letters() should query with status=DEAD_LETTER."""
        db = _make_db(rows=[])
        store = SqlWebhookDeliveryStore(db=db)

        await store.get_dead_letters(subscription_id="sub-1")

        sql: str = db.execute_query.call_args[0][0]
        params: list[Any] = db.execute_query.call_args[0][1]
        assert "status = ?" in sql
        assert "dead_letter" in params
        assert "sub-1" in params

    @pytest.mark.asyncio
    async def test_get_dead_letters_applies_limit_and_offset(self) -> None:
        """get_dead_letters() should forward limit and offset."""
        db = _make_db(rows=[])
        store = SqlWebhookDeliveryStore(db=db)

        await store.get_dead_letters(limit=5, offset=2)

        params: list[Any] = db.execute_query.call_args[0][1]
        assert params[-2] == 5
        assert params[-1] == 2


class TestSqlWebhookDeliveryStoreCountRecentFailures:
    """Tests for SqlWebhookDeliveryStore.count_recent_failures()."""

    @pytest.mark.asyncio
    async def test_count_recent_failures_returns_count(self) -> None:
        """count_recent_failures() should return integer from COUNT(*) row."""
        db = _make_db(rows=[{"count": 7}])
        store = SqlWebhookDeliveryStore(db=db)

        total = await store.count_recent_failures("sub-1", since=datetime(2024, 1, 1, tzinfo=UTC))

        sql: str = db.execute_query.call_args[0][0]
        assert "COUNT(*)" in sql
        assert total == 7

    @pytest.mark.asyncio
    async def test_count_recent_failures_filters_both_failure_statuses(self) -> None:
        """count_recent_failures() should query for both FAILED and DEAD_LETTER."""
        db = _make_db(rows=[{"count": 3}])
        store = SqlWebhookDeliveryStore(db=db)

        await store.count_recent_failures("sub-1", since=datetime(2024, 1, 1, tzinfo=UTC))

        params: list[Any] = db.execute_query.call_args[0][1]
        assert "failed" in params
        assert "dead_letter" in params

    @pytest.mark.asyncio
    async def test_count_recent_failures_returns_zero_on_failure(self) -> None:
        """count_recent_failures() should return 0 when the DB result fails."""
        db = _make_db(success=False)
        store = SqlWebhookDeliveryStore(db=db)

        total = await store.count_recent_failures("sub-1", since=datetime(2024, 1, 1, tzinfo=UTC))

        assert total == 0

    @pytest.mark.asyncio
    async def test_count_recent_failures_includes_subscription_id_in_params(self) -> None:
        """count_recent_failures() should pass subscription_id as first param."""
        db = _make_db(rows=[{"count": 0}])
        store = SqlWebhookDeliveryStore(db=db)

        await store.count_recent_failures("sub-filter", since=datetime(2024, 1, 1, tzinfo=UTC))

        params: list[Any] = db.execute_query.call_args[0][1]
        assert params[0] == "sub-filter"
