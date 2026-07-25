"""Config-alignment tests for ObservabilityProvider."""

from __future__ import annotations

import pytest

from lexigram.ai.observability.config import ObservabilityConfig
from lexigram.ai.observability.di.provider import ObservabilityProvider
from lexigram.ai.observability.tracing import AITracer
from lexigram.contracts.observability.ai import AITracerProtocol


class _FakeRegistrar:
    def __init__(self) -> None:
        self.singletons: dict[type, object] = {}

    def singleton(
        self,
        service_type: type,
        instance: object = None,
        *,
        name: str | None = None,
        factory: object = None,
        validate: bool = True,
    ) -> None:
        self.singletons[service_type] = factory if factory is not None else instance

    def bind(self, service_type: type, instance: object) -> None:
        self.singletons[service_type] = instance

    def transient(
        self, service_type: type, factory: object, validate: bool = True
    ) -> None:
        pass

    def scoped(
        self,
        service_type: type,
        factory: object,
        validate: bool = True,
        *,
        name: str | None = None,
    ) -> None:
        pass

    def has(self, service_type: type) -> bool:
        return service_type in self.singletons


class TestConfigAlignment:
    def test_provider_declares_config_key_and_model(self) -> None:
        provider = ObservabilityProvider()
        assert provider.config_key == ObservabilityConfig.config_section
        assert provider.config_model is ObservabilityConfig

    @pytest.mark.asyncio
    async def test_injected_config_used_when_no_explicit(self) -> None:
        provider = ObservabilityProvider()
        provider.config = ObservabilityConfig(enabled=False)
        container = _FakeRegistrar()

        await provider.register(container)

        assert container.singletons[ObservabilityConfig] is provider.config

    @pytest.mark.asyncio
    async def test_explicit_config_wins_over_injected(self) -> None:
        explicit = ObservabilityConfig(enabled=True)
        provider = ObservabilityProvider(config=explicit)
        provider.config = ObservabilityConfig(enabled=False)
        container = _FakeRegistrar()

        await provider.register(container)

        assert container.singletons[ObservabilityConfig] is explicit

    @pytest.mark.asyncio
    async def test_default_config_binds_when_nothing_supplied(self) -> None:
        provider = ObservabilityProvider()
        container = _FakeRegistrar()

        await provider.register(container)

        assert isinstance(
            container.singletons[ObservabilityConfig], ObservabilityConfig
        )


class TestRedactionWiring:
    @pytest.mark.asyncio
    async def test_redaction_disabled_by_default_registers_plain_class(self) -> None:
        provider = ObservabilityProvider()
        container = _FakeRegistrar()

        await provider.register(container)

        assert container.singletons[AITracer] is None
        assert container.singletons[AITracerProtocol] is AITracer

    @pytest.mark.asyncio
    async def test_redaction_enabled_registers_configured_instance(self) -> None:
        config = ObservabilityConfig(trace_redaction_enabled=True)
        provider = ObservabilityProvider(config=config)
        container = _FakeRegistrar()

        await provider.register(container)

        tracer = container.singletons[AITracer]
        assert isinstance(tracer, AITracer)
        assert tracer._redaction_policy is not None
        assert tracer._max_attribute_length is None
        assert container.singletons[AITracerProtocol] is tracer

    @pytest.mark.asyncio
    async def test_size_cap_registers_truncating_instance(self) -> None:
        config = ObservabilityConfig(trace_max_attribute_length=4096)
        provider = ObservabilityProvider(config=config)
        container = _FakeRegistrar()

        await provider.register(container)

        tracer = container.singletons[AITracer]
        assert isinstance(tracer, AITracer)
        assert tracer._redaction_policy is None
        assert tracer._max_attribute_length == 4096
        assert container.singletons[AITracerProtocol] is tracer
