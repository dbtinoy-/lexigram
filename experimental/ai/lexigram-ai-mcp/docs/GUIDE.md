---
title: lexigram-ai-mcp Guide
description: Mental model, core concepts, and typical usage of Lexigram's MCP integration
---

## Requirements

| Package | Required | Purpose |
|---------|----------|---------|
| `lexigram` | Yes | Core framework |
| `lexigram-contracts` | Yes | Protocol definitions |
| `lexigram-ai-agents` | Optional | Agent system bridging |
| `lexigram-ai-skills` | Optional | Skills-to-MCP bridging |

MCP servers let AI agents — like Claude Desktop or custom LLM applications — interact with your application through **tools**, **resources**, and **prompts**.

The package wraps the [Model Context Protocol](https://modelcontextprotocol.io) as a first-class Lexigram citizen: handlers, transports, and connectors are wired through the DI container with the same provider/module lifecycle as any other extension.

## Core Concepts

### Server vs Client

| Role | Class | Purpose |
|------|-------|---------|
| **Server** | `MCPServer` | Exposes tools/resources/prompts to AI clients. JSON-RPC message router. |
| **Client** | `MCPClient` | Connects to external MCP servers (stdio or SSE) and calls their tools. |

### Tools, Resources, Prompts

An MCP server exposes three capability types:

- **Tools** — callable functions the AI can invoke (`tools/list`, `tools/call`).
- **Resources** — data the AI can read (`resources/list`, `resources/read`).
- **Prompts** — template-driven messages (`prompts/list`, `prompts/get`).

### Handlers

Handlers implement the routing for each capability:

| Handler | Registers | Dispatches to |
|---------|-----------|---------------|
| `ToolHandler` | `@tool`-decorated methods, `MCPController` subclasses, connectors | `MCPToolProviderProtocol` |
| `ResourceHandler` | `@resource`-decorated methods, connectors | `MCPResourceProviderProtocol` |
| `PromptHandler` | `@prompt`-decorated methods | `MCPPromptProviderProtocol` |

### Transports

| Transport | Direction | I/O |
|-----------|-----------|-----|
| `StdioTransport` | Server-side | stdin/stdout (local desktop tools) |
| `SSETransport` | Server-side | HTTP + Server-Sent Events |
| `StdioClientTransport` | Client-side | stdin/stdout subprocess |
| `SSEClientTransport` | Client-side | HTTP POST + SSE |

## Typical Usage

### Exposing Tools via MCPController

```python
from lexigram.ai.mcp import MCPController, tool, MCPModule
from lexigram.contracts.data.vector.protocols import VectorStoreProtocol


class SearchController(MCPController):
    def __init__(self, vector_store: VectorStoreProtocol) -> None:
        self._store = vector_store

    @tool("search_docs", description="Search documents by query")
    async def search_docs(self, query: str, limit: int = 10) -> list[dict]:
        result = await self._store.similarity_search(query, k=limit)
        return result.unwrap_or([])


# Wiring
module = MCPModule.configure(controllers=[SearchController])
```

### Auto-Exposing Existing Services

```python
module = MCPModule.from_services(
    services=[UserService, AnalyticsService],
    include_methods=["search", "get_*"],
)
```

Service methods matching the glob are registered as MCP tools automatically.

### Connecting to External MCP Servers (Client)

```python
from lexigram.ai.mcp.client import MCPClientModule, MCPConnection


module = MCPClientModule.configure(
    connections=[
        MCPConnection.stdio(["uvx", "mcp-server-git"], name="git"),
        MCPConnection.sse("http://localhost:9000/mcp", name="local"),
    ],
)
```

Inject `MCPClientRegistry` for named access or `MCPClient` for the primary connection.

## Common Patterns

### Exposing Connectors Conditionally

```yaml
ai_mcp:
  connectors:
    filesystem:
      root_dir: "/workspace"        # enables FilesystemConnector
      read_only: true
    web_fetch:
      enabled: true
    github:
      token: "${GITHUB_TOKEN}"      # enables GitHubConnector
```

Connectors are enabled by supplying the required config keys — absent keys disable the connector.

### Custom Tool Provider

```python
from lexigram.contracts.mcp.protocols import MCPToolProviderProtocol


class MyToolProvider:
    async def list_tools(self) -> list[dict[str, Any]]:
        return [{"name": "hello", "description": "Say hello", "inputSchema": {}}]

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return {"content": [{"type": "text", "text": "Hello!"}]}
```

Register it in a custom provider's `boot()` against `MCPToolProviderProtocol`.

### Bridge to lexigram-ai-skills

When `lexigram-ai-skills` is installed and its provider is registered, `SkillToolAdapter` is automatically created — all skills become MCP tools.

## Best Practices

- ✅ Use `MCPModule.from_services()` for quick prototyping, `MCPController` for production.
- ✅ Set `read_only: true` on connectors that should never mutate state.
- ✅ Set `enable_streaming: False` in tests to simplify assertions.
- ❌ Don't import `MCPServer` from the server module directly — resolve it from the container.
- ❌ Don't expose database write connectors (`sql.read_only: false`) to untrusted AI clients.

## Next Steps

- [How-Tos](./HOWTOS.md) — specific task recipes
- [Configuration](./CONFIGURATION.md) — every config key
- [Architecture](./ARCHITECTURE.md) — internal design and extension points
