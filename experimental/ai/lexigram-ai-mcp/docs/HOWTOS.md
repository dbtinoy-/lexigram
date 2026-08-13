---
title: lexigram-ai-mcp How-Tos
description: Task-oriented recipes for common MCP operations
---

## Define a Tool with Validation

```python
from lexigram.ai.mcp import MCPController, tool


class CalculatorController(MCPController):
    @tool("add", description="Add two numbers")
    async def add(self, a: float, b: float) -> dict:
        return {"result": a + b}

    @tool("divide", description="Divide two numbers")
    async def divide(self, a: float, b: float) -> dict:
        if b == 0:
            return {"error": "Division by zero"}
        return {"result": a / b}
```

## Expose a Resource

```python
from lexigram.ai.mcp import MCPController, resource


class ConfigController(MCPController):
    def __init__(self, config: AppConfig) -> None:
        self._config = config

    @resource("config://app", description="Application configuration")
    async def get_config(self) -> dict:
        return {"name": self._config.name, "version": self._config.version}
```

## Expose a Prompt Template

```python
from lexigram.ai.mcp import MCPController, prompt


class SummarizeController(MCPController):
    @prompt("summarize", description="Generate a summarization prompt")
    async def summarize_prompt(self, text: str) -> dict:
        return {
            "messages": [
                {"role": "system", "content": "Summarize the following text concisely."},
                {"role": "user", "content": text},
            ],
        }
```

## Connect to an External MCP Server via stdio

```python
from lexigram.ai.mcp.client import MCPClient, StdioClientTransport


transport = StdioClientTransport(
    ["uvx", "mcp-server-git", "--repository", "/repo"],
    startup_timeout=10.0,
)
async with MCPClient(transport, request_timeout=30.0) as client:
    tools = await client.list_tools()
    result = await client.call_tool("git_log", {"max_count": 5})
```

## Connect to an External MCP Server via SSE

```python
from lexigram.ai.mcp.client import MCPClient, SSEClientTransport


transport = SSEClientTransport("http://localhost:8080/mcp")
async with MCPClient(transport) as client:
    tools = await client.list_tools()
```

## Use Named MCP Client Connections

```python
from lexigram.ai.mcp.client import MCPClientModule, MCPConnection, MCPClientRegistry


app.add_module(
    MCPClientModule.configure(
        connections=[
            MCPConnection.stdio(["uvx", "mcp-server-git"], name="git"),
            MCPConnection.sse("http://analytics:9000/mcp", name="analytics"),
        ],
    ),
)


class ReportService:
    def __init__(self, registry: MCPClientRegistry) -> None:
        self._git = registry.get("git")
        self._analytics = registry.get("analytics")
```

## Register a Custom Connector

Implement `MCPToolProviderProtocol` (or `MCPResourceProviderProtocol`) and register it during a custom provider's boot:

```python
from lexigram.contracts.mcp.protocols import MCPToolProviderProtocol


class WeatherConnector:
    async def list_tools(self) -> list[dict[str, Any]]:
        return [{"name": "get_weather", "description": "Get weather", "inputSchema": {}}]

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return {"content": [{"type": "text", "text": "Sunny, 72°F"}]}
```

## Bridge Skills to MCP Tools

Install `lexigram-ai-skills` alongside `lexigram-ai-mcp`. The `MCPProvider` automatically detects `SkillRegistryProtocol` and `SkillExecutorProtocol` in the container and registers `SkillToolAdapter` — no extra wiring needed.

## Auto-Expose Existing Services as MCP Tools

Use `MCPModule.from_services()` to automatically register service methods as MCP tools by name pattern:

```python
from lexigram.ai.mcp import MCPModule, MCPConfig


class UserService:
    async def search(self, query: str, limit: int = 10) -> list[dict]:
        ...

    async def get_profile(self, user_id: str) -> dict:
        ...

    async def delete_account(self, user_id: str) -> None:
        ...


module = MCPModule.from_services(
    services=[UserService],
    include_methods=["search", "get_*"],  # glob pattern; excludes delete_account
    config=MCPConfig(server_name="user-service"),
)
```

## Bridge Agent Tools to MCP via ToolRegistryAdapter

Connect an existing lexigram-agents `ToolRegistryProtocol` to MCP:

```python
from lexigram.ai.mcp import ToolRegistryAdapter
from lexigram.contracts.ai.agents import ToolRegistryProtocol


registry: ToolRegistryProtocol
adapter = ToolRegistryAdapter(tool_registry=registry)

# Use the adapter as an MCPToolProviderProtocol implementation
tools = await adapter.list_tools()
result = await adapter.call_tool("my_tool", {"arg": "value"})
```

## Handle MCP Protocol Errors

Catch specific errors from MCP client operations:

```python
from lexigram.ai.mcp import (
    MCPClient,
    StdioClientTransport,
    MCPError,
    MCPTransportError,
    MCPToolCallError,
    MCPInitializationError,
)

transport = StdioClientTransport(["uvx", "mcp-server-git"], startup_timeout=10.0)
try:
    async with MCPClient(transport) as client:
        result = await client.call_tool("git_log", {"max_count": 5})
except MCPInitializationError as e:
    print(f"Handshake failed: {e}")
except MCPTransportError as e:
    print(f"Transport error: {e}")
except MCPToolCallError as e:
    print(f"Tool execution failed: {e}")
except MCPError as e:
    print(f"Generic MCP error: {e}")
```

## Test Without a Transport

```python
module = MCPModule.stub()  # enable_streaming=False, safe for tests
```
