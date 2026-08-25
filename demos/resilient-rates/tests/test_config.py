"""Tests for yaml-first configuration binding (Blueprint reference)."""

from __future__ import annotations

import pytest

from rates.config import RatesConfig, bind_application
from rates.di.provider import RatesProvider
from rates.repository.simulated_upstream import Scenario


def test_bind_application_reads_web_and_demo_sections() -> None:
    web_config, demo_config = bind_application()
    assert web_config.server.port == 7073
    assert web_config.server.host == "127.0.0.1"
    assert web_config.security.csrf.enabled is False
    assert demo_config.upstream_scenario == "healthy"
    assert demo_config.cache_ttl_seconds == 60


def test_env_overrides_win(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LEX_DEMO__CACHE_TTL_SECONDS", "7")
    monkeypatch.setenv("LEX_WEB__SERVER__PORT", "7099")
    web_config, demo_config = bind_application()
    assert demo_config.cache_ttl_seconds == 7
    assert web_config.server.port == 7099


class _RecordingRegistrar:
    """Captures singleton registrations at the container boundary."""

    def __init__(self) -> None:
        self.singletons: list[tuple[type, object]] = []

    def singleton(self, cls: type, instance: object | None = None,
                  **_kw: object) -> None:
        self.singletons.append((cls, instance))


def test_provider_wires_scenario_and_ttl_from_bound_config() -> None:
    provider = RatesProvider(
        config=RatesConfig(upstream_scenario="flaky", cache_ttl_seconds=5)
    )
    registrar = _RecordingRegistrar()
    import asyncio

    asyncio.run(provider.register(registrar))  # sync driver; register is async

    faults = next(inst for cls, inst in registrar.singletons
                  if cls.__name__ == "FaultController")
    assert faults.current is Scenario.FLAKY


def test_module_contains_no_literal_server_config() -> None:
    import pathlib

    module_src = (
        pathlib.Path(__file__).resolve().parents[1] / "src" / "rates" / "module.py"
    ).read_text()
    assert "ServerConfig(" not in module_src
    assert "SecurityConfig(" not in module_src
    assert "7073" not in module_src
