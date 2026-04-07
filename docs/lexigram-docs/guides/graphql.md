---
title: "GraphQL APIs"
description: "Schema-first GraphQL with Strawberry, subscriptions, and depth/complexity guards."
---

`lexigram-graphql` is a Strawberry-based GraphQL layer that plugs into `lexigram-web`. Resolvers receive their dependencies from the container, the schema is built and validated at boot, and depth, complexity, and alias guards are enabled by default. WebSocket subscriptions, automatic persisted queries, and a per-request DataLoader cache are all on by default and tuned via configuration.

For the complete API and tuning reference, see the [`lexigram-graphql` package docs](/packages/lexigram-graphql/).

---

## 1. Defining Root Types

Schemas are declared with Strawberry — `lexigram-graphql` adds DI, monitoring, and security around Strawberry's type system. Define your `Query` root with `@strawberry.type` and decorate fields with `lexigram.graphql.query`:

```python
import strawberry
from strawberry import Info
from lexigram.graphql import query


@strawberry.type
class User:
    id: strawberry.ID
    email: str
    display_name: str


@strawberry.type
class Query:
    @query(description="Look up a user by ID")
    async def user(self, info: Info, id: strawberry.ID) -> User | None:
        ...
```

The `query`, `mutation`, and `subscription` decorators are thin wrappers around `strawberry.field`/`mutation`/`subscription` that accept a `permission_classes=[...]` list for field-level authorization (see section 6).

---

## 2. Resolvers and Dependency Injection

Resolvers reach into the container through the GraphQL **context**. `get_context(info)` returns a `GraphQLContext` carrying the request, the authenticated principal, and a per-request container scope:

```python
from lexigram.graphql import query, get_context
from my_app.users.repository import UserRepository


@strawberry.type
class Query:
    @query()
    async def user(self, info: Info, id: strawberry.ID) -> User | None:
        ctx = get_context(info)
        repo = await ctx.container.resolve(UserRepository)
        result = await repo.find(str(id))
        return User(**result.value.__dict__) if result.is_ok() else None
```

`ctx.principal` is a `GraphQLPrincipal` (from `lexigram.contracts.graphql`) populated by the auth layer. For long-lived services, register a custom `ContextFactory` via `GraphQLModule.configure(context_factory_class=...)` and attach them once at context creation.

:::note
The container scope on `GraphQLContext` is per-request — services resolved here participate in request-scoped lifetimes and DataLoader caching automatically.
:::

---

## 3. Mutations with Input Types and Result

Mutations follow the same pattern, with `@strawberry.input` for argument shaping. Domain services return `Result[Ok, Err]`; map them onto a GraphQL union or a discriminated payload type:

```python
import strawberry
from strawberry import Info
from lexigram.graphql import mutation, get_context
from my_app.users.service import UserService, CreateUserError


@strawberry.input
class CreateUserInput:
    email: str
    display_name: str


@strawberry.type
class CreateUserFailure:
    code: str
    message: str


CreateUserPayload = strawberry.union("CreateUserPayload", (User, CreateUserFailure))


@strawberry.type
class Mutation:
    @mutation(description="Register a new user")
    async def create_user(
        self, info: Info, input: CreateUserInput
    ) -> CreateUserPayload:
        svc = await get_context(info).container.resolve(UserService)
        result = await svc.create(input.email, input.display_name)
        if result.is_ok():
            user = result.value
            return User(id=user.id, email=user.email, display_name=user.display_name)
        err: CreateUserError = result.error
        return CreateUserFailure(code=err.code, message=str(err))
```

---

## 4. Subscriptions

Subscriptions stream values to clients over a WebSocket. `lexigram-graphql` ships the `graphql-transport-ws` protocol enabled by default and mounted at `/graphql/ws`. Yield from an async generator to push updates:

```python
from collections.abc import AsyncGenerator
from lexigram.graphql import subscription, get_context
from lexigram.contracts.events import EventBusProtocol
from my_app.orders.events import OrderStatusChanged


@strawberry.type
class OrderStatus:
    order_id: strawberry.ID
    status: str


@strawberry.type
class Subscription:
    @subscription(description="Receive order status changes")
    async def order_status(
        self, info: Info, order_id: strawberry.ID
    ) -> AsyncGenerator[OrderStatus, None]:
        bus = await get_context(info).container.resolve(EventBusProtocol)
        async for event in bus.stream(OrderStatusChanged):
            if event.order_id == str(order_id):
                yield OrderStatus(order_id=order_id, status=event.status)
```

