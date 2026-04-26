"""Tests for webhook schema setup contributions."""

from unittest.mock import AsyncMock

import pytest

from lexigram.contracts.cli.contributions import SchemaSetupResult
from lexigram.webhook.cli.schema_setup import ensure_delivery_attempts, ensure_subscriptions


@pytest.mark.asyncio
async def test_ensure_subscriptions_reports_created_when_absent():
    """Absent table yields CREATED."""
    db = AsyncMock()
    db.table_exists.return_value = False
    db.execute_query.return_value = None

    outcome = await ensure_subscriptions(db)

    assert outcome.status == SchemaSetupResult.CREATED


@pytest.mark.asyncio
async def test_ensure_delivery_attempts_reports_already_present():
    """Present table yields ALREADY_PRESENT."""
    db = AsyncMock()
    db.table_exists.return_value = True
    db.execute_query.return_value = None

    outcome = await ensure_delivery_attempts(db)

    assert outcome.status == SchemaSetupResult.ALREADY_PRESENT


@pytest.mark.asyncio
async def test_ensure_subscriptions_reports_failure_message():
    """Failure propagates message into FAILED outcome."""
    db = AsyncMock()
    db.table_exists.side_effect = RuntimeError("connection refused")

    outcome = await ensure_subscriptions(db)

    assert outcome.status == SchemaSetupResult.FAILED
    assert outcome.message == "connection refused"