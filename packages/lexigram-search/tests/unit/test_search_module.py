"""Tests for search module."""

from lexigram.di.module import DynamicModule
from lexigram.search import SearchModule


class TestSearchModule:
    def test_search_module_exists(self) -> None:
        assert SearchModule is not None

    def test_configure_without_config_defers_to_injection(self) -> None:
        """Zero-arg configure() builds a provider that defers backend
        composition to register(), where the orchestrator injects the
        yaml ``search`` section (dual-mode AUTO path)."""
        dm = SearchModule.configure(None)
        assert isinstance(dm, DynamicModule)
        provider = dm.providers[0]
        assert provider.backend is None
        assert provider._config is None
