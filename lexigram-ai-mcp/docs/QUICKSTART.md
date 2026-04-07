---
title: lexigram-ai-mcp Quickstart
description: Get an MCP server running in under 5 minutes
---

:::note[Maturity]
Alpha (0.1.x) — MIT. Public APIs may change before 1.0.
:::

## Install

```bash
uv add lexigram-ai-mcp
```

`lexigram-ai-mcp` depends on `lexigram` and `lexigram-contracts` (installed automatically).

## Minimal MCP Server

```python
import asyncio

from lexigram import Application, LexigramConfig
from lexigram.ai.mcp import MCPModule


async def main() -> None:
    config = LexigramConfig.from_yaml("application.yaml")
    app = Application(name="my-mcp-app", config=config)
    app.add_module(MCPModule.configure())
    await app.start()

    # MCPServer is now wired and ready
    print("MCP server is running")

    await app.stop()


asyncio.run(main())
```

With `application.yaml`:

```yaml
ai_mcp:
  host: "0.0.0.0"
  port: 8080
  path: "/mcp"
```

## What Just Happened

1. `MCPModule.configure()` creates a `DynamicModule` with an `MCPProvider`.
2. `Application.boot()` starts the provider lifecycle:
   - **register** — `MCPConfig` is bound in the container.
   - **boot** — handlers, connectors, transports, and the `MCPServer` are wired.
3. The server listens for JSON-RPC messages over HTTP+SSE or stdio.

## Next Steps

- [Guide](./GUIDE.md) — mental model, tools/resources/prompts, client usage
- [How-Tos](./HOWTOS.md) — task-oriented recipes
- [Configuration](./CONFIGURATION.md) — all config keys and env-var overrides
