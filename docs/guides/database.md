---
title: "Database & Persistence"
description: "Async SQL with the repository pattern, domain models, and migrations."
---

`lexigram-sql` provides async database access for Postgres, MySQL, and SQLite. It favours a protocol-first **repository pattern**: your domain logic depends on contracts, not on a specific ORM, which keeps services clean and trivially testable.

For the complete API and performance tuning, see the [`lexigram-sql` package docs](/packages/lexigram-sql/).

---

## 1. The Repository Pattern

Define a **Protocol** that describes how data is accessed — your services depend on this, never on database internals.

```python
from typing import Protocol, runtime_checkable
from lexigram.result import Result
from my_app.domain.models import Product


@runtime_checkable
class ProductRepository(Protocol):
    async def find(self, product_id: str) -> Result[Product, str]: ...
    async def save(self, product: Product) -> Result[None, str]: ...
```

Implement it in your infrastructure layer:

```python
from lexigram import singleton
from lexigram.result import Result, Ok, Err
from my_app.domain.models import Product
from my_app.repositories.base import ProductRepository


@singleton
class SqlProductRepository(ProductRepository):
    async def find(self, product_id: str) -> Result[Product, str]:
        ...

    async def save(self, product: Product) -> Result[None, str]:
        ...
```

Bind the implementation to the protocol in a [provider](/fundamentals/providers/) so you can swap it for an in-memory fake in tests:

```python
async def register(self, container: ContainerRegistrarProtocol) -> None:
    container.singleton(ProductRepository, SqlProductRepository)
```

---

## 2. Domain Models

Lexigram models are lightweight dataclasses built on `DomainModel` — **not** SQLAlchemy ORM classes. SQLAlchemy is used internally by `lexigram-sql` for query building; your domain stays framework-agnostic.

```python
from dataclasses import dataclass
from lexigram.domain import DomainModel


@dataclass
class Product(DomainModel):
    id: str
    name: str
    stock: int = 0
```

For common CRUD, `lexigram-sql` ships a `GenericRepository` you can compose against a table:

```python
from lexigram.sql import GenericRepository

repo = GenericRepository[Product, str](
    provider=db_provider,
    table_name="products",
    entity_class=Product,
    key_field="id",
)
```

---

## 3. Configuration

Add the provider and configure the `sql` section. The connection URL uses an async driver (`postgresql+asyncpg://`, `mysql+aiomysql://`, `sqlite+aiosqlite://`):

```python
from lexigram import Application
from lexigram.sql import DatabaseProvider

app = Application(name="my-app")
app.add_provider(DatabaseProvider())
```

```yaml title="application.yaml"
sql:
  backend:
    url: "${DATABASE_URL:postgresql+asyncpg://user:pass@localhost/app}"
  pool:
    min_size: 2
    max_size: 10
  operations:
    echo: false          # log every SQL statement
```

---

## 4. Resolving the Database

The provider registers a `DatabaseService` (and `DatabaseProviderProtocol`) in the container. Inject it like any other dependency:

```python
from lexigram.contracts.data import DatabaseProviderProtocol


class ReportService:
    def __init__(self, db: DatabaseProviderProtocol) -> None:
        self._db = db

    async def total_products(self) -> int:
        rows = await self._db.execute_query("SELECT count(*) AS n FROM products")
        return rows[0]["n"]
```

Outside the container (scripts, tests), resolve from the booted app:

```python
async with Application.boot(providers=[DatabaseProvider()]) as app:
    db = await app.container.resolve(DatabaseProviderProtocol)
```

---

## 5. Multiple Databases

Declare a `backends` list to run several databases. Each is registered under its name and injected with `Named`:

```yaml title="application.yaml"
sql:
  backends:
    - name: primary
      primary: true
      backend: { url: "${DATABASE_URL}" }
    - name: analytics
      backend: { url: "${ANALYTICS_DATABASE_URL}" }
```

```python
from typing import Annotated
from lexigram.contracts.data import DatabaseProviderProtocol
from lexigram.di.markers import Named


class AnalyticsService:
    def __init__(
        self,
        primary: DatabaseProviderProtocol,                          # the primary backend
        analytics: Annotated[DatabaseProviderProtocol, Named("analytics")],
    ) -> None:
        ...
```

---

## 6. Migrations

`lexigram-cli` drives schema migrations:

```bash
lexigram db migrate "create products"    # generate a migration
lexigram db upgrade                       # apply pending migrations
lexigram db inspect                       # view current schema
```

---

## Next Steps

- [Dependency Injection](/fundamentals/dependency-injection/) — binding protocols to implementations
- [Result Pattern](/fundamentals/result-pattern/) — modelling expected failures
- [Testing](/guides/testing/) — swapping the repository for an in-memory fake