The `subscriptions[websockets]` extra is required: `uv add "lexigram-graphql[subscriptions]"`.

---

## 5. Depth and Complexity Limits

Hostile or accidentally recursive queries are blocked before execution. Both guards are on by default; tune the ceilings in YAML:

```yaml title="application.yaml"
graphql:
  depth_limit:
    enabled: true
    max_depth: 10
    ignore_introspection: true
  complexity:
    enabled: true
    max_complexity: 1000
    default_field_cost: 1.0
    default_list_cost: 10.0
```

Queries that exceed the budget are rejected with `QueryTooDeepError` or `QueryTooComplexError` — surfaced to the client as a structured GraphQL error, not a 500. An alias-limit validator is also wired in to mitigate alias-amplification attacks.

---

## 6. Configuration and Wiring

Add the module and (optionally) your root types. `WebModule` must be imported alongside it — the HTTP endpoint is mounted as a contributor to the web app at `/graphql`, with the playground at `/graphql/playground`:

```python
from lexigram import Application
from lexigram.di.module import Module, module
from lexigram.graphql import GraphQLModule
from lexigram.web import WebModule


@module(
    imports=[
        WebModule.configure(host="0.0.0.0", port=8000),
        GraphQLModule.configure(
            query_class=Query,
            mutation_class=Mutation,
            subscription_class=Subscription,
        ),
    ]
)
class AppModule(Module):
    pass
```

```yaml title="application.yaml"
graphql:
  path: "/graphql"
  debug: false
  playground:
    enabled: true
    path: "/graphql/playground"
  introspection:
    enabled: true
    allowed_environments: ["development", "testing"]
  subscriptions:
    enabled: true
    path: "/graphql/ws"
```

:::note
`introspection.enabled` and `playground.enabled` are auto-disabled when `LEX_ENV=production`, regardless of the YAML value. This is enforced inside `GraphQLConfig` validators, not something the deployer has to remember.
:::

---

## 7. Field-Level Permissions

Subclass `AbstractPermission` and pass instances via `permission_classes=[...]` on any decorator. Helpers like `IsAuthenticated`, `IsAdmin`, and `IsOwner` ship out of the box:

```python
from lexigram.graphql import query, IsAuthenticated


@strawberry.type
class Query:
    @query(permission_classes=[IsAuthenticated])
    async def me(self, info: Info) -> User: ...
```

---

## 8. Automatic Persisted Queries

APQ is enabled by default — clients send a SHA-256 hash on subsequent requests instead of the full query body, cutting payload size for repeated operations. Tune the store and TTL in config:

```yaml title="application.yaml"
graphql:
  persisted_queries:
    enabled: true
    store_type: "memory"     # or "redis"
    ttl_seconds: 86400
```

---

## 9. Testing

Use `GraphQLModule.stub()` for unit tests, or boot the full module and resolve the executor to drive real queries:

```python
from lexigram import Application
from lexigram.graphql import GraphQLModule
from lexigram.contracts.graphql import GraphQLExecutorProtocol


async def test_user_query() -> None:
    async with Application.boot(modules=[AppModule]) as app:
        executor = await app.container.resolve(GraphQLExecutorProtocol)
        result = await executor.execute(
            'query { user(id: "u1") { email } }',
        )
        assert result.is_ok()
        assert result.value["data"]["user"]["email"] == "ada@example.com"
```

See [Testing](/guides/testing/) for fixture patterns and stub modules.

---

## Next Steps

- [Event-Driven Architecture](/guides/event-driven/) — feed subscriptions from your domain event bus
- [Authentication & Authorization](/guides/authentication/) — populate `GraphQLPrincipal` and reuse policies in `AbstractPermission`
- [`lexigram-graphql` package](/packages/lexigram-graphql/) — DataLoader, federation, schema baselines, and metrics
