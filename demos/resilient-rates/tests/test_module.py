"""Integration tests: boot the real composition root and exercise reads."""

from __future__ import annotations

from typing import AsyncIterator

import pytest

from lexigram.app import Application

from rates.app import create_app
from rates.repository import FaultController, Scenario
from rates.services import RatesService


@pytest.fixture
async def app() -> AsyncIterator[Application]:
    instance = create_app()
    await instance.start()
    try:
        yield instance
    finally:
        await instance.stop()


async def test_boots_and_resolves_services(app: Application) -> None:
    service = await app.container.resolve(RatesService)
    faults = await app.container.resolve(FaultController)

    assert faults.current is Scenario.HEALTHY
    assert service.stats().upstream_calls == 0


async def test_end_to_end_miss_hit_through_real_backend(app: Application) -> None:
    service = await app.container.resolve(RatesService)

    first = (await service.fetch("EUR/USD")).unwrap()
    second = (await service.fetch("EUR/USD")).unwrap()

    assert first.source == "upstream"
    assert second.source == "cache"
    stats = service.stats()
    assert stats.upstream_calls == 1 and stats.hits == 1


async def test_fault_controller_flips_scenario_live(app: Application) -> None:
    service = await app.container.resolve(RatesService)
    faults = await app.container.resolve(FaultController)

    await service.fetch("GBP/USD")  # warm stale store
    faults.set(Scenario.DOWN)
    try:
        await service.fetch("GBP/USD")
    except Exception:  # noqa: BLE001 — terminal pipeline outcome expected
        pass

    assert faults.current is Scenario.DOWN
    faults.set(Scenario.HEALTHY)
