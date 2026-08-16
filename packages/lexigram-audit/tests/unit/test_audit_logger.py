"""Tests for audit logging logger."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.audit.logging.logger import AuditLogger
from lexigram.contracts.audit import AuditEntry, AuditEventSeverity


class TestAuditLogger:
    """Tests for AuditLogger."""

    @pytest.fixture
    def mock_store(self) -> MagicMock:
        store = MagicMock()
        store.append = AsyncMock()
        return store

    def test_logger_creation(self, mock_store: MagicMock) -> None:
        logger = AuditLogger(store=mock_store)
        assert logger._store is mock_store

    @pytest.mark.asyncio
    async def test_log_calls_store_append(self, mock_store: MagicMock) -> None:
        logger = AuditLogger(store=mock_store)
        entry = AuditEntry(
            action="user.login",
            actor_id="user-1",
            outcome="success",
        )
        await logger.log(entry)
        mock_store.append.assert_called_once_with(entry)

    @pytest.mark.asyncio
    async def test_log_with_all_fields(self, mock_store: MagicMock) -> None:
        logger = AuditLogger(store=mock_store)
        entry = AuditEntry(
            action="user.update",
            actor_id="user-1",
            resource_type="User",
            resource_id="user-1",
            outcome="success",
            severity=AuditEventSeverity.HIGH,
            source="api",
        )
        await logger.log(entry)
        mock_store.append.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_multiple_entries(self, mock_store: MagicMock) -> None:
        logger = AuditLogger(store=mock_store)
        for i in range(5):
            entry = AuditEntry(
                action=f"action.{i}",
                actor_id="user-1",
                outcome="success",
            )
            await logger.log(entry)
        assert mock_store.append.call_count == 5