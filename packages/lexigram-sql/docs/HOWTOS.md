---
title: lexigram-sql How-Tos
description: Task-oriented recipes for common database tasks.
---

## Define a Repository

```python
from dataclasses import dataclass
from lexigram.domain import DomainModel
from lexigram.contracts.data import DatabaseProviderProtocol
from lexigram.sql import GenericRepository


@dataclass
class User(DomainModel):
    id: int | None = None
    name: str = ""
    email: str = ""


class UserRepository:
    def __init__(self, db: DatabaseProviderProtocol) -> None:
        self.repo = GenericRepository[User, int](
            provider=db,
            table_name="users",
            entity_class=User,
            key_field="id",
        )

    async def find_by_email(self, email: str) -> User | None:
        return await self.repo.find_one(email=email)
```

## Run Migrations

```bash
# Using the CLI
uv run lexigram db upgrade

# Using AlembicManager directly
```

```python
from lexigram.sql.migrations.api import AlembicManager

manager = AlembicManager("postgresql+asyncpg://localhost/mydb", "migrations")
await manager.upgrade()
await manager.create("add_user_table")  # create a new migration
```

## Use DatabaseModule.stub() in Tests

```python
import pytest
from lexigram import Application
from lexigram.sql import DatabaseModule
from lexigram.contracts.data import DatabaseProviderProtocol
from lexigram.sql import GenericRepository


@pytest.mark.asyncio
async def test_user_repository():
    async with Application.boot(
        name="test",
        modules=[DatabaseModule.stub()],
    ) as app:
        db = await app.container.resolve(DatabaseProviderProtocol)
        repo = GenericRepository[dict, str](
            provider=db,
            table_name="test_users",
            entity_class=dict,
            key_field="id",
        )
        result = await repo.create({"name": "Test User"})
        assert result.is_ok()
```

## Query with Filters

```python
from lexigram.sql import F, Filter

# Find active users over 18, ordered by name
users = await repo.find(
    filters=[
        Filter("status", "==", "active"),
        Filter("age", ">=", 18),
    ],
    order_by=[F("name").asc()],
    limit=20,
    offset=0,
)

# Count matching
count = await repo.count(status="active")

# Check existence
exists = await repo.exists(email="test@example.com")
```

## Use a Custom Query with AsyncQueryBuilder

```python
from lexigram.sql.query import AsyncQueryBuilder, Operator

query = (
    AsyncQueryBuilder("users")
    .where("age", Operator.GTE, 18)
    .where("status", "=", "active")
    .order_by("created_at", ascending=False)
    .limit(10)
)
results = await query.fetch(db_provider)
```

## Use Unit of Work for Transactions

```python
from lexigram.sql import SimpleUnitOfWork


class UserService:
    def __init__(self, uow: SimpleUnitOfWork) -> None:
        self.uow = uow

    async def create_with_profile(self, user_data: dict) -> Result[User, Error]:
        async with self.uow:
            user = await self.uow.users.create(user_data)
            profile = await self.uow.profiles.create({"user_id": user.id, "bio": ""})
            await self.uow.commit()
            return Ok(user)
```

## Configure Multi-Backend (Multiple Databases)

```yaml
sql:
  backends:
    - name: primary
      backend:
        url: postgresql+asyncpg:///primary
      primary: true
    - name: analytics
      backend:
        url: postgresql+asyncpg:///analytics
```

```python
from typing import Annotated
from lexigram.contracts.data import DatabaseProviderProtocol


class AnalyticsService:
    def __init__(
        self,
        analytics_db: Annotated[DatabaseProviderProtocol, "analytics"],
        primary_db: DatabaseProviderProtocol,  # unnamed = primary
    ) -> None:
        self.analytics_db = analytics_db
        self.primary_db = primary_db
```

## Use DatabaseModule.scope() for Feature Repositories

```python
from lexigram.di.module import module
from lexigram.sql import DatabaseModule


@module(
    imports=[
        DatabaseModule.configure("postgresql:///mydb"),
        DatabaseModule.scope(UserRepository, OrderRepository),
    ]
)
class BillingModule(Module):
    pass
```

## Full-Text Search

```python
from lexigram.sql import full_text_search, FTSDialect

results = await full_text_search(
    provider=db,
    table="articles",
    query="python async framework",
    dialect=FTSDialect.POSTGRESQL,
    limit=10,
)
```

## Add Row-Level Security

```python
from lexigram.sql import RowLevelSecurityPolicy, ScopeColumn

policy = RowLevelSecurityPolicy(columns=[ScopeColumn("tenant_id")])
repo = GenericRepository[User, int](
    provider=db,
    table_name="users",
    entity_class=User,
    key_field="id",
    rls_policy=policy,
)
```
