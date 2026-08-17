"""Tests for session module."""

from __future__ import annotations

import pytest

from lexigram.ai.session import SessionModule
from lexigram.contracts.ai.session import SessionManagerProtocol, SessionStoreProtocol
from lexigram.di.module import DynamicModule


class TestSessionModule:
    """Test suite for SessionModule."""

    def test_module_decorator_exists(self) -> None:
        """Verify @module decorator is applied to SessionModule."""
        assert hasattr(SessionModule, '__lexigram_module__')

    def test_configure_returns_dynamic_module(self) -> None:
        """Verify configure() returns DynamicModule instance."""
        result = SessionModule.configure(None)
        assert isinstance(result, DynamicModule)
        assert result.module is SessionModule

    def test_configure_exports_session_protocols(self) -> None:
        """Verify configure() exports session protocols."""
        result = SessionModule.configure(None)
        assert SessionStoreProtocol in result.exports
        assert SessionManagerProtocol in result.exports

    def test_configure_with_dict_config(self) -> None:
        """Verify configure() accepts dict configuration."""
        config = {"backend": "memory"}
        result = SessionModule.configure(config)
        assert isinstance(result, DynamicModule)
        assert result.module is SessionModule
