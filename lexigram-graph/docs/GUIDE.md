---
title: lexigram-graph Guide
description: Mental model, core concepts, and common patterns for graph database access.
---

## Requirements

| Package | Required | Purpose |
|---------|----------|---------|
| `lexigram` | Yes | Core framework |
| `lexigram-contracts` | Yes | Protocol definitions |
| `neo4j` | Recommended | Neo4j graph backend |

## Problem

Your application models data as **nodes** (entities) connected by **edges** (relationships) — social graphs, knowledge graphs, recommendation engines, or hierarchical org charts. You need to query paths, traverse neighborhoods, and run graph algorithms without coupling to a specific backend.

## Mental Model

`lexigram-graph` provides a **graph-oriented** abstraction with two layers:

- **`GraphStoreProtocol`** — connection lifecycle and graph-database management (create/list/delete graphs).
- **`GraphProtocol`** — all operations on a single graph: node CRUD, edge CRUD, traversal, raw queries, bulk ops, and schema management.

All operations are async. Nodes and edges carry string-keyed `Properties` dicts. Traversal results are `GraphPath` objects containing nodes and edges.

---

## Core Concepts

### Graph Store

`GraphStoreProtocol` is the top-level handle:

```python
from lexigram.contracts.data.graph import GraphStoreProtocol


store = await container.resolve(GraphStoreProtocol)
await store.connect()

# Get the default graph
graph = await store.get_graph()

# Or create a named graph
await store.create_graph("recommendations")
rec_graph = await store.get_graph("recommendations")
```

### Graph Operations

`GraphProtocol` provides the full surface area:

| Category | Methods |
|----------|---------|
| **Nodes** | `create_node`, `get_node`, `find_nodes`, `update_node`, `delete_node`, `neighbors`, `count_nodes`, `get_labels` |
| **Edges** | `create_edge`, `get_edge`, `get_edges`, `update_edge`, `delete_edge`, `count_edges`, `get_edge_types` |
| **Traversal** | `traverse`, `shortest_path` |
| **Raw Query** | `query` (pass-through Cypher or backend-native) |
| **Bulk** | `bulk_create_nodes`, `bulk_create_edges` |
| **Schema** | `create_index`, `drop_index`, `create_constraint`, `drop_constraint` |

### Backends

| Backend | Identifier | Use Case |
|---------|-----------|----------|
| **In-memory** | `"memory"` | Development, testing, single-node apps |
| **Neo4j** | `"neo4j"` | Production graph workloads |

---

## Typical Usage

### Create and Query a Social Graph

```python
from lexigram.contracts.data.graph import GraphStoreProtocol, GraphProtocol


class SocialGraphService:
    def __init__(self, graph: GraphProtocol) -> None:
        self.graph = graph

    async def add_user(self, user_id: str, name: str) -> None:
        await self.graph.create_node(
            ["User"],
            {"user_id": user_id, "name": name},
            node_id=user_id,
        )

    async def follow(self, follower: str, followee: str) -> None:
        await self.graph.create_edge(
            follower, followee, "FOLLOWS",
            {"since": clock.now().isoformat()},
        )

    async def get_followers(self, user_id: str) -> list[GraphNode]:
        return await self.graph.neighbors(
            user_id, depth=1, direction="INCOMING", edge_types=["FOLLOWS"],
        )

    async def shortest_connection(
        self, user_a: str, user_b: str,
    ) -> GraphPath | None:
        return await self.graph.shortest_path(user_a, user_b, max_depth=5)
```

### Traversal with Filters

```python
# Find nodes with specific labels and property filters
from lexigram.contracts.data.graph import PropertyFilter

results = await graph.find_nodes(
    labels=["Product"],
    filter=PropertyFilter(
        conditions={"category": "electronics", "price": {"$lt": 100}},
    ),
    limit=50,
)
```

---

## Common Patterns

### Multi-Graph Applications

Create separate graph databases for different domains:

```python
# On boot
store = await container.resolve(GraphStoreProtocol)
await store.create_graph("users")
await store.create_graph("content")
await store.create_graph("analytics")

# In services
class ContentGraphService:
    def __init__(self, store: GraphStoreProtocol) -> None:
        self.graph = await store.get_graph("content")
```

### Bulk Import

```python
from lexigram.contracts.data.graph import NodeSpec


nodes = [
    NodeSpec(labels=["Movie"], properties={"title": "Inception", "year": 2010}),
    NodeSpec(labels=["Movie"], properties={"title": "The Matrix", "year": 1999}),
    NodeSpec(labels=["Actor"], properties={"name": "Keanu Reeves"}),
]
result = await graph.bulk_create_nodes(nodes)
print(f"Created {result.count} nodes")
```

### Schema Management

```python
from lexigram.contracts.data.graph import IndexSpec, ConstraintSpec


# Create a unique constraint (Neo4j)
await graph.create_constraint(
    ConstraintSpec(label="User", property="email", type="unique")
)

# Create an index
await graph.create_index(
    IndexSpec(label="Product", properties=["category", "price"])
)
```

### Raw Cypher Queries

```python
# Passthrough for backend-specific queries
results = await graph.query(
    "MATCH (u:User)-[:FOLLOWS]->(f:User) "
    "WHERE u.name = $name "
    "RETURN f.name AS friend",
    parameters={"name": "Alice"},
)
for row in results:
    print(row["friend"])
```

---

## Best Practices

- ✅ Use the in-memory backend for tests and local dev — it's fast and stateless.
- ✅ Set `backend: neo4j` in production and configure `neo4j.password` via secrets or env vars.
- ✅ Name graph databases semantically (`users`, `content`, `analytics`) rather than by host.
- ❌ Don't mix graph paradigms — use a single graph per domain, not one giant graph.
- ❌ Don't use `traverse()` for simple neighbor lookups — use `neighbors()` instead (it's optimised).

## Next Steps

- [How-Tos](./HOWTOS.md) — task-oriented recipes
- [Architecture](./ARCHITECTURE.md) — internal design and extension points
- [Configuration](./CONFIGURATION.md) — every config key
