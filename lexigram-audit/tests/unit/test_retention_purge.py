"""Tests for AuditPurger."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.audit.retention.purge import AuditPurger
from lexigram.audit.store.memory import InMemoryAuditStore
from lexigram.contracts.audit import (
    AuditEntry,
    AuditEventSeverity,
    AuditQuery,
    RetentionDecision,
    RetentionPolicyProtocol,
)


class MockRetentionPolicy:
    """Mock retention policy for testing."""

    def __init__(self, decisions: dict[str, RetentionDecision]) -> None:
        self._decisions = decisions

    async def evaluate(self, entry: AuditEntry) -> RetentionDecision:
        key = entry.action
        return self._decisions.get(key, RetentionDecision.RETAIN_UNTIL)

    async def get_expiry(self, entry: AuditEntry) -> datetime | None:
        decision = await self.evaluate(entry)
        if decision == RetentionDecision.RETAIN:
            return None
        return entry.occurred_at + timedelta(days=30)


def _stamped_entry(action: str, occurred_at: datetime, retention_days: int = 30) -> AuditEntry:
    """Build an entry stamped like AuditLogger.log() would for a 30-day policy."""
    return AuditEntry(
        action=action,
        actor_id="user-1",
        resource_type="User",
        outcome="success",
        severity=AuditEventSeverity.MEDIUM,
        occurred_at=occurred_at,
        metadata={
            "__expires_at": (occurred_at + timedelta(days=retention_days)).isoformat()
        },
    )


class TestAuditPurger:
    """Tests for AuditPurger."""

    @pytest.fixture
    def mock_store(self) -> MagicMock:
        store = MagicMock()
        store.query = AsyncMock(return_value=[])
        store.delete_expired = AsyncMock(return_value=0)
        return store

    @pytest.fixture
    def mock_retention(self) -> MockRetentionPolicy:
        return MockRetentionPolicy({})

    @pytest.fixture
    def mock_audit_logger(self) -> MagicMock:
        logger = MagicMock()
        logger.log = AsyncMock()
        return logger

    @pytest.mark.asyncio
    async def test_purge_expired_empty_store(self, mock_store: MagicMock, mock_retention: MockRetentionPolicy) -> None:
        purger = AuditPurger(store=mock_store, retention=mock_retention)
        result = await purger.purge_expired()
        assert result == 0
        mock_store.query.assert_called_once()

    @pytest.mark.asyncio
    async def test_purge_expired_retains_valid_entries(self, mock_store: MagicMock, mock_retention: MockRetentionPolicy) -> None:
        entry = AuditEntry(
            action="user.login",
            actor_id="user-1",
            resource_type="User",
            outcome="success",
            severity=AuditEventSeverity.MEDIUM,
        )
        mock_store.query = AsyncMock(return_value=[entry])
        
        # All entries should be retained
        purger = AuditPurger(store=mock_store, retention=mock_retention)
        result = await purger.purge_expired()
        assert result == 0

    @pytest.mark.asyncio
    async def test_purge_expired_purges_expired_entries(self, mock_store: MagicMock) -> None:
        old_entry = AuditEntry(
            action="user.login",
            actor_id="user-1",
            resource_type="User",
            outcome="success",
            severity=AuditEventSeverity.MEDIUM,
            occurred_at=datetime.now(UTC) - timedelta(days=400),
        )
        mock_store.query = AsyncMock(return_value=[old_entry])
        
        # Create retention that says purge and has expired
        retention = MagicMock(spec=RetentionPolicyProtocol)
        retention.evaluate = AsyncMock(return_value=RetentionDecision.PURGE)
        retention.get_expiry = AsyncMock(
            return_value=datetime.now(UTC) - timedelta(days=1)
        )
        
        purger = AuditPurger(store=mock_store, retention=retention)
        result = await purger.purge_expired()
        assert result == 1

    @pytest.mark.asyncio
    async def test_purge_expired_with_audit_logger(self, mock_store: MagicMock, mock_retention: MockRetentionPolicy, mock_audit_logger: MagicMock) -> None:
        mock_store.query = AsyncMock(return_value=[])
        
        purger = AuditPurger(
            store=mock_store,
            retention=mock_retention,
            audit_logger=mock_audit_logger,
        )
        result = await purger.purge_expired()
        
        assert result == 0
        mock_audit_logger.log.assert_called_once()
        call_args = mock_audit_logger.log.call_args
        entry = call_args[0][0]
        assert entry.action == "audit.purge_expired"
        assert entry.actor_id == "system"

    @pytest.mark.asyncio
    async def test_purge_expired_logs_evaluated_count(self, mock_store: MagicMock) -> None:
        entries = [
            AuditEntry(action=f"action.{i}", actor_id="user", outcome="success")
            for i in range(5)
        ]
        mock_store.query = AsyncMock(return_value=entries)
        
        retention = MagicMock(spec=RetentionPolicyProtocol)
        retention.evaluate = AsyncMock(return_value=RetentionDecision.RETAIN)
        
        purger = AuditPurger(store=mock_store, retention=retention)
        result = await purger.purge_expired()
        
        assert result == 0

    @pytest.mark.asyncio
    async def test_purge_expired_skips_when_not_expired(self, mock_store: MagicMock) -> None:
        recent_entry = AuditEntry(
            action="user.login",
            actor_id="user-1",
            resource_type="User",
            outcome="success",
            severity=AuditEventSeverity.MEDIUM,
            occurred_at=datetime.now(UTC) - timedelta(days=1),
        )
        mock_store.query = AsyncMock(return_value=[recent_entry])
        
        retention = MagicMock(spec=RetentionPolicyProtocol)
        retention.evaluate = AsyncMock(return_value=RetentionDecision.RETAIN_UNTIL)
        retention.get_expiry = AsyncMock(
            return_value=datetime.now(UTC) + timedelta(days=30)
        )
        
        purger = AuditPurger(store=mock_store, retention=retention)
        result = await purger.purge_expired()
        
        assert result == 0

    @pytest.mark.asyncio
    async def test_purge_expired_multiple_entries_mixed(self, mock_store: MagicMock) -> None:
        now = datetime.now(UTC)
        entries = [
            AuditEntry(action="keep", actor_id="u", outcome="success", occurred_at=now - timedelta(days=10)),
            AuditEntry(action="purge_old", actor_id="u", outcome="success", occurred_at=now - timedelta(days=400)),
            AuditEntry(action="purge_recent", actor_id="u", outcome="success", occurred_at=now - timedelta(days=5)),
        ]
        mock_store.query = AsyncMock(return_value=entries)
        
        async def mock_evaluate(entry: AuditEntry) -> RetentionDecision:
            if entry.action == "keep":
                return RetentionDecision.RETAIN
            return RetentionDecision.PURGE
        
        async def mock_get_expiry(entry: AuditEntry) -> datetime | None:
            if entry.action == "keep":
                return None
            if entry.action == "purge_old":
                return now - timedelta(days=1)
            return now + timedelta(days=30)
        
        retention = MagicMock(spec=RetentionPolicyProtocol)
        retention.evaluate = mock_evaluate
        retention.get_expiry = mock_get_expiry
        
        purger = AuditPurger(store=mock_store, retention=retention)
        result = await purger.purge_expired()
        
        assert result == 1  # Only one expired entry

    @pytest.mark.asyncio
    async def test_purge_expired_calls_delete_expired_once(self, mock_store: MagicMock) -> None:
        old_entry = AuditEntry(
            action="user.login",
            actor_id="user-1",
            resource_type="User",
            outcome="success",
            severity=AuditEventSeverity.MEDIUM,
            occurred_at=datetime.now(UTC) - timedelta(days=400),
        )
        mock_store.query = AsyncMock(return_value=[old_entry])
        retention = MagicMock(spec=RetentionPolicyProtocol)
        retention.evaluate = AsyncMock(return_value=RetentionDecision.PURGE)
        retention.get_expiry = AsyncMock(
            return_value=datetime.now(UTC) - timedelta(days=1)
        )

        purger = AuditPurger(store=mock_store, retention=retention)
        result = await purger.purge_expired()

        assert result == 1
        mock_store.delete_expired.assert_awaited_once()
        called_cutoff = mock_store.delete_expired.await_args.args[0]
        assert isinstance(called_cutoff, datetime)

    @pytest.mark.asyncio
    async def test_purge_expired_dry_run_does_not_delete(self, mock_store: MagicMock) -> None:
        old_entry = AuditEntry(
            action="user.login",
            actor_id="user-1",
            resource_type="User",
            outcome="success",
            severity=AuditEventSeverity.MEDIUM,
            occurred_at=datetime.now(UTC) - timedelta(days=400),
        )
        mock_store.query = AsyncMock(return_value=[old_entry])
        retention = MagicMock(spec=RetentionPolicyProtocol)
        retention.evaluate = AsyncMock(return_value=RetentionDecision.PURGE)
        retention.get_expiry = AsyncMock(
            return_value=datetime.now(UTC) - timedelta(days=1)
        )

        purger = AuditPurger(store=mock_store, retention=retention)
        result = await purger.purge_expired(dry_run=True)

        assert result == 1
        mock_store.delete_expired.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_purge_expired_removes_expired_entries_from_store(self) -> None:
        now = datetime.now(UTC)
        store = InMemoryAuditStore()
        await store.append(_stamped_entry("expired.login", now - timedelta(days=400)))
        await store.append(_stamped_entry("recent.login", now - timedelta(days=10)))
        await store.append(AuditEntry(action="keep", actor_id="user-1", outcome="success"))
        retention = MockRetentionPolicy({"expired.login": RetentionDecision.PURGE})

        purger = AuditPurger(store=store, retention=retention)
        purged = await purger.purge_expired()

        assert purged == 1
        remaining = await store.query(AuditQuery(limit=100))
        assert {e.action for e in remaining} == {"recent.login", "keep"}

    @pytest.mark.asyncio
    async def test_purge_expired_dry_run_leaves_store_unchanged(self) -> None:
        now = datetime.now(UTC)
        store = InMemoryAuditStore()
        await store.append(_stamped_entry("expired.login", now - timedelta(days=400)))
        await store.append(_stamped_entry("recent.login", now - timedelta(days=10)))
        retention = MockRetentionPolicy({"expired.login": RetentionDecision.PURGE})

        purger = AuditPurger(store=store, retention=retention)
        purged = await purger.purge_expired(dry_run=True)

        assert purged == 1
        remaining = await store.query(AuditQuery(limit=100))
        assert {e.action for e in remaining} == {"expired.login", "recent.login"}
