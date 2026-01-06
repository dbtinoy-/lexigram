---
title: lexigram-sql Configuration
description: Every configuration key for the SQL database layer.
---

## Config Section

All database configuration lives under the `sql` key in `application.yaml`. The provider auto-injects `DatabaseConfig` — no manual loading needed.

Config section: `sql` | Env prefix: `LEX_SQL__` | Nested delimiter: `__`

```yaml
sql:
  enabled: true
  backend:
    url: postgresql+asyncpg://user:pass@localhost/mydb
  pool:
    min_size: 2
    max_size: 10
  operations:
    echo: false
```

```bash
export LEX_SQL__BACKEND__URL=postgresql+asyncpg://user:pass@localhost/mydb
export LEX_SQL__POOL__MIN_SIZE=2
```

---

## DatabaseConfig

| Key | Type | Default | Env Var | Description |
|-----|------|---------|---------|-------------|
| `enabled` | `bool` | `True` | `LEX_SQL__ENABLED` | Enable the database module |
| `backend` | `DatabaseBackendConfig` | `sqlite:///piccolina.db` | `LEX_SQL__BACKEND__*` | Connection URL and driver |
| `pool` | `DatabasePoolConfig` | (see below) | `LEX_SQL__POOL__*` | Connection pool settings |
| `operations` | `DatabaseOperationConfig` | (see below) | `LEX_SQL__OPERATIONS__*` | Operation settings |
| `outbox` | `DatabaseOutboxConfig` | (see below) | `LEX_SQL__OUTBOX__*` | Outbox pattern settings |
| `migrations` | `DatabaseMigrationConfig` | (see below) | `LEX_SQL__MIGRATIONS__*` | Migration settings |
| `audit_hmac_key` | `str \| None` | `None` | `LEX_SQL__AUDIT_HMAC_KEY` | HMAC key for audit signing |
| `backends` | `list[NamedDatabaseConfig]` | `[]` | `LEX_SQL__BACKENDS` | Multi-database backends |

---

## DatabaseBackendConfig

| Key | Type | Default | Env Var | Description |
|-----|------|---------|---------|-------------|
| `url` | `SecretStr` | **required** | `LEX_SQL__BACKEND__URL` | Database connection URL |

Valid URL prefixes: `sqlite`, `postgresql`, `postgres`, `mysql`, `mariadb`, `oracle`, `mssql`, `custom`.

---

## DatabasePoolConfig

| Key | Type | Default | Env Var | Description |
|-----|------|---------|---------|-------------|
| `min_size` | `int` | `1` | `LEX_SQL__POOL__MIN_SIZE` | Minimum pool connections |
| `max_size` | `int` | `10` | `LEX_SQL__POOL__MAX_SIZE` | Maximum pool connections |
| `max_overflow` | `int` | `5` | `LEX_SQL__POOL__MAX_OVERFLOW` | Max overflow connections |
| `recycle` | `int` | `3600` | `LEX_SQL__POOL__RECYCLE` | Connection recycle time (seconds) |
| `timeout` | `float` | `30.0` | `LEX_SQL__POOL__TIMEOUT` | Pool timeout (seconds) |
| `acquire_timeout` | `Duration` | `30s` | `LEX_SQL__POOL__ACQUIRE_TIMEOUT` | Connection acquire timeout |
| `idle_timeout` | `Duration` | `5m` | `LEX_SQL__POOL__IDLE_TIMEOUT` | Idle connection timeout |
| `max_lifetime` | `Duration` | `1h` | `LEX_SQL__POOL__MAX_LIFETIME` | Max connection lifetime |

---

## DatabaseOperationConfig

| Key | Type | Default | Env Var | Description |
|-----|------|---------|---------|-------------|
| `echo` | `bool` | `False` | `LEX_SQL__OPERATIONS__ECHO` | Log all SQL statements |
| `statement_timeout` | `Duration` | `60s` | `LEX_SQL__OPERATIONS__STATEMENT_TIMEOUT` | Max query execution time |

---

## DatabaseOutboxConfig

| Key | Type | Default | Env Var | Description |
|-----|------|---------|---------|-------------|
| `enabled` | `bool` | `True` | `LEX_SQL__OUTBOX__ENABLED` | Enable outbox pattern |
| `poll_interval` | `Duration` | `5s` | `LEX_SQL__OUTBOX__POLL_INTERVAL` | Outbox poll interval |
| `batch_max_age` | `Duration` | `30s` | `LEX_SQL__OUTBOX__BATCH_MAX_AGE` | Max age for outbox batches |

---

## DatabaseMigrationConfig

| Key | Type | Default | Env Var | Description |
|-----|------|---------|---------|-------------|
| `lock_timeout` | `Duration` | `30s` | `LEX_SQL__MIGRATIONS__LOCK_TIMEOUT` | Migration lock timeout |

---

## NamedDatabaseConfig

| Key | Type | Default | Env Var | Description |
|-----|------|---------|---------|-------------|
| `name` | `str` | **required** | `LEX_SQL__BACKENDS__0__NAME` | Unique backend name |
| `backend` | `DatabaseBackendConfig` | **required** | `LEX_SQL__BACKENDS__0__BACKEND__*` | Connection config |
| `primary` | `bool` | `False` | `LEX_SQL__BACKENDS__0__PRIMARY` | Primary backend (unnamed bindings) |
| `pool` | `DatabasePoolConfig` | `min_size=2` | `LEX_SQL__BACKENDS__0__POOL__*` | Per-backend pool settings |
| `migration_dir` | `str \| None` | `None` | `LEX_SQL__BACKENDS__0__MIGRATION_DIR` | Alembic dir for this backend |

---

## DataConfig

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `default_page_size` | `int` | `20` | Default pagination page size |
| `max_page_size` | `int` | `100` | Maximum allowed page size |
| `default_cursor_size` | `int` | `20` | Default cursor pagination size |

---

## Application Example

```yaml
# application.yaml
sql:
  enabled: true
  backend:
    url: postgresql+asyncpg://user:password@localhost:5432/mydb
  pool:
    min_size: 2
    max_size: 20
    timeout: 30
  operations:
    echo: false
  audit_hmac_key: "${AUDIT_HMAC_KEY}"
```

Environment override equivalent:

```bash
export LEX_SQL__BACKEND__URL=postgresql+asyncpg://user:password@localhost:5432/mydb
export LEX_SQL__POOL__MIN_SIZE=5
export LEX_SQL__POOL__MAX_SIZE=30
export LEX_SQL__AUDIT_HMAC_KEY=my-hmac-key
```

### Multi-Backend Example

```yaml
sql:
  backends:
    - name: primary
      backend:
        url: postgresql+asyncpg:///primary
      primary: true
      pool:
        min_size: 5
        max_size: 20
    - name: reporting
      backend:
        url: postgresql+asyncpg:///reporting
      migration_dir: migrations/reporting
      pool:
        min_size: 2
        max_size: 10
```

:::warning
In production, set `LEX_SQL__BACKEND__URL` via environment variable — never hardcode credentials in YAML. The production validator rejects common default passwords.
:::
