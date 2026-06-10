"""Tests for lexigram.plugins.discovery.discover_providers."""

from __future__ import annotations

from typing import Any

import pytest

from lexigram.di.provider import Provider
from lexigram.plugins import discovery


class _FakeProvider(Provider):
    name = "fake"


class _BrokenCtorProvider(Provider):
    name = "broken"

    def __init__(self, required_arg: str) -> None:  # noqa: B027 — no default -> unconstructible
        super().__init__(name="broken")
        self.required_arg = required_arg


def _fake_entry_points(monkeypatch: pytest.MonkeyPatch, mapping: dict[str, type]) -> None:
    """Monkeypatch importlib.metadata.entry_points(group=...) for the given group."""

    class _FakeEntryPoint:
        def __init__(self, name: str, cls: type) -> None:
            self.name = name
            self._cls = cls
            self.value = f"{cls.__module__}:{cls.__qualname__}"

        def load(self) -> type:
            return self._cls

    def _entry_points(*, group: str) -> list[Any]:
        if group != "lexigram.providers":
            return []
        return [_FakeEntryPoint(name, cls) for name, cls in mapping.items()]

    monkeypatch.setattr(discovery, "_entry_points", _entry_points)


def test_discover_providers_returns_instances(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_entry_points(monkeypatch, {"fake": _FakeProvider})
    result = discovery.discover_providers()
    assert len(result) == 1
    assert isinstance(result[0], _FakeProvider)


def test_discover_providers_skips_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_entry_points(monkeypatch, {"fake": _FakeProvider})
    result = discovery.discover_providers(disabled={"fake"})
    assert result == []


def test_discover_providers_skips_unconstructible(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_entry_points(monkeypatch, {"broken": _BrokenCtorProvider})
    result = discovery.discover_providers()
    assert result == []


def test_discover_providers_empty_when_no_entry_points(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_entry_points(monkeypatch, {})
    assert discovery.discover_providers() == []


from lexigram.contracts.plugins import PluginDescriptor

_SAMPLE_DESCRIPTOR = PluginDescriptor(
    name="relay-gateway",
    display_name="AI Gateway",
    description="AI relay/gateway capabilities.",
    icon="shuffle",
    provider_entry_point="relay-gateway",
)


def _fake_plugin_entry_points(
    monkeypatch: pytest.MonkeyPatch, mapping: dict[str, PluginDescriptor]
) -> None:
    class _FakeEntryPoint:
        def __init__(self, name: str, descriptor: PluginDescriptor) -> None:
            self.name = name
            self._descriptor = descriptor

        def load(self) -> PluginDescriptor:
            return self._descriptor

    def _entry_points(*, group: str) -> list[Any]:
        if group != "lexigram.plugins":
            return []
        return [_FakeEntryPoint(name, d) for name, d in mapping.items()]

    monkeypatch.setattr(discovery, "_entry_points", _entry_points)


def test_discover_plugins_returns_descriptors(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_plugin_entry_points(monkeypatch, {"relay-gateway": _SAMPLE_DESCRIPTOR})
    result = discovery.discover_plugins()
    assert result == [_SAMPLE_DESCRIPTOR]


def test_discover_plugins_skips_non_descriptor(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeEntryPoint:
        name = "bad"

        def load(self) -> str:
            return "not a descriptor"

    def _entry_points(*, group: str) -> list[Any]:
        return [_FakeEntryPoint()] if group == "lexigram.plugins" else []

    monkeypatch.setattr(discovery, "_entry_points", _entry_points)
    assert discovery.discover_plugins() == []