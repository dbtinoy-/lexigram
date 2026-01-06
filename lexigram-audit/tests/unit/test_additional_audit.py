"""Tests for additional audit components."""

from __future__ import annotations

from datetime import datetime

import pytest

from lexigram.audit.logging.logger import AuditLogger
from lexigram.audit.store.memory import InMemoryAuditStore
from lexigram.audit.types import AuditStoreBackend, PurgeResult, VerificationResult
from lexigram.contracts.audit import AuditEntry, AuditQuery


class TestAuditLoggerExtended:
    """Additional tests for AuditLogger."""

    @pytest.mark.asyncio
    async def test_log_without_source(self) -> None:
        store = InMemoryAuditStore()
        logger = AuditLogger(store=store)
        
        entry = AuditEntry(
            action="test.action",
            actor_id="test-user",
            outcome="success",
        )
        
        await logger.log(entry)
        
        results = await store.query(AuditQuery(limit=10))
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_log_with_all_metadata(self) -> None:
        store = InMemoryAuditStore()
        logger = AuditLogger(store=store)
        
        entry = AuditEntry(
            action="user.permission.change",
            actor_id="admin",
            resource_type="Permission",
            resource_id="perm-123",
            outcome="success",
            severity="high",
            source="admin_api",
            metadata={"old_value": "read", "new_value": "write"},
            tenant_id="tenant-1",
        )
        
        await logger.log(entry)
        
        results = await store.query(AuditQuery(limit=10))
        assert len(results) == 1
        assert results[0].metadata == {"old_value": "read", "new_value": "write"}


class TestPurgeResultExtended:
    """Additional tests for PurgeResult."""

    def test_purge_result_equality(self) -> None:
        r1 = PurgeResult(entries_purged=10, entries_retained=90)
        r2 = PurgeResult(entries_purged=10, entries_retained=90)
        assert r1 == r2

    def test_purge_result_repr(self) -> None:
        result = PurgeResult(entries_purged=5)
        repr_str = repr(result)
        assert "entries_purged" in repr_str


class TestVerificationResultExtended:
    """Additional tests for VerificationResult."""

    def test_verification_result_equality(self) -> None:
        now = datetime.now()
        r1 = VerificationResult(entries_checked=100, mismatches=0, started_at=now, completed_at=now)
        r2 = VerificationResult(entries_checked=100, mismatches=0, started_at=now, completed_at=now)
        assert r1 == r2

    def test_verification_result_repr(self) -> None:
        now = datetime.now()
        result = VerificationResult(entries_checked=50, mismatches=2, started_at=now, completed_at=now)
        repr_str = repr(result)
        assert "entries_checked" in repr_str


class TestAuditStoreBackendExtended:
    """Additional tests for AuditStoreBackend."""

    def test_backend_can_be_used_as_dict_key(self) -> None:
        d = {AuditStoreBackend.MEMORY: "in-memory", AuditStoreBackend.SQL: "sql"}
        assert d[AuditStoreBackend.MEMORY] == "in-memory"

    def test_backend_in_string_comparison(self) -> None:
        assert AuditStoreBackend.MEMORY == "memory"
        assert "memory" in [str(b) for b in AuditStoreBackend]