"""Tests for AdminProvider extra_providers extension point (E6)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock


def _make_fake_provider():
    p = MagicMock()
    p.register = AsyncMock()
    p.boot = AsyncMock()
    p.shutdown = AsyncMock()
    return p


async def test_extra_providers_accepted_in_init() -> None:
    from lexigram.admin.di.bundle_provider import AdminProvider

    p = _make_fake_provider()
    provider = AdminProvider(extra_providers=[p])
    assert provider is not None


async def test_extra_providers_defaults_to_none() -> None:
    from lexigram.admin.di.bundle_provider import AdminProvider

    provider = AdminProvider()
    assert provider is not None


async def test_extra_providers_registered_in_register() -> None:
    from lexigram.admin.di.bundle_provider import AdminProvider

    extra = _make_fake_provider()
    provider = AdminProvider(extra_providers=[extra])

    fake_container = MagicMock()
    fake_container.singleton = MagicMock()

    provider._sub_providers = []

    await provider.register(fake_container)

    extra.register.assert_awaited_once_with(fake_container)


async def test_multiple_extra_providers_all_registered() -> None:
    from lexigram.admin.di.bundle_provider import AdminProvider

    extras = [_make_fake_provider(), _make_fake_provider()]
    provider = AdminProvider(extra_providers=extras)

    fake_container = MagicMock()
    fake_container.singleton = MagicMock()
    provider._sub_providers = []

    await provider.register(fake_container)

    for extra in extras:
        extra.register.assert_awaited_once_with(fake_container)
