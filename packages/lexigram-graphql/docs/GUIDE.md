---
title: lexigram-graphql Guide
description: Mental model, schema design, subscriptions, security, and best practices
---

## Requirements

| Package | Required | Purpose |
|---------|----------|---------|
| `lexigram` | Yes | Core framework |
| `lexigram-contracts` | Yes | Protocol definitions |
| `lexigram-web` | Yes | HTTP server integration |
| `lexigram-cache` | Optional | Persisted queries |
| `lexigram-auth` | Optional | Authentication |
| `lexigram-resilience` | Optional | Rate limiting |

## Problem

Building a production GraphQL server involves more than defining types and resolvers. You need query depth limiting, complexity analysis, DataLoader batching, subscription handling, rate limiting, metrics, and persisted queries. `lexigram-graphql` provides all of this as a turnkey Strawberry-based GraphQL server integrated with the Lexigram DI container.

## Mental model

```
Schema types (Strawberry)
    │
    ▼
SchemaBuilder ──► SchemaValidator
    │                  │
    ├── query          ├── depth_limit
    ├── mutation       ├── complexity
    └── subscription   └── alias_limit
    │
    ▼
GraphQLExecutor ──► Extensions
    │                   ├── Tracing
    └──► Result         ├── Metrics
                        └── RateLimit
    │
    ▼
GraphQLController ──► HTTP (lexigram-web)
  or
Standalone executor
```

## Core concepts

### Schema definition

Use Strawberry types to define your schema:

```python
import strawberry


@strawberry.type
class Query:
    @strawberry.field
    async def users(self) -> list[User]:
        return await user_service.list_all()


@strawberry.type
class Mutation:
    @strawberry.mutation
    async def create_user(self, name: str, email: str) -> User:
        return await user_service.create(name=name, email=email)


@strawberry.type
class Subscription:
    @strawberry.subscription
    async def user_created(self) -> AsyncIterator[User]:
        async for user in user_service.events():
            yield user
```

### Auto-discovery

Scan packages for Strawberry types automatically:

```python
provider = GraphQLProvider.auto_discover("my_app.graphql")
```

### Context factory

Access the DI container and DataLoader instances in resolvers:

```python
from lexigram.graphql import GraphQLContext


@strawberry.type
class Query:
    @strawberry.field
    async def me(self, info: strawberry.types.Info) -> User:
        ctx: GraphQLContext = info.context
        user_service = await ctx.resolve(UserService)
        return await user_service.get_current()
```

### DataLoader

Solve N+1 queries with batching:

```python
from lexigram.graphql import create_loader

loader = create_loader(
    load_fn=lambda keys: user_repo.get_by_ids(keys),
)
users = await loader.load_many(["user-1", "user-2", "user-3"])
```

### Security

| Feature | Config | Default |
|---------|--------|---------|
| Depth limit | `depth_limit.max_depth` | 10 |
| Complexity limit | `complexity.max_complexity` | 1000 |
| Alias limit | (always on) | 15 |
| Rate limiting | `rate_limit.requests_per_minute` | 60 |
| Introspection | `introspection.allowed_environments` | dev + test |
| Playground | `playground.enabled` | auto-disabled in production |

## Typical usage

```python
from lexigram.app import Application
from lexigram.graphql import GraphQLModule, GraphQLConfig

config = GraphQLConfig(
    debug=True,
    depth_limit=DepthLimitConfig(max_depth=15),
)

app.add_module(GraphQLModule.configure(
    config=config,
    query_class=Query,
    mutation_class=Mutation,
))
```

## Best practices

- ✅ **Use DataLoader for all list-fetching resolvers** — prevents N+1 queries
- ✅ **Enable depth and complexity limits in production** — protects against abusive queries
- ✅ **Use persisted queries for high-traffic endpoints** — reduces bandwidth and parsing overhead
- ✅ **Set `playground.enabled: false` in production** — enabled by default; auto-disables when `LEX_ENV=production`
- ❌ **Don't share resolvers between queries and mutations** — mutations have different error semantics
- ❌ **Don't expose internal services directly in resolvers** — create dedicated resolver methods
