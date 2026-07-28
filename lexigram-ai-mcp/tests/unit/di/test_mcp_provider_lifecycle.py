"""Lifecycle-focused tests for MCPProvider."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from lexigram.ai.mcp.config import MCPConfig
from lexigram.ai.mcp.di.provider import MCPProvider
from lexigram.ai.mcp.transport import SSETransport, StdioTransport


class _ContainerStub:
    def __init__(self) -> None:
        self.bindings: dict[type, object] = {}

    def singleton(self, service_type: type, instance: object) -> None:
        self.bindings[service_type] = instance


@pytest.mark.asyncio
async def test_shutdown_stops_managed_transports_and_disconnects_client() -> None:
    """shutdown() should stop transports and disconnect the managed MCP client."""
    provider = MCPProvider()

    transport_a = AsyncMock()
    transport_b = AsyncMock()
    client = AsyncMock()

    provider._managed_transports = [transport_a, transport_b]
    provider._managed_client = client

    await provider.shutdown()

    transport_a.stop.assert_awaited_once()
    transport_b.stop.assert_awaited_once()
    client.disconnect.assert_awaited_once()


def test_boot_transports_registers_concrete_transport_instances() -> None:
    """_boot_transports() should bind each concrete transport type correctly."""
    provider = MCPProvider(config=MCPConfig(stdio_mode=False))
    container = _ContainerStub()

    provider._boot_transports(container)

    assert isinstance(container.bindings[SSETransport], SSETransport)
    assert isinstance(container.bindings[StdioTransport], StdioTransport)
