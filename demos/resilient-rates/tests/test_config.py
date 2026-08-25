"""Tests for yaml-first configuration binding (Blueprint reference)."""

from __future__ import annotations

import pathlib

import pytest

from rates.config import RatesConfig, bind_application
from rates.di.provider import RatesProvider
from rates.repository.simulated_upstream import FaultController, Scenario


def test_bind_application_reads_web_cache_demo_sections() -> None:
    web_config, cache_config, demo_config = bind_application()
    assert web_config.server.port == 7073
    assert web_config.server.host == "127.0.0.1"
    assert web_config.security.csrf.enabled is False
    backend = next(b for b in cache_config.backends if b.default)
    assert backend.default_ttl == 60
    assert demo_config.upstream_scenario == "healthy"


def test_env_overrides_win(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LEX_WEB__SERVER__PORT", "7099")
    monkeypatch.setenv("LEX_DEMO__UPSTREAM_SCENARIO", "down")
    web_config, _cache_config, demo_config = bind_application()
    assert web_config.server.port == 7099
    assert demo_config.upstream_scenario == "down"


class _RecordingRegistrar:
    """Captures singleton registrations at the container boundary."""

    def __init__(self) -> None:
        self.singletons: dict[type, dict] = {}

    def singleton(self, cls: type, instance: object | None = None,
                  **kw: object) -> None:
        self.singletons[cls] = {"instance": instance, **kw}


def test_provider_wires_scenario_from_bound_config() -> None:
    import asyncio

    provider = RatesProvider(
        config=RatesConfig(upstream_scenario="flaky")
    )
    registrar = _RecordingRegistrar()
    asyncio.run(provider.register(registrar))

    assert registrar.singletons[RatesConfig]["instance"].upstream_scenario == "flaky"
    factory = registrar.singletons[FaultController]["factory"]
    faults = factory()
    assert faults.current is Scenario.FLAKY


def test_composition_root_contains_no_literal_server_config() -> None:
    app_src = (
        pathlib.Path(__file__).resolve().parents[1] / "src" / "rates" / "app.py"
    ).read_text()
    assert "ServerConfig(" not in app_src
    assert "SecurityConfig(" not in app_src
    assert "7073" not in app_src
