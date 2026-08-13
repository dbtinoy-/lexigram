---
title: lexigram-nosql Guide
description: Mental model, core concepts, and common patterns for document-store access.
---

## Requirements

| Package | Required | Purpose |
|---------|----------|---------|
| `lexigram` | Yes | Core framework |
| `lexigram-contracts` | Yes | Protocol definitions |
| `lexigram-cache` | Optional | Connection caching |

## Problem

Your application needs to store and query JSON-like documents — user profiles, product catalogs, audit logs — in a NoSQL database. You want to write code against a single abstraction and swap backends (MongoDB, DynamoDB, Firestore) without changing business logic.

## Mental Model

`lexigram-nosql` provides a **document-oriented** data layer parallel to `lexigram-sql`'s relational layer. The key abstractions are:

- **`DocumentStoreProtocol`** — connection lifecycle and collection access.
- **`CollectionProtocol`** — CRUD, indexing, and aggregation on a single collection.
- **`DocumentRepository`** — base class for repository-style access with entity mapping and soft-delete support.

All I/O returns dicts and async iterators — no ORM, no schema magic. You work with plain `dict[str, Any]` documents.

---

## Core Concepts

### Document Store

`DocumentStoreProtocol` (from `lexigram-contracts`) is the top-level handle. It connects, disconnects, hands out `CollectionProtocol` handles, and supports multi-document transactions.

```python
from lexigram.contracts.data.nosql import DocumentStoreProtocol
```

### Collections

A `CollectionProtocol` maps to a MongoDB collection, Firestore collection group, or DynamoDB table. It provides `insert_one`, `find`, `update_one`, `delete_one`, `aggregate`, `create_index`, and more.

:::note
Collection handles are cached by name — calling `store.collection("users")` twice returns the same handle.
:::

### Document Repository

`DocumentRepository[TEntity, TKey]` is the recommended pattern for entity-centric access:

```python
from lexigram.nosql.repository.base import DocumentRepository


class UserRepository(DocumentRepository[User, str]):
    collection_name = "users"

    async def _document_to_entity(self, doc: dict) -> User:
        return User(**doc)

    async def _entity_to_document(self, entity: User) -> dict:
        return entity.to_dict()
```

### Aggregation Pipeline

Build and execute aggregation pipelines with the `AggregationPipeline` builder:

```python
from lexigram.nosql import AggregationPipeline, AggregationOp

pipeline = (
    AggregationPipeline()
    .match({"status": "active"})
    .group("_id", {"total": AggregationOp.SUM(1)})
    .sort([("total", -1)])
)
```

---

## Typical Usage

### Write Path

```python
from lexigram.nosql.repository.base import DocumentRepository


class UserRepository(DocumentRepository[dict, str]):
    collection_name = "users"

    async def _document_to_entity(self, doc: dict) -> dict:
        return doc

    async def _entity_to_document(self, entity: dict) -> dict:
        return entity


# Usage in a service
class UserService:
    def __init__(self, repo: UserRepository) -> None:
        self.repo = repo

    async def create_user(self, name: str, email: str) -> dict:
        return await self.repo.save({"name": name, "email": email})

    async def find_by_email(self, email: str) -> dict | None:
        users = await self.repo.find_by_filter({"email": email})
        return users[0] if users else None

    async def delete_user(self, user_id: str) -> bool:
        return await self.repo.delete(user_id)
```

### Aggregation

```python
from lexigram.nosql import AggregationPipeline

pipeline = (
    AggregationPipeline()
    .match({"status": "active"})
    .group("_id", {
        "count": {"$sum": 1},
        "avg_score": {"$avg": "$score"},
    })
)
async with app.container.resolve(DocumentStoreProtocol) as store:
    async for doc in store.collection("results").aggregate(pipeline.build()):
        print(doc)
```

---

## Common Patterns

### Multi-Backend (Named Stores)

Register multiple document stores for different purposes:

```yaml
# application.yaml
nosql:
  backends:
    - name: primary
      driver: mongodb
      primary: true
      mongodb:
        uri: mongodb://localhost:27017
        database: app
    - name: analytics
      driver: mongodb
      mongodb:
        uri: mongodb://analytics:27017
        database: analytics
```

Resolve by name via `Annotated[T, Named(name)]`:

```python
from typing import Annotated
from lexigram.di.markers import Named


class DashboardService:
    def __init__(
        self,
        primary: DocumentStoreProtocol,
        analytics: Annotated[DocumentStoreProtocol, Named("analytics")],
    ) -> None:
        self.primary = primary
        self.analytics = analytics
```

### Soft Delete

Enable soft-delete on a repository to mark documents as deleted instead of removing them:

```python
class UserRepository(DocumentRepository[User, str]):
    collection_name = "users"

    def __init__(self, store: DocumentStoreProtocol) -> None:
        super().__init__(store, soft_delete=True)
```

All queries automatically filter out soft-deleted documents (`_deleted != true`).

### Specifications

Use filter expressions from `lexigram.contracts.data.protocols` for reusable queries:

```python
from lexigram.contracts.data.protocols import FieldEq, AndExpr


async def find_active_admins(repo: UserRepository) -> list[User]:
    active = FieldEq("status", "active")
    admin = FieldEq("role", "admin")
    combined = active & admin
    return await repo.find_by_spec(combined)
```

### Migrations

Define and apply schema migrations:

```python
from lexigram.nosql import MigrationManager, CreateIndex, AddField


manager = MigrationManager(db_name="myapp")
manager.add(CreateIndex("users", [("email", 1)], unique=True))
manager.add(AddField("users", "avatar_url", default=""))
await manager.apply()
```

---

## Best Practices

- ✅ Write a `DocumentRepository` subclass per entity — it centralises serialization.
- ✅ Use soft-delete for recoverable data; hard-delete for ephemeral data.
- ✅ Name backends semantically (`primary`, `analytics`, `audit`) rather than by host.
- ❌ Don't share a single `DocumentStoreProtocol` between logical domains — use named backends.
- ❌ Don't catch `NoSQLConnectionError` at the call site — let it propagate to the provider's health check.

## Next Steps

- [How-Tos](./HOWTOS.md) — task-oriented recipes
- [Architecture](./ARCHITECTURE.md) — internal design and extension points
- [Configuration](./CONFIGURATION.md) — every config key
