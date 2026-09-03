"""Tests for contributor boot and entry-point health truth."""

from __future__ import annotations

from unittest.mock import Mock

import pytest
import structlog.testing

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
async def test_normal_boot_failure_is_reflected_in_health(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from lexigram.admin.di import sub_providers
    from lexigram.admin.di.sub_providers.contributor import AdminContributorSubProvider

    monkeypatch.setattr(
        sub_providers.contributor.importlib.metadata,
        "entry_points",
        lambda **_kwargs: [],
    )
    provider = AdminContributorSubProvider(contributors=[_BadContributor()])
    with structlog.testing.capture_logs() as captured:
        await provider.boot(Mock())

    failed = [
        log
        for log in captured
        if log.get("event") == "admin.contributor_on_boot_failed"
    ]
    assert len(failed) == 1
    assert failed[0]["error"] == "boot failed"
    assert failed[0]["error_type"] == "RuntimeError"
    assert failed[0]["exc_info"] is True

    result = provider.health_check()
    assert result.status is HealthStatus.DEGRADED
    assert result.details["boot_failures"]["bad"] == "boot failed"


def test_entry_point_load_failure_is_reflected_in_health(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from lexigram.admin.di import sub_providers
    from lexigram.admin.di.sub_providers.contributor import AdminContributorSubProvider

    class _EntryPoint:
        name = "broken_ep"

        def load(self) -> object:
            raise RuntimeError("entry point exploded")

    monkeypatch.setattr(
        sub_providers.contributor.importlib.metadata,
        "entry_points",
        lambda **_kwargs: [_EntryPoint()],
    )
    provider = AdminContributorSubProvider()
    result = provider.health_check()
    assert result.status is HealthStatus.DEGRADED
    assert result.details["entry_point_failures"]["broken_ep"] == "entry point exploded"


class _MissingContributor:
    name = "optional"
    contributor_id = "optional"
    depends_on: tuple[str, ...] = ()

    async def on_admin_boot(self, container: object) -> None:  # noqa: ARG002
        from lexigram.contracts.exceptions.container import UnresolvableDependencyError

        raise UnresolvableDependencyError(
            "[LEX_ERR_DI_004] missing\n  → Fix: register it",
            dependency="OptionalService",
        )

    async def on_admin_shutdown(self) -> None:
        return None


@pytest.mark.asyncio
async def test_expected_boot_failure_is_one_concise_disabled_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The admin aggregator uses the shared expected-failure contract."""
    from lexigram.admin.di import sub_providers
    from lexigram.admin.di.sub_providers.contributor import AdminContributorSubProvider

    monkeypatch.setattr(
        sub_providers.contributor.importlib.metadata,
        "entry_points",
        lambda **_kwargs: [],
    )
    provider = AdminContributorSubProvider(contributors=[_MissingContributor()])

    with structlog.testing.capture_logs() as captured:
        await provider.boot(Mock())

    disabled = [
        log for log in captured if log.get("event") == "admin.contributor_disabled"
    ]
    assert len(disabled) == 1
    assert disabled[0]["contributor"] == "optional"
    assert disabled[0]["missing"] == "OptionalService"
    assert "LEX_ERR" not in str(disabled[0])
    assert "\n" not in str(disabled[0])
    assert provider.health_check().details["boot_failures"]["optional"] == (
        "OptionalService"
    )
