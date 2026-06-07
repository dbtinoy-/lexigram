"""Tests for notification schema setup contributions."""

from unittest.mock import AsyncMock

import pytest

from lexigram.contracts.cli.contributions import SchemaSetupResult
from lexigram.notification.cli.schema_setup import ensure_inbox_messages


@pytest.mark.asyncio
async def test_ensure_inbox_messages_reports_created_when_absent():
    """Absent table yields CREATED."""
    db = AsyncMock()
    db.table_exists.return_value = False
    db.execute.return_value = None

    outcome = await ensure_inbox_messages(db)

    assert outcome.status == SchemaSetupResult.CREATED


@pytest.mark.asyncio
async def test_ensure_inbox_messages_reports_failure_message():
    """Failure propagates message into FAILED outcome."""
    db = AsyncMock()
    db.table_exists.side_effect = RuntimeError("connection refused")

    outcome = await ensure_inbox_messages(db)

    assert outcome.status == SchemaSetupResult.FAILED
    assert outcome.message == "connection refused"