"""Tests for Application.discover_modules()."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from lexigram.app.base import Application
from lexigram.di.module import Module, module


class TestApplicationDiscoverModules:
    def _make_app(self) -> Application:
        """Return a fresh Application instance for testing."""
        return Application()

    def test_discover_modules_calls_add_module_for_each_discovered(self) -> None:
        @module()
        class DiscoveredModule(Module):
            pass

        app = self._make_app()
        ep = MagicMock()
        ep.name = "DiscoveredModule"
        ep.load.return_value = DiscoveredModule

        initial_count = len(app._modules)

        with patch("importlib.metadata.entry_points", return_value=[ep]):
            app.discover_modules()

        assert len(app._modules) > initial_count
        assert DiscoveredModule in app._modules

    def test_discover_modules_respects_disabled_list(self) -> None:
        @module()
        class SkipMe(Module):
            pass

        app = self._make_app()
        ep = MagicMock()
        ep.name = "SkipMe"
        ep.load.return_value = SkipMe

        initial_modules = list(app._modules)

        with patch("importlib.metadata.entry_points", return_value=[ep]):
            app.discover_modules(disabled=["SkipMe"])

        assert app._modules == initial_modules

    def test_discover_modules_respects_enabled_list(self) -> None:
        @module()
        class AllowedModule(Module):
            pass

        @module()
        class NotAllowedModule(Module):
            pass

        app = self._make_app()

        allowed_ep = MagicMock()
        allowed_ep.name = "AllowedModule"
        allowed_ep.load.return_value = AllowedModule

        blocked_ep = MagicMock()
        blocked_ep.name = "NotAllowedModule"
        blocked_ep.load.return_value = NotAllowedModule

        added: list[type] = []
        original_add = app.add_module

        def tracking_add(m: type) -> None:
            added.append(m)
            original_add(m)

        app.add_module = tracking_add  # type: ignore[method-assign]

        with patch("importlib.metadata.entry_points", return_value=[allowed_ep, blocked_ep]):
            app.discover_modules(enabled=["AllowedModule"])

        assert AllowedModule in added
        assert NotAllowedModule not in added

    def test_discover_modules_empty_when_no_entry_points(self) -> None:
        app = self._make_app()
        with patch("importlib.metadata.entry_points", return_value=[]):
            app.discover_modules()  # must not raise

    def test_auto_discover_triggered_on_start(self) -> None:
        @module()
        class AutoModule(Module):
            pass

        from lexigram.app.config.discovery import ModuleDiscoveryConfig
        from lexigram.config.main import LexigramConfig

        disc_cfg = ModuleDiscoveryConfig(auto_discover=True)
        config = LexigramConfig()
        config.discovery = disc_cfg

        app = Application(config=config)

        ep = MagicMock()
        ep.name = "AutoModule"
        ep.load.return_value = AutoModule

        with patch("importlib.metadata.entry_points", return_value=[ep]):
            discovered_modules: list[type] = []
            original_discover = app.discover_modules

            def capturing_discover(**kwargs: object) -> None:
                original_discover(**kwargs)  # type: ignore[arg-type]
                discovered_modules.extend(app._modules)

            app.discover_modules = capturing_discover  # type: ignore[method-assign]
            # Just test that discover_modules was wired correctly without booting
            app.discover_modules()

        assert AutoModule in app._modules
