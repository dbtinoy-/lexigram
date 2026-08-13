"""Tests for resilience module."""

from __future__ import annotations

import inspect

import pytest

from lexigram.contracts.infra.resilience import (
    CircuitBreakerRegistryProtocol,
    ResiliencePipelineFactoryProtocol,
)
from lexigram.resilience import ResilienceModule


class TestResilienceModule:
    def test_resilience_module_exists(self) -> None:
        assert ResilienceModule is not None

    def test_configure_exports_pipeline_factory(self) -> None:
        module = ResilienceModule.configure()
        assert CircuitBreakerRegistryProtocol in module.exports
        assert ResiliencePipelineFactoryProtocol in module.exports

    def test_stub_exports_pipeline_factory(self) -> None:
        module = ResilienceModule.stub()
        assert CircuitBreakerRegistryProtocol in module.exports
        assert ResiliencePipelineFactoryProtocol in module.exports


class TestResiliencePipelineFactoryProtocolRegistration:
    @pytest.mark.asyncio
    async def test_resolving_pipeline_factory_returns_callable_not_crash(
        self,
    ) -> None:
        """ResiliencePipelineFactoryProtocol must resolve to the factory function itself.

        The singleton registration previously used ``instance=resilience_pipeline_factory``
        but ServiceStore.singleton() treats Python functions as zero-arg factories and
        calls them — crashing with missing-argument TypeError.  Fix: use
        ``factory=lambda: resilience_pipeline_factory`` so the lambda is called and
        returns the function.
        """
        from lexigram.di.container import Container
        from lexigram.resilience.di.provider import ResilienceProvider

        container = Container()
        provider = ResilienceProvider()
        await provider.register(container)

        factory = await container.resolve(ResiliencePipelineFactoryProtocol)

        # Must be a callable, and specifically the factory function (accepts 3 args).
        assert callable(factory), "resolved value must be callable"
        sig = inspect.signature(factory)
        params = list(sig.parameters.keys())
        assert len(params) == 3, (
            f"factory must accept (retry_config, circuit_config, timeout_config), "
            f"got {params}"
        )
