"""Tests for admin schema setup contributions."""

from unittest.mock import AsyncMock

import pytest

from lexigram.admin.cli.schema_setup import ensure_tenant_configs
from lexigram.contracts.cli.contributions import SchemaSetupResult


@pytest.mark.asyncio
async def test_ensure_tenant_configs_reports_created_when_absent():
    """Absent table yields CREATED."""
    db = AsyncMock()
    db.table_exists.return_value = False
    db.execute.return_value = None

    outcome = await ensure_tenant_configs(db)

    assert outcome.status == SchemaSetupResult.CREATED


@pytest.mark.asyncio
async def test_ensure_tenant_configs_reports_already_present():
    """Existing table yields ALREADY_PRESENT."""
    db = AsyncMock()
    db.table_exists.return_value = True
    db.execute.return_value = None

    outcome = await ensure_tenant_configs(db)

    assert outcome.status == SchemaSetupResult.ALREADY_PRESENT


@pytest.mark.asyncio
async def test_ensure_tenant_configs_reports_failure_message():
    """Failure propagates message into FAILED outcome."""
    db = AsyncMock()
    db.table_exists.return_value = False
    db.execute.side_effect = RuntimeError("connection refused")

    outcome = await ensure_tenant_configs(db)

    assert outcome.status == SchemaSetupResult.FAILED
    assert outcome.message == "connection refused"
