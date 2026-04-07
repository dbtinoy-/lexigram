"""Tests for QueueProvider Named DI registration."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.contracts.queue.protocols import QueueProtocol
from lexigram.queue.config import KafkaDriverConfig, NamedQueueConfig, QueueConfig
from lexigram.queue.di.provider import QueueProvider


class TestQueueProvider:
    """Test QueueProvider."""

    @pytest.fixture
    def mock_container(self) -> MagicMock:
        """Create a mock container."""
        container = MagicMock()
        container.singleton = MagicMock()
        container.resolve_optional = AsyncMock(return_value=None)
        return container

    @pytest.fixture
    def memory_config(self) -> QueueConfig:
        """Create a single memory backend config."""
        return QueueConfig(
            backends=[
                NamedQueueConfig(name="memory", driver="memory", primary=True)
            ]
        )

    @pytest.fixture
    def multi_backend_config(self) -> QueueConfig:
        """Create a multi-backend config."""
        return QueueConfig(
            backends=[
                NamedQueueConfig(
                    name="memory",
                    driver="memory",
                ),
                NamedQueueConfig(
                    name="kafka",
                    driver="kafka",
                    primary=True,
                    kafka=KafkaDriverConfig(bootstrap_servers="localhost:9092"),
                ),
            ]
        )

    @pytest.mark.asyncio
    async def test_registers_config(
        self, mock_container: MagicMock, memory_config: QueueConfig
    ) -> None:
        """register() should register the QueueConfig."""
        provider = QueueProvider(config=memory_config)
        await provider.register(mock_container)

        # Check that QueueConfig was registered
        config_calls = [
            c for c in mock_container.singleton.call_args_list
            if c.args and c.args[0] is QueueConfig
        ]
        assert len(config_calls) > 0

    @pytest.mark.asyncio
    async def test_registers_named_binding(
        self, mock_container: MagicMock, memory_config: QueueConfig
    ) -> None:
        """register() should create named QueueProtocol bindings."""
        provider = QueueProvider(config=memory_config)
        await provider.register(mock_container)

        calls = mock_container.singleton.call_args_list
        named_calls = [
            c for c in calls
            if c.args and c.args[0] is QueueProtocol and c.kwargs.get("name")
        ]
        assert len(named_calls) >= 1

    @pytest.mark.asyncio
    async def test_registers_primary_unnamed(
        self, mock_container: MagicMock, memory_config: QueueConfig
    ) -> None:
        """register() should register primary backend without name."""
        provider = QueueProvider(config=memory_config)
        await provider.register(mock_container)

        calls = mock_container.singleton.call_args_list
        unnamed_calls = [
            c for c in calls
            if c.args and c.args[0] is QueueProtocol and not c.kwargs.get("name")
        ]
        assert len(unnamed_calls) >= 1

    @pytest.mark.asyncio
    async def test_multi_backend_named_bindings(
        self, mock_container: MagicMock, multi_backend_config: QueueConfig
    ) -> None:
        """register() should create named bindings for each backend."""
        provider = QueueProvider(config=multi_backend_config)
        await provider.register(mock_container)

        calls = mock_container.singleton.call_args_list
        memory_calls = [
            c for c in calls
            if c.args and c.args[0] is QueueProtocol and c.kwargs.get("name") == "memory"
        ]
        kafka_calls = [
            c for c in calls
            if c.args and c.args[0] is QueueProtocol and c.kwargs.get("name") == "kafka"
        ]
        assert len(memory_calls) >= 1
        assert len(kafka_calls) >= 1

    @pytest.mark.asyncio
    async def test_boot_health_checks(
        self, mock_container: MagicMock, memory_config: QueueConfig
    ) -> None:
        """boot() should health-check backends."""
        provider = QueueProvider(config=memory_config)
        await provider.register(mock_container)
        # boot() doesn't require mock_container calls, just should not raise
        await provider.boot(mock_container)

    @pytest.mark.asyncio
    async def test_boot_resolves_and_wires_optional_tracer(
        self, mock_container: MagicMock, memory_config: QueueConfig
    ) -> None:
        """boot() should resolve optional tracer and wire it into backends.
        
        This test verifies that:
        1. QueueProvider.boot() awaits resolve_optional(TracerProtocol)
        2. The resolved tracer is wired into backends via set_tracer()
        """
        from lexigram.testing.fakes import FakeTracer

        tracer = FakeTracer()
        
        # Setup mock_container to return the tracer when resolve_optional is called
        async def mock_resolve_optional(contract_type):
            from lexigram.contracts.observability.tracing import TracerProtocol
            if contract_type is TracerProtocol:
                return tracer
            return None

        mock_container.resolve_optional = AsyncMock(side_effect=mock_resolve_optional)
        
        provider = QueueProvider(config=memory_config)
        await provider.register(mock_container)
        await provider.boot(mock_container)

        # Verify resolve_optional was called for TracerProtocol
        from lexigram.contracts.observability.tracing import TracerProtocol
        
        resolve_calls = [
            call for call in mock_container.resolve_optional.call_args_list
            if call.args and call.args[0] is TracerProtocol
        ]
        assert len(resolve_calls) > 0, "resolve_optional(TracerProtocol) was not called"

        # Verify backend received the tracer
        for _name, backend in provider._queue_services:
            if hasattr(backend, "_tracer"):
                assert backend._tracer is tracer, f"Backend {_name} did not receive tracer"


    async def test_shutdown(
        self, mock_container: MagicMock, memory_config: QueueConfig
    ) -> None:
        """shutdown() should close backends."""
        provider = QueueProvider(config=memory_config)
        await provider.register(mock_container)
        # shutdown() should not raise
        await provider.shutdown()

    @pytest.mark.asyncio
    async def test_health_check(
        self, mock_container: MagicMock, memory_config: QueueConfig
    ) -> None:
        """health_check() should return HealthCheckResult."""
        provider = QueueProvider(config=memory_config)
        await provider.register(mock_container)
        result = await provider.health_check()
        assert result is not None


__all__ = ["TestQueueProvider"]
