---
title: lexigram-sql Backends
description: Compare Postgres, MySQL, and SQLite backends for lexigram-sql
sidebar:
  order: 3
---

`lexigram-sql` ships three database backends. All implement `DatabaseProviderProtocol` from `lexigram-contracts` and expose the same repository, unit-of-work, and migration APIs.

## Supported Backends

| Backend | Extra | Driver | Production-ready | Best for |
|---------|-------|--------|-----------------|----------|
| Postgres | `lexigram-sql[postgres]` | `asyncpg>=0.29.0` | Yes | Primary production database |
| MySQL | `lexigram-sql[mysql]` | `aiomysql>=0.1.0` | Yes | Existing MySQL/MariaDB deployments |
| SQLite | `lexigram-sql[sqlite]` | `aiosqlite>=0.22.1` | Development / test | Local dev, CI, single-user apps |

:::note
SQLite (`aiosqlite`) is a core dependency — no extra needed. Install extras for Postgres and MySQL: `pip install lexigram-sql[postgres,mysql]`.
:::

## Backend Details

### Postgres

The production-grade backend. Connection pooling, prepared statements, advisory locks, and full-text search (`PostgresFTSQuery`) are all supported.

- **Strengths:** Best-in-class reliability, advisory locks for distributed coordination, rich data types, row-level security support (`RowLevelSecurityPolicy`).
- **Weaknesses:** Requires an external Postgres server; connection overhead makes it unsuitable for ephemeral/CI workflows.
- **When to choose:** Any production deployment, especially multi-service, multi-tenant, or data-intensive apps.

```yaml
# application.yaml
sql:
  backend:
    url: postgresql://user:pass@localhost:5432/mydb
  pool:
    min_size: 2
    max_size: 20
```

### MySQL

Full MySQL/MariaDB support via `aiomysql`. Includes `MySQLFTSQuery` for full-text search.

- **Strengths:** Drop-in for existing MySQL infrastructure; mature replication tooling.
- **Weaknesses:** Slightly narrower feature set than Postgres (no advisory locks, no partial indexes in older versions).
- **When to choose:** You already run MySQL or need MariaDB compatibility.

```yaml
sql:
  backend:
    url: mysql://user:pass@localhost:3306/mydb
```

### SQLite

Zero-config file-based backend via `aiosqlite`. SQLite is the default when no URL is provided.

- **Strengths:** No server process, no install — just a file path. Perfect for tests and single-user tools.
- **Weaknesses:** No concurrency (WAL mode helps but doesn't replace a real server); fewer SQL features.
- **When to choose:** Unit tests (`DatabaseModule.stub()`), local development, embedded or single-process apps.

```yaml
sql:
  backend:
    url: sqlite:///./dev.db    # file-based
```

Or in code:

```python
config = DatabaseConfig.from_url("sqlite:///:memory:")
```

## Quick Selection Guide

- **I'm deploying to production** → `postgres` (with `asyncpg`). Use the `postgres` extra.
- **My org already uses MySQL** → `mysql` (with `aiomysql`). Use the `mysql` extra.
- **I need a test database** → `sqlite` (with `aiosqlite`). No extra needed. Use `DatabaseModule.stub()`.
- **I'm building a CLI tool** → `sqlite`. Zero install, zero config.
- **I need multiple databases** → Use the `backends:` list (see below).

## Multi-Backend Configuration

When your app talks to more than one database, configure them as named backends:

```yaml
sql:
  backends:
    - name: primary
      backend:
        url: postgresql://user:pass@primary-host:5432/app
      primary: true
    - name: analytics
      backend:
        url: postgresql://user:pass@analytics-host:5432/olap
```

Resolve by name:

```python
from typing import Annotated
from lexigram.contracts.data import DatabaseProviderProtocol
from lexigram.di.markers import Named

# Injected by name
class ReportService:
    def __init__(
        self,
        primary: DatabaseProviderProtocol,
        analytics: Annotated[DatabaseProviderProtocol, Named("analytics")],
    ):
        ...
```

Backends without `primary: true` must be resolved via `Named(name)`. The primary backend also receives the unnamed binding for backward compatibility.

## Testing

Use the in-memory SQLite backend for tests — no server, no file I/O:

```python
from lexigram.sql import DatabaseModule, DatabaseConfig

stub = DatabaseModule.stub(DatabaseConfig.from_url("sqlite:///:memory:"))
```

Or set it via config:

```python
config = DatabaseConfig(
    backend=DatabaseBackendConfig(url="sqlite:///:memory:"),
)
```

:::tip
The in-memory SQLite backend is **not** a mock — it runs real SQL. Use it to catch dialect differences early if you deploy on Postgres. Match your production dialect in CI.
:::

## Async vs Sync

All three backends are **async-only** via the async driver. There is no synchronous fallback. Every repository method, migration, and query runs through `asyncio`.

To call from sync code, use `run_in_threadpool_with_context`:

```python
from lexigram.sql.context import run_in_threadpool_with_context

result = await run_in_threadpool_with_context(sync_function, arg)
```
