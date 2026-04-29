"""Tests for PluginEngineProvider boot integration."""

from __future__ import annotations

from typing import Any

import pytest

from lexigram.di.provider import Provider
from lexigram.di.provider import ProviderPriority
from lexigram.plugins.engine import PluginEngineProvider


class _FakeProvider(Provider):
    name = "fake"

    def __init__(self) -> None:
        super().__init__()
        self.register_called = False
        self.boot_called = False
        self.shutdown_called = False

    async def register(self, container: Any) -> None:
        self.register_called = True
        container.registered.append(self.name)

    async def boot(self, container: Any) -> None:
        self.boot_called = True

    async def shutdown(self) -> None:
        self.shutdown_called = True


class _FakeRegistrar:
    def __init__(self) -> None:
        self.registered: list[str] = []


def _fake_entry_points(monkeypatch: pytest.MonkeyPatch, mapping: dict[str, type]) -> None:
    class _FakeEntryPoint:
        def __init__(self, name: str, cls: type) -> None:
            self.name = name
            self._cls = cls
            self.value = f"{cls.__module__}:{cls.__qualname__}"

        def load(self) -> type:
            return self._cls

    def _entry_points(*, group: str) -> list[Any]:
        return [_FakeEntryPoint(name, cls) for name, cls in mapping.items()]

    monkeypatch.setattr("lexigram.plugins.engine._entry_points", _entry_points)


@pytest.mark.asyncio
async def test_engine_registers_enabled_providers(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    _fake_entry_points(monkeypatch, {"fake": _FakeProvider})
    engine = PluginEngineProvider(state_path=tmp_path / "plugins.json")
    registrar = _FakeRegistrar()
    await engine.register(registrar)
    assert registrar.registered == ["fake"]
    assert len(engine.discovered_providers) == 1


@pytest.mark.asyncio
async def test_engine_skips_disabled_providers(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    _fake_entry_points(monkeypatch, {"fake": _FakeProvider})
    from lexigram.plugins.state import save_disabled

    save_disabled({"fake"}, tmp_path / "plugins.json")
    engine = PluginEngineProvider(state_path=tmp_path / "plugins.json")
    registrar = _FakeRegistrar()
    await engine.register(registrar)
    assert registrar.registered == []
    assert engine.discovered_providers == []


@pytest.mark.asyncio
async def test_engine_boots_and_shuts_down_discovered(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    _fake_entry_points(monkeypatch, {"fake": _FakeProvider})
    engine = PluginEngineProvider(state_path=tmp_path / "plugins.json")
    await engine.register(_FakeRegistrar())
    container: Any = object()
    await engine.boot(container)
    await engine.shutdown()
    provider = engine.discovered_providers[0]
    assert provider.boot_called and provider.shutdown_called


def test_engine_provider_metadata() -> None:
    engine = PluginEngineProvider()
    assert engine.name == "plugins"
    assert engine.priority == ProviderPriority.INFRASTRUCTURE


def test_plugins_module_configure_returns_provider(tmp_path) -> None:
    from lexigram.plugins.module import PluginsModule

    dynamic = PluginsModule.configure(state_path=tmp_path / "plugins.json")
    provider_classes = [p.__class__ for p in dynamic.providers]
    assert PluginEngineProvider in provider_classes