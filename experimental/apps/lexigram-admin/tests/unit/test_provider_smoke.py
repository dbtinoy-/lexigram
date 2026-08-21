"""Smoke: AdminProvider's exported contracts resolve after register+boot.

AdminProvider cannot boot in a bare container: freeze-time validation
(LEX_ERR_DI_008) requires DatabaseProviderProtocol and FlagManagerProtocol to
be registered. Both are satisfied with MagicMock stand-ins via
``TestEnvironment.override``, which ``setup()`` applies before the app starts.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from lexigram.admin.config import AdminConfig
from lexigram.admin.di.bundle_provider import AdminProvider
from lexigram.contracts.admin.protocols import (
    AdminContributorRegistryProtocol,
    AdminDashboardProtocol,
)
from lexigram.contracts.data import DatabaseProviderProtocol
from lexigram.contracts.feature_flags.protocols import FlagManagerProtocol
from lexigram.testing.fixtures.bed import TestEnvironment
from lexigram.testing.lib.smoke import assert_contracts_resolve


@pytest.mark.asyncio
async def test_admin_exports_resolve() -> None:
    bed = TestEnvironment()
    bed.override(DatabaseProviderProtocol, MagicMock()).override(
        FlagManagerProtocol, MagicMock()
    )
    bed.use_provider(
        AdminProvider(
            config=AdminConfig.from_dict(
                {"auth": {"security": {"setup_token": "smoke-token"}}}
            )
        )
    )
    await bed.setup()
    try:
        await assert_contracts_resolve(
            bed.container,
            [AdminContributorRegistryProtocol, AdminDashboardProtocol],
        )
    finally:
        await bed.teardown()
