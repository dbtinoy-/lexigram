"""Test that AIProvider skips disabled lexigram.ai.subsystems entry points."""

from __future__ import annotations

import importlib.metadata
from typing import Any

import pytest

from lexigram.ai.config import AIConfig
from lexigram.ai.di.provider import AIProvider


class _FakeContainer:
    def singleton(self, *args: Any, **kwargs: Any) -> None:
        pass


class _FakeSubsystemProvider:
    registered_names: list[str] = []

    def __init__(self, config: Any = None) -> None:
        self._config = config

    async def register(self, container: Any) -> None:
        _FakeSubsystemProvider.registered_names.append("called")


@pytest.mark.asyncio
async def test_disabled_subsystem_is_skipped(monkeypatch: pytest.MonkeyPatch) -> None:
    _FakeSubsystemProvider.registered_names.clear()

    class _FakeEntryPoint:
        name = "relay-gateway"
        value = "fake:FakeSubsystemProvider"

        def load(self) -> type:
            return _FakeSubsystemProvider

    def _fake_entry_points(*, group: str) -> list[Any]:
        return [_FakeEntryPoint()] if group == "lexigram.ai.subsystems" else []

    monkeypatch.setattr(importlib.metadata, "entry_points", _fake_entry_points)

    provider = AIProvider(config=AIConfig(), disabled={"relay-gateway"})
    await provider.register(_FakeContainer())

    assert _FakeSubsystemProvider.registered_names == []