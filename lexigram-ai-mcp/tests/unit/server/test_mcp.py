"""Unit tests for lexigram-ai-mcp configuration and server."""

from __future__ import annotations

import pytest

from lexigram.ai.mcp import MCPConfig, MCPServer
from lexigram.ai.mcp.exceptions import (
    MCPError,
    MCPInitializationError,
    MCPProtocolError,
    MCPTransportError,
)


class TestMCPConfig:
    """Tests for MCPConfig."""

    def test_default_config(self) -> None:
        """Test MCPConfig default values."""
        config = MCPConfig()

        assert config.host == "0.0.0.0"
        assert config.port == 8080
        assert config.path == "/mcp"
        assert config.enable_sse is True
        assert config.stdio_mode is False
        assert config.server_name == "lexigram-mcp"
        assert config.server_version == "1.0.0"
        assert config.cors_origins == []
        assert config.max_request_size == 1024 * 1024
        assert config.request_timeout == 30.0

    def test_custom_config(self) -> None:
        """Test MCPConfig with custom values."""
        config = MCPConfig(
            host="127.0.0.1",
            port=9000,
            path="/api/mcp",
            enable_sse=False,
            stdio_mode=True,
            server_name="my-server",
            server_version="2.0.0",
            cors_origins=["https://example.com"],
            max_request_size=2 * 1024 * 1024,
            request_timeout=60.0,
        )

        assert config.host == "127.0.0.1"
        assert config.port == 9000
        assert config.path == "/api/mcp"
        assert config.enable_sse is False
        assert config.stdio_mode is True
        assert config.server_name == "my-server"
        assert config.server_version == "2.0.0"
        assert config.cors_origins == ["https://example.com"]
        assert config.max_request_size == 2 * 1024 * 1024
        assert config.request_timeout == 60.0

    def test_port_validation_min(self) -> None:
        """Test port validation rejects values below 1."""
        with pytest.raises(ValueError, match="port"):
            MCPConfig(port=0)

    def test_port_validation_max(self) -> None:
        """Test port validation rejects values above 65535."""
        with pytest.raises(ValueError, match="port"):
            MCPConfig(port=70000)

    def test_request_timeout_validation(self) -> None:
        """Test request timeout validation."""
        with pytest.raises(ValueError, match="request_timeout"):
            MCPConfig(request_timeout=0.5)


class TestMCPExceptions:
    """Tests for MCP exception hierarchy."""

    def test_mcp_error_base(self) -> None:
        """Test MCPError is the base exception."""
        error = MCPError(message="Test error")
        assert "Test error" in str(error)

    def test_mcp_initialization_error(self) -> None:
        """Test MCPInitializationError."""
        error = MCPInitializationError(message="Init failed")
        assert isinstance(error, MCPError)

    def test_mcp_protocol_error(self) -> None:
        """Test MCPProtocolError."""
        error = MCPProtocolError(message="Protocol violation")
        assert isinstance(error, MCPError)

    def test_mcp_transport_error(self) -> None:
        """Test MCPTransportError."""
        error = MCPTransportError(message="Transport failed")
        assert isinstance(error, MCPError)

    def test_exception_hierarchy(self) -> None:
        """Test all MCP exceptions inherit from MCPError."""
        assert issubclass(MCPInitializationError, MCPError)
        assert issubclass(MCPProtocolError, MCPError)
        assert issubclass(MCPTransportError, MCPError)


class TestMCPServer:
    """Tests for MCPServer."""

    def test_server_creation(self) -> None:
        """Test MCPServer can be created."""
        config = MCPConfig()
        server = MCPServer(config=config)
        assert server.config == config

    def test_server_default_config(self) -> None:
        """Test MCPServer creates default config if not provided."""
        server = MCPServer()
        assert isinstance(server.config, MCPConfig)

    def test_server_name_from_config(self) -> None:
        """Test server uses name from config."""
        config = MCPConfig(server_name="test-mcp")
        server = MCPServer(config=config)
        assert server.config.server_name == "test-mcp"


class TestMCPTransport:
    """Tests for MCP transport mechanisms."""

    def test_stdio_transport_exists(self) -> None:
        """Test StdioTransport can be imported."""
        from lexigram.ai.mcp import StdioTransport

        # Basic instantiation test
        transport = StdioTransport()
        assert transport is not None

    def test_sse_transport_exists(self) -> None:
        """Test SSETransport can be imported."""
        from lexigram.ai.mcp import SSETransport

        transport = SSETransport()
        assert transport is not None


class TestMCPHandlers:
    """Tests for MCP request handlers."""

    def test_tool_handler_exists(self) -> None:
        """Test ToolHandler can be imported."""
        from lexigram.ai.mcp import ToolHandler

        assert ToolHandler is not None

    def test_resource_handler_exists(self) -> None:
        """Test ResourceHandler can be imported."""
        from lexigram.ai.mcp import ResourceHandler

        assert ResourceHandler is not None

    def test_prompt_handler_exists(self) -> None:
        """Test PromptHandler can be imported."""
        from lexigram.ai.mcp import PromptHandler

        assert PromptHandler is not None


class TestMCPModule:
    """Tests for MCPModule."""

    def test_mcp_module_exists(self) -> None:
        """Test MCPModule can be imported."""
        from lexigram.ai.mcp import MCPModule

        module = MCPModule()
        assert module is not None

    def test_mcp_module_configure_returns_dynamic_module(self) -> None:
        """Test MCPModule.configure() returns a DynamicModule with correct provider."""
        from lexigram.ai.mcp import MCPModule, MCPProvider
        from lexigram.di.module import DynamicModule

        dynamic = MCPModule.configure(config=MCPConfig())
        assert isinstance(dynamic, DynamicModule)
        assert any(isinstance(p, MCPProvider) for p in dynamic.providers)


class TestMCPProvider:
    """Tests for MCPProvider."""

    def test_mcp_provider_exists(self) -> None:
        """Test MCPProvider can be imported."""
        from lexigram.ai.mcp import MCPProvider

        provider = MCPProvider()
        assert provider.name == "mcp"
