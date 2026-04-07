"""Tests for AI module."""

from __future__ import annotations
from enum import Enum

import pytest

from lexigram.ai import AIModule
from lexigram.contracts.ai import AIProviderProtocol
from lexigram.di.module import DynamicModule


class TestAIModule:
    """Test suite for AIModule."""

    def test_module_decorator_exists(self) -> None:
        """Verify @module decorator is applied to AIModule."""
        assert hasattr(AIModule, '__lexigram_module__')

    def test_configure_returns_dynamic_module(self) -> None:
        """Verify configure() returns DynamicModule instance."""
        result = AIModule.configure(None)
        assert isinstance(result, DynamicModule)
        assert result.module is AIModule

    def test_configure_exports_ai_provider_protocol(self) -> None:
        """Verify configure() exports AIProviderProtocol."""
        result = AIModule.configure(None)
        assert AIProviderProtocol in result.exports

    def test_configure_with_dict_config(self) -> None:
        """Verify configure() accepts dict configuration."""
        config = {"enable_governance": True}
        result = AIModule.configure(config)
        assert isinstance(result, DynamicModule)
        assert result.module is AIModule
