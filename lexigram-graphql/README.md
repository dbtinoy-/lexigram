# lexigram-graphql

GraphQL support for Lexigram Framework — Strawberry, Apollo Federation, and subscriptions.

---

## Overview

`lexigram-graphql` provides a complete GraphQL layer built on Strawberry, with field-level permissions, DataLoaderProtocol batching for N+1 query elimination, WebSocket subscriptions, depth/complexity limiting, persisted queries, and automatic playground disable in production. All services are wired through Lexigram's DI container.

---


> Full documentation: [docs.lexigram.dev](https://docs.lexigram.dev)
## Install

```bash
uv add lexigram lexigram-web lexigram-graphql
# Optional extras
uv add "lexigram-graphql[starlette]"   # Starlette integration
uv add "lexigram-graphql[subscriptions]"  # WebSocket subscriptions
```

## Quick Start

```python
from lexigram import Application
from lexigram.di.module import Module, module
from lexigram.graphql import GraphQLModule
from lexigram.web import WebModule

import strawberry


@strawberry.type
class Query:
    @strawberry.field
    def hello(self) -> str:
        return "world"


@module(
    imports=[
        WebModule.configure(host="127.0.0.1", port=8000),
        GraphQLModule.configure(query_class=Query),
    ]
)
class AppModule(Module):
    pass


async def main() -> None:
    async with Application.boot(modules=[AppModule]) as app:
        web = await app.container.resolve(WebProvider)
        web.run_server(host="127.0.0.1", port=8000)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

GraphQL endpoint: `http://127.0.0.1:8000/graphql`
Playground: `http://127.0.0.1:8000/graphql/playground` (development only)

## Configuration

> **Zero-config usage:** Call `GraphQLModule.configure()` with no arguments to use all defaults.

### Option 1 — YAML file

```yaml
# application.yaml
graphql:
  server:
    path: "/graphql"
    debug: false
  playground:
    enabled: true
  schema:
    max_depth: 10
    complexity_limit: 1000
```

### Option 2 — Profiles + Environment Variables *(recommended)*

```bash
export LEX_GRAPHQL__PATH=/api/graphql
export LEX_GRAPHQL__DEBUG=true
export LEX_GRAPHQL__DEPTH_LIMIT__MAX_DEPTH=8
```

### Option 3 — Python

```python
from lexigram.graphql import GraphQLModule
from lexigram.graphql.config import GraphQLConfig

config = GraphQLConfig.development()
GraphQLModule.configure(config=config, query_class=Query)
```

### Config reference

| Field | Default | Env var | Description |
|-------|---------|---------|-------------|
| `path` | `"/graphql"` | `LEX_GRAPHQL__PATH` | GraphQL HTTP endpoint |
| `debug` | `false` | `LEX_GRAPHQL__DEBUG` | Propagates to `errors.debug_mode` |
| `introspection.enabled` | `true` | `LEX_GRAPHQL__INTROSPECTION__ENABLED` | Disabled automatically in production |
| `playground.enabled` | `true` | `LEX_GRAPHQL__PLAYGROUND__ENABLED` | Disabled automatically in production |
| `playground.path` | `"/graphql/playground"` | `LEX_GRAPHQL__PLAYGROUND__PATH` | Playground URL |
| `subscriptions.enabled` | `true` | `LEX_GRAPHQL__SUBSCRIPTIONS__ENABLED` | WebSocket subscriptions |
| `subscriptions.path` | `"/graphql/ws"` | `LEX_GRAPHQL__SUBSCRIPTIONS__PATH` | WebSocket endpoint |
| `depth_limit.enabled` | `true` | `LEX_GRAPHQL__DEPTH_LIMIT__ENABLED` | Enable query depth limiting |
| `depth_limit.max_depth` | `10` | `LEX_GRAPHQL__DEPTH_LIMIT__MAX_DEPTH` | Maximum allowed query depth |
| `complexity.enabled` | `true` | `LEX_GRAPHQL__COMPLEXITY__ENABLED` | Enable complexity scoring |
| `complexity.max_complexity` | `1000` | `LEX_GRAPHQL__COMPLEXITY__MAX_COMPLEXITY` | Maximum complexity score |
| `dataloader.enabled` | `true` | `LEX_GRAPHQL__DATALOADER__ENABLED` | Enable DataLoaderProtocol integration |
| `dataloader.batch_delay_ms` | `2.0` | `LEX_GRAPHQL__DATALOADER__BATCH_DELAY_MS` | Batch accumulation delay (ms) |
| `persisted_queries.enabled` | `true` | `LEX_GRAPHQL__PERSISTED_QUERIES__ENABLED` | Automatic persisted queries (APQ) |
| `cache.enabled` | `true` | `LEX_GRAPHQL__CACHE__ENABLED` | Response caching |
| `errors.mask_errors` | `true` | `LEX_GRAPHQL__ERRORS__MASK_ERRORS` | Mask internal errors in responses |
| `schema_baseline_path` | `null` | `LEX_GRAPHQL__SCHEMA_BASELINE_PATH` | SDL file for breaking-change detection |

## Module Factory Methods

| Method | Description |
|--------|-------------|
| `GraphQLModule.configure(...)` | Configure with explicit config and query class |
| `GraphQLModule.stub()` | Minimal config for testing |

## Key Features

- **Strawberry GraphQL** — schema-first GraphQL with type annotations
- **DataLoaderProtocol batching** — eliminates N+1 queries with per-request caching
- **WebSocket subscriptions** — `graphql-transport-ws` protocol support
- **Depth and complexity limiting** — prevents malicious or expensive queries
- **Field-level permissions** — `AbstractPermission` subclassing for fine-grained access
- **Automatic persisted queries (APQ)** — reduces payload size for repeated queries
- **Schema baseline checking** — detect breaking changes at boot via SDL comparison

## Testing

```python
from lexigram import Application
from lexigram.graphql import GraphQLModule

async with Application.boot(modules=[GraphQLModule.stub()]) as app:
    executor = await app.container.resolve(GraphQLExecutorProtocol)
    assert executor is not None
```

## Key Source Files

| File | What it contains |
|------|----------------|
| `src/lexigram/graphql/module.py` | `GraphQLModule.configure()`, `.stub()` |
| `src/lexigram/graphql/config.py` | `GraphQLConfig` and all sub-configs |
| `src/lexigram/graphql/di/provider.py` | `GraphQLProvider` boot and registration |
| `src/lexigram/graphql/security/permissions.py` | `AbstractPermission` base class |
| `src/lexigram/graphql/dataloader/loader.py` | `DataLoaderProtocol` implementation |
| `src/lexigram/graphql/decorators.py` | `@retry_resolver`, `@log_resolver` |