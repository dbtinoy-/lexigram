---
title: lexigram-graphql Quickstart
description: Install, configure, and execute your first GraphQL query in under 5 minutes
---

Install the package:

```bash
uv add lexigram-graphql
```

## Minimal example

```python
import asyncio
import strawberry
from lexigram import Application
from lexigram.graphql import GraphQLModule


@strawberry.type
class Query:
    @strawberry.field
    def hello(self) -> str:
        return "world"


async def main() -> None:
    app = Application(name="my-app")
    app.add_module(GraphQLModule.configure(query_class=Query))
    async with Application.boot(name="my-app", modules=[GraphQLModule.configure(query_class=Query)]) as app:
        from lexigram.contracts.graphql import GraphQLExecutorProtocol

        executor = await app.container.resolve(GraphQLExecutorProtocol)
        result = await executor.execute("{ hello }")
        if result.is_ok():
            print(result.unwrap()["data"])  # {'hello': 'world'}


asyncio.run(main())
```

## What just happened

- `GraphQLModule.configure()` registered the GraphQL provider, schema builder, and executor in the container
- The root `Query` type was attached to the schema
- `GraphQLExecutorProtocol.execute()` ran the query through the Strawberry execution pipeline

## Next steps

- [Guide](./GUIDE.md) — schema design, mutations, subscriptions, security
- [Architecture](./ARCHITECTURE.md) — provider, contracts, extensions, lifecycle
- [Configuration](./CONFIGURATION.md) — depth limits, caching, subscriptions, introspection
- [How-Tos](./HOWTOS.md) — resolvers, dataloaders, federation, persisted queries
