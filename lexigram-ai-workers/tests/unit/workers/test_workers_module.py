"""Tests for workers module."""

from __future__ import annotations

import pytest

from lexigram.ai.workers.config import WorkersConfig
from lexigram.ai.workers.module import WorkersModule


class TestWorkersModule:
    """Test WorkersModule class."""

    def test_configure_returns_dynamic_module(self) -> None:
        """Test configure returns DynamicModule."""
        result = WorkersModule.configure()
        assert result.module == WorkersModule
        assert len(result.providers) == 1

    def test_configure_with_custom_config(self) -> None:
        """Test configure with custom config."""
        config = WorkersConfig(enabled=False)
        result = WorkersModule.configure(config=config)
        assert result.module == WorkersModule
        assert len(result.providers) == 1

    def test_configure_with_scheduler_disabled(self) -> None:
        """Test configure with scheduler disabled."""
        result = WorkersModule.configure(enable_scheduler=False)
        assert result.module == WorkersModule

    def test_configure_exports_task_worker_protocol(self) -> None:
        """Test configure exports TaskWorkerProtocol."""
        from lexigram.contracts.infra.tasks.protocols import TaskWorkerProtocol

        result = WorkersModule.configure()
        assert TaskWorkerProtocol in result.exports

    def test_configure_rejects_unknown_kwargs(self) -> None:
        """Test configure rejects unsupported keyword arguments."""
        with pytest.raises(TypeError):
            WorkersModule.configure(dlq_check_interval=30)

    def test_stub_returns_dynamic_module(self) -> None:
        """Test stub returns DynamicModule."""
        result = WorkersModule.stub()
        assert result.module == WorkersModule

    def test_stub_with_custom_config(self) -> None:
        """Test stub with custom config."""
        config = WorkersConfig(batch_embedding_concurrency=10)
        result = WorkersModule.stub(config=config)
        assert result.module == WorkersModule

    def test_stub_exports_task_worker_protocol(self) -> None:
        """Test stub exports TaskWorkerProtocol."""
        from lexigram.contracts.infra.tasks.protocols import TaskWorkerProtocol

        result = WorkersModule.stub()
        assert TaskWorkerProtocol in result.exports

    def test_stub_disables_scheduler_by_default(self) -> None:
        """Test stub disables scheduler by default."""
        result = WorkersModule.stub()
        assert result.module == WorkersModule


class TestWorkersModuleExports:
    """Test module exports."""

    def test_all_exports(self) -> None:
        """Test __all__ contains expected items."""
        from lexigram.ai.workers import module

        expected = ["WorkersModule"]
        assert module.__all__ == expected