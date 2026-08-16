"""Tests for web module."""

from __future__ import annotations

from lexigram.di.module import DynamicModule
from lexigram.web import WebModule


class TestWebModule:
    def test_web_module_exists(self) -> None:
        assert WebModule is not None

    def test_configure_returns_dynamic_module(self) -> None:
        result = WebModule.configure()
        assert isinstance(result, DynamicModule)
        assert result.module is WebModule

    def test_configure_with_custom_host(self) -> None:
        result = WebModule.configure(host="127.0.0.1")
        assert isinstance(result, DynamicModule)

    def test_configure_with_custom_port(self) -> None:
        result = WebModule.configure(port=9000)
        assert isinstance(result, DynamicModule)

    def test_configure_with_controllers(self) -> None:
        class DummyController:
            pass

        result = WebModule.configure(controllers=[DummyController])
        assert isinstance(result, DynamicModule)

    def test_configure_discovers_controllers_from_packages(self, monkeypatch) -> None:
        class DummyController:
            pass

        monkeypatch.setattr(
            "lexigram.web.routing.discovery.discover_controllers",
            lambda _packages: [DummyController],
        )

        result = WebModule.configure(discover=["dummy.package"])
        assert isinstance(result, DynamicModule)
        provider = result.providers[0]
        assert provider.controllers == [DummyController]

    def test_legacy_auto_discover_factory_is_removed(self) -> None:
        assert not hasattr(WebModule, "auto_discover")
