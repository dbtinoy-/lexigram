"""Unit tests for lexigram-ai-mcp types."""

import pytest

from lexigram.ai.mcp.types import (
    MCPInitializeResult,
    MCPJSONRPCRequest,
    MCPJSONRPCResponse,
    MCPPrompt,
    MCPPromptMessage,
    MCPResource,
    MCPResourceContent,
    MCPServerCapabilities,
    MCPServerInfo,
    MCPToolDefinition,
    MCPToolResult,
)


class TestMCPToolDefinition:
    """Tests for MCPToolDefinition dataclass."""

    def test_tool_definition_creation(self) -> None:
        """Test MCPToolDefinition creation."""
        tool = MCPToolDefinition(name="test_tool", description="A test tool")

        assert tool.name == "test_tool"
        assert tool.description == "A test tool"
        assert tool.input_schema == {}

    def test_tool_definition_to_dict(self) -> None:
        """Test MCPToolDefinition serialization."""
        tool = MCPToolDefinition(
            name="test_tool",
            description="A test tool",
            input_schema={"type": "object", "properties": {}},
        )
        result = tool.to_dict()

        assert result["name"] == "test_tool"
        assert result["description"] == "A test tool"
        assert result["inputSchema"] == {"type": "object", "properties": {}}


class TestMCPToolResult:
    """Tests for MCPToolResult dataclass."""

    def test_tool_result_creation(self) -> None:
        """Test MCPToolResult creation."""
        result = MCPToolResult(content=[{"type": "text", "text": "Hello"}])

        assert len(result.content) == 1
        assert result.is_error is False

    def test_tool_result_text_factory(self) -> None:
        """Test MCPToolResult.text factory method."""
        result = MCPToolResult.text("Hello world")

        assert result.content[0]["type"] == "text"
        assert result.content[0]["text"] == "Hello world"
        assert result.is_error is False

    def test_tool_result_error_factory(self) -> None:
        """Test MCPToolResult.error factory method."""
        result = MCPToolResult.error("Something went wrong")

        assert result.content[0]["type"] == "text"
        assert result.content[0]["text"] == "Something went wrong"
        assert result.is_error is True

    def test_tool_result_to_dict(self) -> None:
        """Test MCPToolResult serialization."""
        result = MCPToolResult.text("Hello")
        output = result.to_dict()

        assert "content" in output
        assert output["isError"] is False


class TestMCPResource:
    """Tests for MCPResource dataclass."""

    def test_resource_creation(self) -> None:
        """Test MCPResource creation."""
        resource = MCPResource(uri="file://test.txt", name="Test File")

        assert resource.uri == "file://test.txt"
        assert resource.name == "Test File"
        assert resource.description == ""
        assert resource.mime_type == "text/plain"

    def test_resource_to_dict(self) -> None:
        """Test MCPResource serialization."""
        resource = MCPResource(
            uri="file://test.txt",
            name="Test File",
            description="A test file",
            mime_type="text/plain",
        )
        result = resource.to_dict()

        assert result["uri"] == "file://test.txt"
        assert result["name"] == "Test File"
        assert result["description"] == "A test file"
        assert result["mimeType"] == "text/plain"


class TestMCPResourceContent:
    """Tests for MCPResourceContent dataclass."""

    def test_resource_content_creation(self) -> None:
        """Test MCPResourceContent creation."""
        content = MCPResourceContent(uri="file://test.txt", text="Hello")

        assert content.uri == "file://test.txt"
        assert content.text == "Hello"
        assert content.blob is None

    def test_resource_content_to_dict(self) -> None:
        """Test MCPResourceContent serialization."""
        content = MCPResourceContent(uri="file://test.txt", text="Hello")
        result = content.to_dict()

        assert result["uri"] == "file://test.txt"
        assert result["text"] == "Hello"
        assert "blob" not in result


class TestMCPPrompt:
    """Tests for MCPPrompt dataclass."""

    def test_prompt_creation(self) -> None:
        """Test MCPPrompt creation."""
        prompt = MCPPrompt(name="test_prompt", description="A test prompt")

        assert prompt.name == "test_prompt"
        assert prompt.description == "A test prompt"
        assert prompt.arguments == []

    def test_prompt_to_dict(self) -> None:
        """Test MCPPrompt serialization."""
        prompt = MCPPrompt(
            name="test_prompt",
            description="A test prompt",
            arguments=[{"name": "arg1", "required": True}],
        )
        result = prompt.to_dict()

        assert result["name"] == "test_prompt"
        assert result["arguments"][0]["name"] == "arg1"


