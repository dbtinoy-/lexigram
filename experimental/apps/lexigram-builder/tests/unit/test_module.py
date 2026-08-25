"""Tests for BuilderModule composition."""

from __future__ import annotations

from lexigram.builder.config import BuilderConfig
from lexigram.builder.controllers.builder_controller import BuilderController
from lexigram.builder.di.provider import BuilderProvider
from lexigram.builder.module import BuilderModule


class TestConfigure:
    def test_returns_dynamic_module_with_provider(self) -> None:
        dynamic = BuilderModule.configure()
        assert any(
            isinstance(p, BuilderProvider)
            or (isinstance(p, type) and issubclass(p, BuilderProvider))
            for p in dynamic.providers
        )

    def test_exports_controller_contract(self) -> None:
        dynamic = BuilderModule.configure()
        assert BuilderController in dynamic.exports

    def test_explicit_config_flows_into_provider(self) -> None:
        config = BuilderConfig(port=9999)
        dynamic = BuilderModule.configure(config=config)
        provider = next(p for p in dynamic.providers if isinstance(p, BuilderProvider))
        assert provider._explicit_config is config

    def test_module_metadata_attached(self) -> None:
        assert hasattr(BuilderModule, "__lexigram_module__")
