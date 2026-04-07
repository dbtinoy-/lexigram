---
title: lexigram-graphql How-Tos
description: Task-oriented recipes for common GraphQL scenarios
---

## How do I add a DataLoader for a resolver?

```python
from lexigram.graphql import create_loader

async def batch_users(keys: list[str]) -> list[User]:
    return await user_repo.get_by_ids(keys)

loader = create_loader(load_fn=batch_users, max_batch_size=100)
user = await loader.load("user-42")
users = await loader.load_many(["user-1", "user-2"])
```

## How do I register a DataLoader factory in the schema builder?

```python
builder.add_dataloader("users", lambda ctx: create_loader(
    load_fn=lambda keys: user_repo.get_by_ids(keys),
))
# Access in resolver: ctx.get_dataloader("users")
```

## How do I enable persisted queries (APQ)?

```python
from lexigram.graphql.config import GraphQLConfig, PersistedQueryConfig

config = GraphQLConfig(
    persisted_queries=PersistedQueryConfig(
        enabled=True,
        store_type="memory",
        ttl_seconds=86400,
    ),
)
```

## How do I add a custom permission check?

```python
from lexigram.graphql.security.permissions import AbstractPermission
import strawberry


class IsPremiumUser(AbstractPermission):
    async def has_permission(self, source, info, **kwargs) -> bool:
        user = info.context.request.user
        return user.is_premium


@strawberry.type
class Query:
    @strawberry.field(permission_classes=[IsPremiumUser])
    async def premium_content(self) -> str:
        return "premium data"
```

## How do I configure Apollo Federation?

```python
# Define an entity in your subgraph
@strawberry.federation.type(keys=["id"])
class User:
    id: strawberry.ID
    name: str

    @classmethod
    def resolve_reference(cls, id: strawberry.ID) -> "User":
        return user_repo.get_by_id(id)
```

## How do I set up WebSocket subscriptions?

Subscription support requires the `subscriptions` extra:

```bash
uv add lexigram-graphql[subscriptions]
```

Subscriptions use `graphql-transport-ws` protocol by default and are served at `/graphql/ws`.

## How do I add query depth limiting?

```python
from lexigram.graphql.config import GraphQLConfig, DepthLimitConfig

config = GraphQLConfig(
    depth_limit=DepthLimitConfig(
        enabled=True,
        max_depth=10,
    ),
)
# Queries exceeding 10 levels of nesting are rejected
# with a QUERY_TOO_DEEP error in the GraphQL response
```

## How do I set up cursor-based pagination?

```python
import strawberry
from lexigram.graphql import (
    Connection,
    Edge,
    PageInfo,
    create_connection_type,
    encode_cursor,
    decode_cursor,
)


@strawberry.type
class User:
    id: strawberry.ID
    name: str


UserConnection = create_connection_type(User)


@strawberry.type
class Query:
    @strawberry.field
    async def users(
        self,
        first: int | None = None,
        after: str | None = None,
    ) -> UserConnection:
        items = await get_all_users()
        offset = decode_cursor(after) + 1 if after else 0
        limit = first or 10
        page = items[offset : offset + limit]
        edges = [
            Edge(node=u, cursor=encode_cursor(offset + i))
            for i, u in enumerate(page)
        ]
        return UserConnection(
            edges=edges,
            page_info=PageInfo(
                has_next_page=(offset + limit < len(items)),
                has_previous_page=(offset > 0),
                start_cursor=edges[0].cursor if edges else None,
                end_cursor=edges[-1].cursor if edges else None,
            ),
            total_count=len(items),
        )
```

## How do I use GraphQL error extensions?

```python
from lexigram.graphql import GraphQLError, GraphQLErrorCode


def resolve_user(self, id: str) -> User:
    user = user_repo.get(id)
    if not user:
        raise GraphQLError(
            "User not found",
            code=GraphQLErrorCode.NOT_FOUND,
            user_id=id,
            resource_type="User",
        )
    return user
```

## How do I compare the current schema against a baseline?

```yaml
graphql:
  schema_baseline_path: ./schemas/baseline.graphql
```

The provider logs breaking removals at WARNING level and additions at DEBUG level during boot.

## How do I trace resolver execution?

```python
from lexigram.graphql import trace_resolver


@trace_resolver("fetch_users")
async def resolve_users(self, info) -> list[User]:
    ...
```

Tracing must be enabled in config (`tracing.enabled: true`).
