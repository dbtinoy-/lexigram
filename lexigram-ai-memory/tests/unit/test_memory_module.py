"""Tests for memory module."""

from __future__ import annotations

import pytest

from lexigram.ai.memory import MemoryModule
from lexigram.contracts.ai.memory import (
    EpisodicMemoryProtocol,
    MemoryConsolidatorProtocol,
    MemoryStoreProtocol,
    SemanticMemoryProtocol,
    WorkingMemoryProtocol,
)
from lexigram.di.module import DynamicModule
from lexigram.di.module.constants import MODULE_METADATA_ATTR


class TestMemoryModule:
    """Test suite for MemoryModule."""

    def test_module_decorator_exists(self) -> None:
        """Verify @module decorator is applied to MemoryModule."""
        assert hasattr(MemoryModule, MODULE_METADATA_ATTR)

    def test_configure_returns_dynamic_module(self) -> None:
        """Verify configure() returns DynamicModule instance."""
        result = MemoryModule.configure(None)
        assert isinstance(result, DynamicModule)
        assert result.module is MemoryModule

    def test_configure_exports_memory_protocols(self) -> None:
        """Verify configure() exports all memory protocols."""
        result = MemoryModule.configure(None)
        expected_protocols = [
            MemoryStoreProtocol,
            EpisodicMemoryProtocol,
            SemanticMemoryProtocol,
            WorkingMemoryProtocol,
            MemoryConsolidatorProtocol,
        ]
        for protocol in expected_protocols:
            assert protocol in result.exports

    def test_configure_with_dict_config(self) -> None:
        """Verify configure() accepts dict configuration."""
        config = {"backend": "memory"}
        result = MemoryModule.configure(config)
        assert isinstance(result, DynamicModule)
        assert result.module is MemoryModule
