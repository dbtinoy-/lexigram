"""Tests for MCPClientModule, MCPConnection, MCPClientRegistry, MCPClientProvider.

Covers:
- MCPConnection.stdio() and .sse() factory methods
- MCPConnection.build_transport() and .build_client()
- MCPConnection validation (empty command / url)
- MCPClientRegistry.get(), .names(), error on unknown name
- MCPClientModule.configure() validation
- MCPClientModule.providers() returns MCPClientProvider
- MCPClientProvider.register() registers registry + primary client
- Integration: module accessible via lexigram.ai.mcp namespace
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest


# ═════════════════════════════════════════════════════════════════════════════
# MCPConnection
# ═════════════════════════════════════════════════════════════════════════════


class TestMCPConnectionStdio:
    def test_stdio_creates_connection(self) -> None:
        from lexigram.ai.mcp.client import MCPConnection

        conn = MCPConnection.stdio(["uvx", "mcp-server-git"], name="git")
        assert conn.name == "git"
        assert conn.transport_type == "stdio"
        assert conn.command == ["uvx", "mcp-server-git"]

    def test_stdio_default_timeouts(self) -> None:
        from lexigram.ai.mcp.client import MCPConnection

        conn = MCPConnection.stdio(["uvx"], name="x")
        assert conn.request_timeout == 30.0
        assert conn.startup_timeout == 10.0

    def test_stdio_custom_timeouts(self) -> None:
        from lexigram.ai.mcp.client import MCPConnection

        conn = MCPConnection.stdio(
            ["uvx"],
            name="x",
            startup_timeout=5.0,
            request_timeout=60.0,
        )
        assert conn.startup_timeout == 5.0
        assert conn.request_timeout == 60.0

    def test_stdio_empty_command_raises(self) -> None:
        from lexigram.ai.mcp.client import MCPConnection

        with pytest.raises(ValueError, match="command must not be empty"):
            MCPConnection.stdio([], name="x")

    def test_stdio_with_env(self) -> None:
        from lexigram.ai.mcp.client import MCPConnection

        conn = MCPConnection.stdio(["cmd"], name="x", env={"GIT_DIR": "/tmp"})
        assert conn.env == {"GIT_DIR": "/tmp"}


class TestMCPConnectionSSE:
    def test_sse_creates_connection(self) -> None:
        from lexigram.ai.mcp.client import MCPConnection

        conn = MCPConnection.sse("http://localhost:8080/mcp", name="analytics")
        assert conn.name == "analytics"
        assert conn.transport_type == "sse"
        assert conn.url == "http://localhost:8080/mcp"

    def test_sse_default_timeout(self) -> None:
        from lexigram.ai.mcp.client import MCPConnection

        conn = MCPConnection.sse("http://example.com/mcp", name="x")
        assert conn.request_timeout == 30.0

    def test_sse_empty_url_raises(self) -> None:
        from lexigram.ai.mcp.client import MCPConnection

        with pytest.raises(ValueError, match="url must not be empty"):
            MCPConnection.sse("", name="x")

    def test_sse_with_headers(self) -> None:
        from lexigram.ai.mcp.client import MCPConnection

        conn = MCPConnection.sse(
            "http://x.com/mcp",
            name="x",
            headers={"Authorization": "Bearer tok"},
        )
        assert conn.headers == {"Authorization": "Bearer tok"}


class TestMCPConnectionBuildTransport:
    def test_builds_stdio_transport(self) -> None:
        from lexigram.ai.mcp.client import MCPConnection
        from lexigram.ai.mcp.client.core import StdioClientTransport

        conn = MCPConnection.stdio(["uvx", "tool"], name="t")
        transport = conn.build_transport()
        assert isinstance(transport, StdioClientTransport)

    def test_builds_sse_transport(self) -> None:
        from lexigram.ai.mcp.client import MCPConnection
        from lexigram.ai.mcp.client.core import SSEClientTransport

        conn = MCPConnection.sse("http://example.com/mcp", name="t")
        transport = conn.build_transport()
        assert isinstance(transport, SSEClientTransport)

    def test_unknown_transport_type_raises(self) -> None:
        from lexigram.ai.mcp.client import MCPConnection

        conn = MCPConnection(name="x", transport_type="grpc")
        with pytest.raises(ValueError, match="Unknown MCPConnection transport_type"):
            conn.build_transport()

    def test_builds_mcp_client(self) -> None:
        from lexigram.ai.mcp.client import MCPConnection
        from lexigram.ai.mcp.client.core import MCPClient

        conn = MCPConnection.stdio(["cmd"], name="t")
        client = conn.build_client()
        assert isinstance(client, MCPClient)


# ═════════════════════════════════════════════════════════════════════════════
# MCPClientRegistry
# ═════════════════════════════════════════════════════════════════════════════


class TestMCPClientRegistry:
    def _make_client(self) -> Any:
        from lexigram.ai.mcp.client.core import MCPClient, StdioClientTransport

        transport = StdioClientTransport(["echo"])
        return MCPClient(transport)

    def test_get_returns_registered_client(self) -> None:
        from lexigram.ai.mcp.client import MCPClientRegistry

        client = self._make_client()
        registry = MCPClientRegistry({"git": client})
        assert registry.get("git") is client

    def test_get_unknown_raises_key_error(self) -> None:
        from lexigram.ai.mcp.client import MCPClientRegistry

        registry = MCPClientRegistry({"git": self._make_client()})
        with pytest.raises(KeyError, match="phantom"):
            registry.get("phantom")

    def test_names_returns_sorted_list(self) -> None:
        from lexigram.ai.mcp.client import MCPClientRegistry

        registry = MCPClientRegistry(
            {
                "z_tool": self._make_client(),
                "a_tool": self._make_client(),
            }
        )
        assert registry.names() == ["a_tool", "z_tool"]

    def test_len_returns_number_of_clients(self) -> None:
        from lexigram.ai.mcp.client import MCPClientRegistry

        registry = MCPClientRegistry(
            {"c1": self._make_client(), "c2": self._make_client()}
        )
        assert len(registry) == 2

    def test_repr_contains_connection_names(self) -> None:
        from lexigram.ai.mcp.client import MCPClientRegistry

        registry = MCPClientRegistry({"git": self._make_client()})
        assert "git" in repr(registry)


# ═════════════════════════════════════════════════════════════════════════════
# MCPClientModule
# ═════════════════════════════════════════════════════════════════════════════


class TestMCPClientModule:
    def _conn(self, name: str = "test") -> Any:
        from lexigram.ai.mcp.client import MCPConnection

        return MCPConnection.stdio(["cmd"], name=name)

    def test_configure_returns_module(self) -> None:
        from lexigram.ai.mcp.client import MCPClientModule

        module = MCPClientModule.configure([self._conn()])
        assert isinstance(module, MCPClientModule)

    def test_configure_empty_raises(self) -> None:
        from lexigram.ai.mcp.client import MCPClientModule

        with pytest.raises(ValueError, match="At least one"):
            MCPClientModule.configure([])

    def test_configure_duplicate_names_raises(self) -> None:
        from lexigram.ai.mcp.client import MCPClientModule

        with pytest.raises(ValueError, match="Duplicate"):
            MCPClientModule.configure([self._conn("x"), self._conn("x")])

    def test_providers_returns_mcp_client_provider(self) -> None:
        from lexigram.ai.mcp.client import MCPClientModule, MCPClientProvider

        module = MCPClientModule.configure([self._conn()])
        providers = module.providers()
        assert len(providers) == 1
        assert isinstance(providers[0], MCPClientProvider)


# ═════════════════════════════════════════════════════════════════════════════
# MCPClientProvider.register()
# ═════════════════════════════════════════════════════════════════════════════


class TestMCPClientProvider:
    def _make_container(self) -> tuple[Any, dict]:
        store: dict = {}

        class FakeContainer:
            def singleton(self, key, value):
                store[key] = value

            def resolve(self, key):
                return store[key]

        return FakeContainer(), store

    @pytest.mark.asyncio
    async def test_registers_registry(self) -> None:
        from lexigram.ai.mcp.client import (
            MCPClientProvider,
            MCPClientRegistry,
            MCPConnection,
        )

        conn = MCPConnection.stdio(["cmd"], name="git")
        provider = MCPClientProvider([conn])
        container, store = self._make_container()
        await provider.register(container)

        assert MCPClientRegistry in store
        registry = store[MCPClientRegistry]
        assert isinstance(registry, MCPClientRegistry)
        assert "git" in registry.names()

    @pytest.mark.asyncio
    async def test_registers_primary_client(self) -> None:
        from lexigram.ai.mcp.client import MCPClientProvider, MCPConnection
        from lexigram.ai.mcp.client.core import MCPClient

        conn = MCPConnection.stdio(["cmd"], name="primary")
        provider = MCPClientProvider([conn])
        container, store = self._make_container()
        await provider.register(container)

        assert MCPClient in store

    @pytest.mark.asyncio
    async def test_multiple_connections_all_in_registry(self) -> None:
        from lexigram.ai.mcp.client import (
            MCPClientProvider,
            MCPClientRegistry,
            MCPConnection,
        )

        conn1 = MCPConnection.stdio(["cmd1"], name="server1")
        conn2 = MCPConnection.sse("http://x.com/mcp", name="server2")
        provider = MCPClientProvider([conn1, conn2])
        container, store = self._make_container()
        await provider.register(container)

        registry: MCPClientRegistry = store[MCPClientRegistry]
        assert set(registry.names()) == {"server1", "server2"}

    @pytest.mark.asyncio
    async def test_primary_client_is_first_connection(self) -> None:
        from lexigram.ai.mcp.client import (
            MCPClientProvider,
            MCPClientRegistry,
            MCPConnection,
        )
        from lexigram.ai.mcp.client.core import MCPClient

        conn1 = MCPConnection.stdio(["cmd1"], name="first")
        conn2 = MCPConnection.stdio(["cmd2"], name="second")
        provider = MCPClientProvider([conn1, conn2])
        container, store = self._make_container()
        await provider.register(container)

        registry: MCPClientRegistry = store[MCPClientRegistry]
        primary: MCPClient = store[MCPClient]
        # Primary client should be the same object as registry.get("first")
        assert primary is registry.get("first")


# ═════════════════════════════════════════════════════════════════════════════
# Namespace / import
# ═════════════════════════════════════════════════════════════════════════════


class TestMCPClientModuleNamespace:
    def test_imports_from_package_namespace(self) -> None:
        from lexigram.ai.mcp import (
            MCPClientModule,
            MCPClientRegistry,
            MCPConnection,
        )

        assert MCPClientModule is not None
        assert MCPClientRegistry is not None
        assert MCPConnection is not None

    def test_connection_in_all(self) -> None:
        from lexigram.ai.mcp import __all__

        assert "MCPClientModule" in __all__
        assert "MCPClientRegistry" in __all__
        assert "MCPConnection" in __all__
