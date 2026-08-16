---
title: lexigram-graph Backends
description: Compare Neo4j and in-memory backends for lexigram-graph
sidebar:
  order: 3
---

`lexigram-graph` provides graph store backends behind the `GraphStoreProtocol` contract from `lexigram-contracts`. Both backends support the same graph, node, edge, and traversal APIs, including Cypher query compilation for Neo4j.

## Supported Backends

| Backend | Extra | Driver | Production-ready | Best for |
|---------|-------|--------|-----------------|----------|
| Neo4j | `lexigram-graph[neo4j]` | `neo4j>=5.20.0` | Yes | Production graph workloads |
| Memory | (core) | in-process `dict`/`set` | Development / test | Local dev, unit tests, demos |

Install the Neo4j extra: `pip install lexigram-graph[neo4j]`.

## Backend Details

### Neo4j

Production-grade graph database backed by the official `neo4j` async Python driver.

- **Strengths:** ACID transactions, Cypher query language, property graph model, indexing, and traversal performance at scale. The `CypherCompiler` translates `TraversalQuery` objects to parameterized Cypher strings with full support for property filters, edge direction, limit, skip, and path uniqueness. Connection pooling, TLS, transaction retry, and configurable fetch size are all supported via `Neo4jConfig`.
- **Weaknesses:** Requires a running Neo4j server (or AuraDB). Heavier operational footprint than in-memory.
- **When to choose:** Knowledge graphs, recommendation engines, fraud detection, network analysis, or any workload that benefits from graph traversal and relationship-heavy queries.

Config fields map to the `Neo4jConfig` model:

```yaml
graph:
  backend: neo4j
  neo4j:
    uri: bolt://localhost:7687
    username: neo4j
    password: ${NEO4J_PASSWORD}
    database: neo4j
    max_connection_pool_size: 50
    encrypted: false
```

:::caution
In production, set `encrypted: true` and provide a valid `password`. The default password is empty — `GraphConfig.validate_for_environment()` rejects Neo4j in production without a password.
:::

### Memory

In-process graph store backed by Python `dict` and `set` collections.

- **Strengths:** Zero external dependencies, instant setup, no server process. Supports all the same operations as Neo4j (traversal, node/edge CRUD, property queries) but in-memory only.
- **Weaknesses:** Data is process-local — lost on restart and invisible to other processes. No indexing, no transactions, no query optimization. Performance degrades with large graphs.
- **When to choose:** Unit tests, CI pipelines, local development, demos, or when the graph is small and ephemeral.

```yaml
graph:
  backend: memory
  memory:
    max_nodes: 100000
    max_edges: 500000
```

`GraphConfig.validate_for_environment()` blocks `backend: memory` in production with an error-level `ConfigIssue`.

## Quick Selection Guide

- **I'm deploying to production** → `neo4j`. Add the `[neo4j]` extra.
- **I'm writing unit tests** → `memory`. No extra needed.
- **I need Cypher queries** → `neo4j`. Memory backend does not support Cypher.
- **I need a demo or prototype** → `memory`. Start with memory, switch to Neo4j for production.

## Multi-Backend Configuration

The current `GraphProvider` supports a single backend selected by `GraphConfig.backend`. There is no `backends` list or Named injection — the `backend` field accepts either `neo4j` or `memory`.

```yaml
graph:
  enabled: true
  backend: neo4j          # or "memory"
  default_traversal_max_depth: 5
  default_query_limit: 100
```

## Cypher Support

The `CypherCompiler` in `lexigram.graph.backends.neo4j.cypher` compiles `TraversalQuery` objects to parameterized Cypher strings. It supports:

- **Property filters:** `EQ`, `NE`, `GT`, `GTE`, `LT`, `LTE`
- **Property groups:** AND/OR groups for compound filters
- **Edge direction:** `OUTGOING`, `INCOMING`, `BOTH`
- **Return types:** `NODES`, `EDGES`, `PATHS`, `COUNT`
- **Limit, skip, and path uniqueness**

## Testing

Use the memory backend for tests — no server needed:

```python
from lexigram.graph import GraphConfig, GraphProvider
from lexigram.graph.constants import BACKEND_MEMORY

config = GraphConfig(backend=BACKEND_MEMORY)
provider = GraphProvider(config=config)

# GraphStoreProtocol resolves to InMemoryGraphStore
```

Or configure via YAML:

```yaml
graph:
  enabled: true
  backend: memory
```
