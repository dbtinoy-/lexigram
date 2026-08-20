---
title: "Model Context Protocol (MCP)"
description: "Expose tools, resources, and prompts through the MCP protocol — server and client."
---

`lexigram-ai-mcp` provides an MCP (Model Context Protocol) server and client built on JSON-RPC 2.0. The server exposes tools, resources, and prompts to AI clients over SSE or stdio transport. The client connects to external MCP servers and injects them as DI-resolvable services.

For the full configuration reference and advanced features (connector config, MCP controller patterns), see the [`lexigram-ai-mcp` package docs](/packages/lexigram-ai-mcp/).

---

## 1. Server Configuration

Add the module and configure the `ai_mcp:` section:

```python
from lexigram.ai.mcp import MCPModule

app.add_module(
    MCPModule.configure(
        controllers=[DataToolsController],
        enable_streaming=True,
    )
)
```

```yaml title="application.yaml"
ai_mcp:
  enabled: true
  host: "0.0.0.0"
  port: 8080
  path: "/mcp"
  enable_sse: true
  stdio_mode: false
  server_name: "my-app-mcp"
  server_version: "1.0.0"
  cors_origins:
    - "http://localhost:5173"
  max_request_size: 1048576   # 1 MB
  request_timeout: 30.0
```

:::note
`MCPConfig` is read from the `ai_mcp:` block automatically. Pass a config instance directly to `MCPModule.configure(config=MCPConfig(...))` for programmatic setup.
:::

### Connectors

The `connectors` block enables built-in tool connectors:

```yaml title="application.yaml"
ai_mcp:
  connectors:
    filesystem:
      root_dir: "/data/sandbox"
      read_only: true
    github:
      token: "${GITHUB_TOKEN}"
    web_fetch:
      enabled: true
      max_content_bytes: 524288
    web_search:
      provider: "brave"
      api_key: "${BRAVE_API_KEY}"
      max_results: 10
    slack:
      bot_token: "${SLACK_BOT_TOKEN}"
    google_drive:
      service_account_json: "/secrets/gdrive-sa.json"
    sql:
      dsn: "${DB_DSN}"
      allowed_tables: ["users", "products"]
      read_only: true
```

---

## 2. Exposing Tools — Three Modes

### Controller-based (decorator + class)

Create an `MCPController` subclass and decorate methods:

```python
from lexigram.ai.mcp import MCPController, tool, resource, prompt


class DataToolsController(MCPController):
    def __init__(self, repo: ProductRepository) -> None:
        self._repo = repo

    @tool("get_product", description="Fetch a product by ID")
    async def get_product(self, product_id: str) -> dict:
        result = await self._repo.find(product_id)
        return result.unwrap_or({})

    @resource("products://{product_id}", name="Product Resource")
    async def product_resource(self, product_id: str) -> str:
        result = await self._repo.find(product_id)
        return str(result.unwrap_or({}))

    @prompt("product_help", description="Template for product queries")
    async def product_prompt(self) -> list[dict]:
        return [{"role": "system", "content": "You are a product assistant."}]
```

Register via `controllers=`:

```python
MCPModule.configure(controllers=[DataToolsController])
```

### Service-based (auto-expose)

Expose existing service methods without writing a controller:

```python
MCPModule.from_services(
    services=[UserService, AnalyticsService],
    include_methods=["search", "get_*"],
)
```

Glob patterns in `include_methods` control which public methods become MCP tools.

### Module-based (decorated functions)

Decorate standalone functions in any module:

```python
from lexigram.ai.mcp import tool


@tool("current_time", description="Get the current server time")
async def current_time(timezone: str = "UTC") -> dict:
    ...
```

---

## 3. MCP Server Host

The `MCPServer` (resolved from the container) handles MCP JSON-RPC methods over SSE transport at `/mcp/sse` and receives messages via POST at `/mcp/messages`:

```python
from lexigram.ai.mcp import MCPServer


async with app.boot() as container:
    server: MCPServer = await container.resolve(MCPServer)
    # Mount on your ASGI app:
    app.mount("/mcp", server)
```

The JSON-RPC methods handled automatically:

| Method | Purpose |
|---|---|
| `initialize` | Protocol handshake |
| `tools/list` | List exposed tools |
| `tools/call` | Invoke a tool |
| `resources/list` | List available resources |
| `resources/read` | Read a resource by URI |
| `prompts/list` | List prompt templates |
| `prompts/get` | Get a specific prompt |

---

## 4. MCP Client

Connect to external MCP servers and call their tools via DI-injected clients:

```python
from lexigram.ai.mcp import MCPClientModule, MCPConnection


app.add_module(
    MCPClientModule.configure(
        connections=[
            MCPConnection.stdio(
                ["uvx", "mcp-server-git", "--repository", "/repo"],
                name="git",
            ),
            MCPConnection.sse(
                "http://analytics.internal/mcp",
                name="analytics",
                headers={"Authorization": "Bearer ${TOKEN}"},
            ),
        ]
    )
)
```

Inject `MCPClientRegistry` for multi-connection access:

```python
from lexigram.ai.mcp import MCPClientRegistry, MCPClient


class ReportService:
    def __init__(self, registry: MCPClientRegistry) -> None:
        self._git = registry.get("git")
        self._analytics = registry.get("analytics")

    async def generate_report(self) -> dict:
        tools = await self._git.list_tools()
        result = await self._analytics.call_tool("query", {"sql": "..."})
        return {"tools": tools, "result": result}
```

The first connection is also registered directly as `MCPClient` for single-connection use:

```python
class SimpleService:
    def __init__(self, mcp: MCPClient) -> None:
        self._mcp = mcp

    async def get_data(self, query: str) -> dict:
        return await self._mcp.call_tool("search", {"q": query})
```

:::tip
Use `MCPClient` as an async context manager for automatic lifecycle:

```python
async with MCPClient(transport) as client:
    tools = await client.list_tools()
```
:::

---

## 5. Testing

Use `MCPModule.stub()` for unit tests — it uses in-memory transport with streaming disabled:

```python
from lexigram import Application
from lexigram.ai.mcp import MCPModule, MCPServer


async def test_server_resolves() -> None:
    async with Application.boot(modules=[MCPModule.stub()]) as app:
        server = await app.container.resolve(MCPServer)
        assert server is not None
```

For client tests, construct `MCPClient` with a test transport directly.

---

## 6. Advanced Wiring

Wire optional `llm_client` (LLMClientProtocol) and `skill_registry` (SkillRegistryProtocol) via provider kwargs to enable sampling and skill-tool integration:

```python
MCPModule.configure(
    controllers=[...],
    provider_kwargs={
        "llm_client": my_llm_client,
        "skill_registry": my_skill_registry,
    },
)
```

---

## Next Steps

- [Dependency Injection](/fundamentals/dependency-injection/) — binding protocols to implementations
- [Providers](/fundamentals/providers/) — how `MCPProvider` hooks into application boot
- [Testing](/guides/testing/) — substituting stubs for infrastructure
- [Real-Time & WebSockets](/guides/real-time/) — SSE transport details
- [`lexigram-ai-mcp` package](/packages/lexigram-ai-mcp/) — connector config, controller patterns
