"""Tests for AuditLogger (fire-tolerant log + query delegation)."""

from __future__ import annotations

import pytest

from lexigram.audit.logging.logger import AuditLogger
from lexigram.audit.store.memory import InMemoryAuditStore
from lexigram.contracts.audit import AuditEntry, AuditQuery


class TestAuditLogger:
    """Tests for AuditLogger."""

    @pytest.mark.asyncio
    async def test_log_persists_entry(
        self, audit_logger: AuditLogger, memory_store: InMemoryAuditStore
    ) -> None:
        entry = AuditEntry(action="user.login", actor_id="user-1", outcome="success")
        await audit_logger.log(entry)
        results = await memory_store.query(AuditQuery())
        assert len(results) == 1
        assert results[0].action == "user.login"

    @pytest.mark.asyncio
    async def test_log_never_raises(self) -> None:
        """log() must not raise even when store fails."""

        class BrokenStore:
            async def append(self, entry: AuditEntry) -> None:
                raise RuntimeError("Store exploded")

            async def query(self, q: AuditQuery) -> list[AuditEntry]:
                return []

            async def count(self, q: AuditQuery) -> int:
                return 0

        logger = AuditLogger(store=BrokenStore())  # type: ignore[arg-type]
        await logger.log(AuditEntry(action="test", actor_id="actor"))

    @pytest.mark.asyncio
    async def test_query_returns_empty_on_store_error(self) -> None:
        """query() returns empty list when store fails."""

        class BrokenStore:
            async def append(self, entry: AuditEntry) -> None:
                pass

            async def query(self, q: AuditQuery) -> list[AuditEntry]:
                raise RuntimeError("Query failed")

            async def count(self, q: AuditQuery) -> int:
                return 0

        logger = AuditLogger(store=BrokenStore())  # type: ignore[arg-type]
        result = await logger.query(AuditQuery())
        assert result == []

    @pytest.mark.asyncio
    async def test_query_delegates_to_store(self, audit_logger: AuditLogger) -> None:
        entries = [
            AuditEntry(action="a.b", actor_id="user-1", source="sql"),
            AuditEntry(action="c.d", actor_id="user-2", source="admin"),
        ]
        for e in entries:
            await audit_logger.log(e)
        results = await audit_logger.query(AuditQuery(actor_id="user-1"))
        assert len(results) == 1
        assert results[0].actor_id == "user-1"
