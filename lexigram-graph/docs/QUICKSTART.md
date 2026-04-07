---
title: lexigram-graph Quickstart
description: Get up and running with graph database support in minutes.
---

:::tip[Package]
`lexigram-graph` — Graph database support for the Lexigram Framework (Neo4j, in-memory).
:::

## Install

```bash
uv add lexigram-graph
```

Add the optional Neo4j extra for production use:

```bash
uv add "lexigram-graph[neo4j]"
```

The in-memory backend requires no extra dependencies.

---

## Minimal Example

```python
import asyncio
from lexigram import Application
from lexigram.contracts.data.graph import GraphStoreProtocol
from lexigram.graph import GraphModule, GraphConfig


async def main() -> None:
    async with Application.boot(
        name="graph-demo",
        modules=[
            GraphModule.configure(
                GraphConfig(backend="memory")
            ),
        ],
    ) as app:
        graph = await app.container.resolve(GraphStoreProtocol)
        db = await graph.get_graph()
        node = await db.create_node(["Person"], {"name": "Alice"})
        print(f"Created node: {node.id}")


asyncio.run(main())
```

For Neo4j:

```bash
uv add "lexigram-graph[neo4j]"
```

```python
config = GraphConfig(backend="neo4j")
```

---

## How It Works

1. **`GraphModule.configure()`** creates a `GraphProvider` with the given config.
2. The provider registers `GraphStoreProtocol` and `GraphProtocol` in the container.
3. On boot, it connects to the configured backend (in-memory or Neo4j).
4. Services receive graph handles via constructor injection.

## Next Steps

- [Guide](./GUIDE.md) — mental model, core concepts, common patterns
- [How-Tos](./HOWTOS.md) — task-oriented recipes
- [Configuration](./CONFIGURATION.md) — every config key with env-var names
