"""Tests for contributor boot and entry-point health truth."""

from __future__ import annotations

from unittest.mock import Mock

import pytest
from lexigram.contracts.core.health import HealthStatus


class _BadContributor:
    name = "bad"
    contributor_id = "bad"
    depends_on: tuple[str, ...] = ()

    async def on_admin_boot(self, container: object) -> None:
        raise RuntimeError("boot failed")

    async def on_admin_shutdown(self) -> None:
        return None


@pytest.mark.asyncio
async def test_normal_boot_failure_is_reflected_in_health() -> None:
    from lexigram.admin.di.sub_providers.contributor import AdminContributorSubProvider

    provider = AdminContributorSubProvider(contributors=[_BadContributor()])
    await provider.boot(Mock())
    result = provider.health_check()
    assert result.status is HealthStatus.DEGRADED
    assert result.details["boot_failures"]["bad"] == "boot failed"


def test_entry_point_load_failure_is_reflected_in_health(monkeypatch: pytest.MonkeyPatch) -> None:
    from lexigram.admin.di import sub_providers
    from lexigram.admin.di.sub_providers.contributor import AdminContributorSubProvider

    class _EntryPoint:
        name = "broken_ep"

        def load(self) -> object:
            raise RuntimeError("entry point exploded")

    monkeypatch.setattr(
        sub_providers.contributor.importlib.metadata,
        "entry_points",
        lambda group: [_EntryPoint()],
    )
    provider = AdminContributorSubProvider()
    result = provider.health_check()
    assert result.status is HealthStatus.DEGRADED
    assert result.details["entry_point_failures"]["broken_ep"] == "entry point exploded"
