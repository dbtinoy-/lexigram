"""Tests for MCP server core module."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock


class TestMCPServer:
    """Tests for MCPServer."""

    def test_constructor_default(self) -> None:
        from lexigram.ai.mcp.server.core import MCPServer

        server = MCPServer()
        assert server._name == "lexigram-mcp"
        assert server._version == "1.0.0"

    def test_constructor_with_name(self) -> None:
        from lexigram.ai.mcp.server.core import MCPServer

        server = MCPServer(name="my-server")
        assert server._name == "my-server"

    def test_constructor_with_version(self) -> None:
        from lexigram.ai.mcp.server.core import MCPServer

        server = MCPServer(version="2.0.0")
        assert server._version == "2.0.0"

    def test_constructor_with_handlers(self) -> None:
        from lexigram.ai.mcp.server.core import MCPServer

        tool_handler = MagicMock()
        resource_handler = MagicMock()
        prompt_handler = MagicMock()

        server = MCPServer(
            tool_handler=tool_handler,
            resource_handler=resource_handler,
            prompt_handler=prompt_handler,
        )
        assert server._tool_handler is tool_handler
        assert server._resource_handler is resource_handler
        assert server._prompt_handler is prompt_handler

    def test_has_handlers_dict(self) -> None:
        from lexigram.ai.mcp.server.core import MCPServer

        server = MCPServer()
        assert hasattr(server, "_handlers")
        assert isinstance(server._handlers, dict)

    def test_initializes_handlers_on_creation(self) -> None:
        from lexigram.ai.mcp.server.core import MCPServer

        server = MCPServer()
        assert "initialize" in server._handlers
        assert "ping" in server._handlers

    def test_tool_handlers_registered(self) -> None:
        from lexigram.ai.mcp.server.core import MCPServer

        tool_handler = MagicMock()
        server = MCPServer(tool_handler=tool_handler)
        assert "tools/list" in server._handlers
        assert "tools/call" in server._handlers

    def test_resource_handlers_registered(self) -> None:
        from lexigram.ai.mcp.server.core import MCPServer

        resource_handler = MagicMock()
        server = MCPServer(resource_handler=resource_handler)
        assert "resources/list" in server._handlers
        assert "resources/read" in server._handlers

    def test_prompt_handlers_registered(self) -> None:
        from lexigram.ai.mcp.server.core import MCPServer

        prompt_handler = MagicMock()
        server = MCPServer(prompt_handler=prompt_handler)
        assert "prompts/list" in server._handlers
        assert "prompts/get" in server._handlers

    @pytest.mark.asyncio
    async def test_handle_initialize_message(self) -> None:
        from lexigram.ai.mcp.server.core import MCPServer

        server = MCPServer()
        message = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
        response = await server.handle_message(message)

        assert response is not None
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response
        assert "protocolVersion" in response["result"]

    @pytest.mark.asyncio
    async def test_handle_ping_message(self) -> None:
        from lexigram.ai.mcp.server.core import MCPServer

        server = MCPServer()
        message = {"jsonrpc": "2.0", "id": 1, "method": "ping", "params": {}}
        response = await server.handle_message(message)

        assert response is not None
        assert response["result"] == {}

    @pytest.mark.asyncio
    async def test_handle_invalid_jsonrpc_version(self) -> None:
        from lexigram.ai.mcp.server.core import MCPServer

        server = MCPServer()
        message = {"jsonrpc": "1.0", "id": 1, "method": "ping"}
        response = await server.handle_message(message)

        assert response is not None
        assert "error" in response
        assert response["error"]["code"] == -32600

    @pytest.mark.asyncio
    async def test_handle_missing_method(self) -> None:
        from lexigram.ai.mcp.server.core import MCPServer

        server = MCPServer()
        message = {"jsonrpc": "2.0", "id": 1, "method": "nonexistent"}
        response = await server.handle_message(message)

        assert response is not None
        assert "error" in response
        assert response["error"]["code"] == -32601

    @pytest.mark.asyncio
    async def test_notification_no_response(self) -> None:
        from lexigram.ai.mcp.server.core import MCPServer

        server = MCPServer()
        message = {"jsonrpc": "2.0", "method": "notifications/initialized"}
        response = await server.handle_message(message)

        assert response is None


class TestMCPServerConstants:
    """Tests for server constants."""

    def test_jsonrpc_version(self) -> None:
        from lexigram.ai.mcp.server.core import JSONRPC_VERSION

        assert JSONRPC_VERSION == "2.0"

    def test_mcp_protocol_version(self) -> None:
        from lexigram.ai.mcp.server.core import MCP_PROTOCOL_VERSION

        assert MCP_PROTOCOL_VERSION == "2024-11-05"


class TestServerExports:
    """Tests for server module exports."""

    def test_all_exported(self) -> None:
        from lexigram.ai.mcp.server import core

        expected = ["MCPServer"]
        for name in expected:
            assert hasattr(core, name)