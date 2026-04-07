---
title: lexigram-sql Troubleshooting
description: Common errors, causes, and fixes.
---

## `ConfigurationError: Invalid database URL prefix`

**Cause:** The `backend.url` does not start with a valid prefix (`sqlite`, `postgresql`, `mysql`, etc.).

**Fix:** Ensure the URL starts with a supported scheme:

```yaml
sql:
  backend:
    url: postgresql+asyncpg://user:pass@localhost/db  # ✅ correct
    url: mydb://localhost/db                            # ❌ invalid prefix
```

---

## `ConfigurationError: max_size must be >= min_size`

**Cause:** Pool `max_size` is smaller than `min_size`.

**Fix:** Adjust pool sizing:

```yaml
sql:
  pool:
    min_size: 2
    max_size: 10  # must be >= min_size
```

---

## `DatabaseError: could not connect to server`

**Cause:** Database server is unreachable, credentials are wrong, or the driver is not installed.

**Fix:**

```bash
# Install the Postgres driver
uv add "lexigram-sql[postgres]"

# Verify connection string
export LEX_SQL__BACKEND__URL=postgresql+asyncpg://user:password@localhost:5432/mydb
```

---

## `ImportError: no module named 'asyncpg'`

**Cause:** The async database driver is not installed. `lexigram-sql` depends only on SQLAlchemy and aiosqlite (SQLite) by default.

**Fix:** Install the appropriate extra:

```bash
uv add "lexigram-sql[postgres]"  # asyncpg
uv add "lexigram-sql[mysql]"     # aiomysql
# SQLite is included by default (aiosqlite)
```

---

## `RepositoryError: Table 'X' does not exist`

**Cause:** The table has not been created yet.

**Fix:** Run migrations:

```bash
uv run lexigram db upgrade
```

Or enable auto-migration in `DatabaseModule.configure()`:

```python
DatabaseModule.configure("...", enable_migrations=True)
```

---

## `OptimisticLockError: Version mismatch`

**Cause:** An update or delete failed because the row version changed since it was read (optimistic locking).

**Fix:** Re-fetch the entity and retry the operation:

```python
result = await repo.find_one(id=entity_id)
if result.is_ok():
    entity = result.unwrap()
    entity.value = new_value
    await repo.update(entity)
```

---

## Unit of Work operations not persisted

**Cause:** `commit()` was not called on the unit of work.

**Fix:** Always call `commit()` within the unit of work context:

```python
async with uow:
    await uow.users.create(data)
    await uow.commit()  # required
```

If `commit()` is not called, the transaction is rolled back on exit.

---

## `NoPrimaryBackendError: No database backend is configured`

**Cause:** `DatabaseProvider` is registered but no config has been provided.

**Fix:** Provide configuration — either via `application.yaml` or in code:

```python
from lexigram.sql import DatabaseProvider
from lexigram.sql.config import DatabaseConfig

app.add_provider(DatabaseProvider(config=DatabaseConfig.from_url("sqlite:///db.sqlite")))
```

---

## Slow connection / queries timing out

**Cause:** Default pool settings may be too low for production load.

**Fix:** Adjust pool and timeout settings:

```yaml
sql:
  pool:
    min_size: 5
    max_size: 30
    timeout: 60
  operations:
    statement_timeout: 120s
```

---

## Debug Tips

- Enable SQL echo: `export LEX_SQL__OPERATIONS__ECHO=true` (logs all SQL to the structured logger)
- Enable debug logging: `export LEX_LOG_LEVEL=DEBUG` for detailed lifecycle and query logs
- Use `DatabaseModule.stub()` with SQLite in-memory for fast, isolated tests
- Check that `DatabaseProviderProtocol` is registered (it's bound at `register()` time — verify the provider is added to `Application`)
- For connection issues, use `DatabaseProvider.health_check()` to get per-backend status
