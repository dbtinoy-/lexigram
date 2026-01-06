"""Tests for QueueModule."""

from __future__ import annotations

import pytest

from lexigram.contracts.queue.protocols import QueueProtocol
from lexigram.di.module import DynamicModule
from lexigram.queue.config import NamedQueueConfig, QueueConfig
from lexigram.queue.module import QueueModule


class TestQueueModule:
    """Test QueueModule."""

    def test_configure_returns_dynamic_module(self) -> None:
        """configure() should return a DynamicModule."""
        config = QueueConfig(
            backends=[NamedQueueConfig(name="memory", driver="memory", primary=True)]
        )
        result = QueueModule.configure(config)
        assert isinstance(result, DynamicModule)

    def test_configure_exports_protocol(self) -> None:
        """configure() should export QueueProtocol."""
        config = QueueConfig(
            backends=[NamedQueueConfig(name="memory", driver="memory", primary=True)]
        )
        result = QueueModule.configure(config)
        assert QueueProtocol in result.exports

    def test_stub_returns_dynamic_module(self) -> None:
        """stub() should return a DynamicModule."""
        result = QueueModule.stub()
        assert isinstance(result, DynamicModule)

    def test_stub_exports_protocol(self) -> None:
        """stub() should export QueueProtocol."""
        result = QueueModule.stub()
        assert QueueProtocol in result.exports

    def test_stub_creates_memory_backend(self) -> None:
        """stub() should create a DynamicModule with default (memory) config."""
        result = QueueModule.stub()
        assert isinstance(result, DynamicModule)
        # Should have providers
        assert len(result.providers) > 0


__all__ = ["TestQueueModule"]
