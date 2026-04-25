"""Tests for resilience schema setup contributions."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.contracts.cli.contributions import SchemaSetupResult
from lexigram.resilience.cli.schema_setup import ensure_idempotency_keys


class _AsyncCtxManager:
    """Async context manager used as the ``scoped_context`` mock."""

    async def __aenter__(self) -> None:
        return None

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


@pytest.mark.asyncio
async def test_ensure_idempotency_keys_reports_created_when_absent():
    """Absent table yields CREATED."""
    conn = AsyncMock()
    conn.execute.return_value = None
    db = AsyncMock()
    db.table_exists.return_value = False
    db.scoped_context = MagicMock(return_value=_AsyncCtxManager())
    db.get_scoped_connection = AsyncMock(return_value=conn)

    outcome = await ensure_idempotency_keys(db)

    assert outcome.status == SchemaSetupResult.CREATED
    conn.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_ensure_idempotency_keys_reports_failure_message():
    """Failure propagates message into FAILED outcome."""
    db = AsyncMock()
    db.table_exists.side_effect = RuntimeError("connection refused")

    outcome = await ensure_idempotency_keys(db)

    assert outcome.status == SchemaSetupResult.FAILED
    assert outcome.message == "connection refused"