class TestMCPServerCapabilities:
    """Tests for MCPServerCapabilities dataclass."""

    def test_capabilities_creation(self) -> None:
        """Test MCPServerCapabilities creation."""
        caps = MCPServerCapabilities(tools=True, resources=True)

        assert caps.tools is True
        assert caps.resources is True
        assert caps.prompts is False

    def test_capabilities_to_dict(self) -> None:
        """Test MCPServerCapabilities serialization."""
        caps = MCPServerCapabilities(tools=True, prompts=True)
        result = caps.to_dict()

        assert "tools" in result
        assert "prompts" in result
        assert "resources" not in result


class TestMCPServerInfo:
    """Tests for MCPServerInfo dataclass."""

    def test_server_info_creation(self) -> None:
        """Test MCPServerInfo creation."""
        info = MCPServerInfo(name="test-server", version="1.0.0")

        assert info.name == "test-server"
        assert info.version == "1.0.0"

    def test_server_info_default(self) -> None:
        """Test MCPServerInfo default values."""
        info = MCPServerInfo()

        assert info.name == "lexigram-mcp"
        assert info.version == "1.0.0"

    def test_server_info_to_dict(self) -> None:
        """Test MCPServerInfo serialization."""
        info = MCPServerInfo(name="test-server", version="2.0.0")
        result = info.to_dict()

        assert result["name"] == "test-server"
        assert result["version"] == "2.0.0"


class TestMCPInitializeResult:
    """Tests for MCPInitializeResult dataclass."""

    def test_initialize_result_creation(self) -> None:
        """Test MCPInitializeResult creation."""
        result = MCPInitializeResult()

        assert result.protocol_version == "2024-11-05"
        assert isinstance(result.capabilities, MCPServerCapabilities)
        assert isinstance(result.server_info, MCPServerInfo)

    def test_initialize_result_to_dict(self) -> None:
        """Test MCPInitializeResult serialization."""
        result = MCPInitializeResult()
        output = result.to_dict()

        assert "protocolVersion" in output
        assert "capabilities" in output
        assert "serverInfo" in output


class TestMCPJSONRPCRequest:
    """Tests for MCPJSONRPCRequest dataclass."""

    def test_jsonrpc_request_creation(self) -> None:
        """Test MCPJSONRPCRequest creation."""
        req = MCPJSONRPCRequest(id=1, method="testMethod", params={"key": "value"})

        assert req.jsonrpc == "2.0"
        assert req.id == 1
        assert req.method == "testMethod"
        assert req.params == {"key": "value"}

    def test_jsonrpc_request_to_dict(self) -> None:
        """Test MCPJSONRPCRequest serialization."""
        req = MCPJSONRPCRequest(id=1, method="testMethod")
        result = req.to_dict()

        assert result["jsonrpc"] == "2.0"
        assert result["id"] == 1
        assert result["method"] == "testMethod"


class TestMCPJSONRPCResponse:
    """Tests for MCPJSONRPCResponse dataclass."""

    def test_jsonrpc_response_creation(self) -> None:
        """Test MCPJSONRPCResponse creation."""
        resp = MCPJSONRPCResponse(id=1, result={"data": "test"})

        assert resp.jsonrpc == "2.0"
        assert resp.id == 1
        assert resp.result == {"data": "test"}
        assert resp.error is None

    def test_jsonrpc_response_success_factory(self) -> None:
        """Test MCPJSONRPCResponse.success factory."""
        resp = MCPJSONRPCResponse.create_success({"status": "ok"}, request_id=42)

        assert resp.result == {"status": "ok"}
        assert resp.id == 42
        assert resp.error is None

    def test_jsonrpc_response_error_factory(self) -> None:
        """Test MCPJSONRPCResponse.error factory."""
        resp = MCPJSONRPCResponse.create_error(-32600, "Invalid request", request_id=1)

        assert resp.error is not None
        assert resp.error["code"] == -32600
        assert resp.error["message"] == "Invalid request"
        assert resp.id == 1

    def test_jsonrpc_response_to_dict(self) -> None:
        """Test MCPJSONRPCResponse serialization."""
        resp = MCPJSONRPCResponse.success({"status": "ok"})
        result = resp.to_dict()

        assert result["jsonrpc"] == "2.0"
        assert result["result"]["status"] == "ok"


class TestMCPTypesExports:
    """Tests for MCP types module exports."""

    def test_all_exports(self) -> None:
        """Test that all types are properly exported."""
        from lexigram.ai.mcp import types

        expected = [
            "MCPInitializeResult",
            "MCPJSONRPCRequest",
            "MCPJSONRPCResponse",
            "MCPPrompt",
            "MCPPromptMessage",
            "MCPResource",
            "MCPResourceContent",
            "MCPServerCapabilities",
            "MCPServerInfo",
            "MCPToolDefinition",
            "MCPToolResult",
        ]
        for name in expected:
            assert hasattr(types, name)