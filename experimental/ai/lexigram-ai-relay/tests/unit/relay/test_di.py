"""Tests for the relay DI module and provider registration."""

from __future__ import annotations

from importlib.metadata import EntryPoint
from typing import Any

import pytest

from lexigram.ai.relay import RelayModule
from lexigram.ai.relay.di.provider import RelayProvider
from lexigram.ai.relay.engine import RelayConverterEngine
from lexigram.ai.relay.registry import RelayConverterRegistry
from lexigram.contracts.ai.relay.protocols import (
    RelayConverterProtocol,
    RelayRegistryProtocol,
)
from lexigram.contracts.ai.relay.types import RelayFormat
from lexigram.contracts.core.provider import ProviderPriority
from lexigram.di.module import DynamicModule, Module
from lexigram.di.provider import Provider


class FakeRegistrar:
    """Minimal container registrar capturing singleton bindings."""

    def __init__(self, existing: Any = None) -> None:
        self.bindings: dict[Any, Any] = {}
        if existing is not None:
            self.bindings[RelayRegistryProtocol] = existing

    def singleton(
        self,
        service_type: type,
        instance: Any = None,
        *,
        name: str | None = None,
        factory: Any = None,
        validate: bool = True,
    ) -> None:
        self.bindings[service_type] = instance if instance is not None else factory

    def has(self, service_type: Any) -> bool:
        return service_type in self.bindings


def test_relay_module_is_module() -> None:
    """RelayModule exists and is decorated."""
    assert issubclass(RelayModule, Module)


def test_relay_module_configure_returns_dynamic_module() -> None:
    """configure() returns a DynamicModule exposing both protocols."""
    result = RelayModule.configure()
    assert isinstance(result, DynamicModule)
    assert result.module is RelayModule
    assert any(isinstance(provider, RelayProvider) for provider in result.providers)
    assert RelayConverterProtocol in result.exports
    assert RelayRegistryProtocol in result.exports


def test_relay_module_stub_returns_dynamic_module() -> None:
    """stub() returns a DynamicModule with the same registrations."""
    result = RelayModule.stub()
    assert isinstance(result, DynamicModule)
    assert result.module is RelayModule
    assert any(isinstance(provider, RelayProvider) for provider in result.providers)
    assert RelayConverterProtocol in result.exports
    assert RelayRegistryProtocol in result.exports


async def test_provider_registers_registry_and_engine() -> None:
    """register() binds the default registry and the engine class."""
    registrar = FakeRegistrar()
    provider = RelayProvider()
    await provider.register(registrar)

    registry_binding = registrar.bindings[RelayRegistryProtocol]
    assert isinstance(registry_binding, RelayConverterRegistry)
    assert registry_binding.route(RelayFormat.OPENAI_CHAT, RelayFormat.CLAUDE) is not None

    engine_binding = registrar.bindings[RelayConverterProtocol]
    assert engine_binding is RelayConverterEngine


async def test_provider_does_not_override_caller_registry() -> None:
    """register() never replaces an existing caller-owned registry."""
    caller_registry = RelayConverterRegistry.with_defaults()
    registrar = FakeRegistrar(existing=caller_registry)
    provider = RelayProvider()
    await provider.register(registrar)

    assert registrar.bindings[RelayRegistryProtocol] is caller_registry
    assert len(registrar.bindings) == 2


def test_provider_metadata() -> None:
    """The provider declares stable name and priority."""
    provider = RelayProvider()
    assert provider.name == "ai-relay"
    assert provider.priority is ProviderPriority.DOMAIN
    assert isinstance(provider, Provider)


async def test_provider_boot_and_shutdown_noop() -> None:
    """boot() and shutdown() complete without side effects."""
    provider = RelayProvider()
    await provider.boot(None)
    await provider.shutdown()


def test_entry_points_resolve() -> None:
    """The relay provider and module resolve via all three entry-point groups."""
    provider_ep = EntryPoint(
        name="relay",
        value="lexigram.ai.relay.di.provider:RelayProvider",
        group="lexigram.providers",
    )
    assert provider_ep.load() is RelayProvider

    subsystem_ep = EntryPoint(
        name="relay",
        value="lexigram.ai.relay.di.provider:RelayProvider",
        group="lexigram.ai.subsystems",
    )
    assert subsystem_ep.load() is RelayProvider

    module_ep = EntryPoint(
        name="relay",
        value="lexigram.ai.relay.module:RelayModule",
        group="lexigram.ai.modules",
    )
    assert module_ep.load() is RelayModule


async def test_entry_point_discovery_produces_registered_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Discovery over the subsystems group yields a working provider."""
    import importlib.metadata as metadata

    from lexigram.di.provider import Provider as ProviderBase

    entry_point = EntryPoint(
        name="relay",
        value="lexigram.ai.relay.di.provider:RelayProvider",
        group="lexigram.ai.subsystems",
    )

    def fake_entry_points(**kwargs: Any) -> Any:
        group = kwargs.get("group")
        if group == "lexigram.ai.subsystems":
            return [entry_point]
        return []

    monkeypatch.setattr(metadata, "entry_points", fake_entry_points)

    discovered = [
        ep.load()
        for ep in metadata.entry_points(group="lexigram.ai.subsystems")
    ]
    assert discovered == [RelayProvider]
    registrar = FakeRegistrar()
    await discovered[0]().register(registrar)
    assert RelayRegistryProtocol in registrar.bindings
    assert RelayConverterProtocol in registrar.bindings
    assert isinstance(discovered[0](), ProviderBase)