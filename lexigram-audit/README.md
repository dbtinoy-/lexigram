# lexigram-audit

Unified audit trail for the Lexigram Framework — append-only, HMAC-verified, retention-managed.

---

## Overview

`lexigram-audit` provides a unified, append-only audit trail with HMAC-SHA256 tamper detection, configurable per-severity retention policies, and scheduled integrity verification batches. The `AuditLogger` is fire-tolerant — audit failures never interrupt business logic.

---


> Full documentation: [docs.lexigram.dev](https://docs.lexigram.dev)
## Install

```bash
uv add lexigram lexigram-audit

# For the SQL backend (recommended for production)
uv add lexigram-sql
```

## Quick Start

```python
from lexigram import Application
from lexigram.di.module import Module, module
from lexigram.audit import AuditModule
from lexigram.audit.config import AuditConfig, RetentionPolicyConfig


@module(
    imports=[
        AuditModule.configure(
            AuditConfig(
                store_backend="sql",
                hmac_key="your-hex-encoded-hmac-key",
                retention_policy=RetentionPolicyConfig(default_retention_days=365),
            )
        )
    ]
)
class AppModule(Module):
    pass


async def main() -> None:
    async with Application.boot(modules=[AppModule]) as app:
        from lexigram.audit.logger import AuditLogger
        audit = await app.container.resolve(AuditLogger)

        await audit.log(
            action="user.deleted",
            actor_id="user-123",
            resource_type="user",
            resource_id="user-42",
            severity="high",
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

## Configuration

> **Zero-config usage:** Call `AuditModule.configure()` with no arguments to use all defaults.

### Option 1 — YAML file

```yaml
# application.yaml
audit:
  store_backend: "sql"
  hmac_key: null
  retention_policy:
    default_retention_days: 365
  enable_admin: true
```

### Option 2 — Profiles + Environment Variables *(recommended)*

```bash
export LEX_AUDIT__STORE_BACKEND=sql
export LEX_AUDIT__HMAC_KEY=your-hex-encoded-key
export LEX_AUDIT__RETENTION_POLICY__DEFAULT_RETENTION_DAYS=365
```

### Option 3 — Python

```python
from lexigram.audit import AuditModule
from lexigram.audit.config import AuditConfig, RetentionPolicyConfig

AuditModule.configure(
    AuditConfig(
        store_backend="sql",
        hmac_key="your-hex-encoded-hmac-key",
        retention_policy=RetentionPolicyConfig(
            default_retention_days=365,
            severity_overrides={"critical": 2555, "high": 1095},
        ),
        enable_admin=True,
    )
)
```

### Config reference

| Field | Default | Env var | Description |
|-------|---------|---------|-------------|
| `store_backend` | `"sql"` | `LEX_AUDIT__STORE_BACKEND` | Storage backend: `"sql"` or `"memory"` |
| `table_name` | `"audit_log"` | `LEX_AUDIT__TABLE_NAME` | SQL table name (SQL backend only) |
| `hmac_key` | `null` | `LEX_AUDIT__HMAC_KEY` | Hex-encoded HMAC-SHA256 key; `null` disables tamper detection |
| `retention_policy.default_retention_days` | `365` | `LEX_AUDIT__RETENTION_POLICY__DEFAULT_RETENTION_DAYS` | Default retention in days (0 = indefinite) |
| `retention_policy.severity_overrides` | `{}` | — | Per-severity retention overrides (days) |
| `verification_schedule` | `"0 * * * *"` | `LEX_AUDIT__VERIFICATION_SCHEDULE` | Cron expression for HMAC verification runs |
| `verification_batch_size` | `100` | `LEX_AUDIT__VERIFICATION_BATCH_SIZE` | Entries verified per scheduled run |
| `enable_admin` | `true` | `LEX_AUDIT__ENABLE_ADMIN` | Enable admin dashboard integration |

## Module Factory Methods

| Method | Description |
|--------|-------------|
| `AuditModule.configure(config)` | Configure with explicit `AuditConfig` |
| `AuditModule.stub()` | In-memory store, checksums disabled — for unit tests |

## Key Features

- **Fire-tolerant logging** — `AuditLogger.log()` never blocks calling code; errors are logged at WARNING and swallowed
- **HMAC-SHA256 checksums** — per-entry tamper detection verified on schedule or on-demand
- **Per-severity retention** — `PolicyBasedRetention` applies different retention periods per severity level
- **SQL backend** — append-only `SqlAuditStore` backed by `lexigram-sql`
- **Memory backend** — bounded in-process store for development and testing
- **Admin dashboard** — `AuditAdminContributor` adds an Audit Log panel
- **Scheduled verification** — hourly HMAC batch verification when a task scheduler is present

## Testing

```python
import pytest
from lexigram import Application
from lexigram.audit import AuditModule
from lexigram.audit.logger import AuditLogger
from lexigram.audit.store.memory import InMemoryAuditStore


@pytest.mark.asyncio
async def test_audit_log_records_entry() -> None:
    async with Application.boot(modules=[AuditModule.stub()]) as app:
        audit = await app.container.resolve(AuditLogger)
        store = await app.container.resolve(InMemoryAuditStore)

        await audit.log(
            action="user.created",
            actor_id="actor-1",
            resource_type="user",
            resource_id="user-42",
        )

        entries = await store.query(action="user.created")
        assert len(entries) == 1
        assert entries[0].actor_id == "actor-1"
```

## Key Source Files

| File | What it contains |
|------|----------------|
| `src/lexigram/audit/module.py` | `AuditModule.configure()`, `.stub()` |
| `src/lexigram/audit/config.py` | `AuditConfig`, `RetentionPolicyConfig` |
| `src/lexigram/audit/di/bundle_provider.py` | `AuditBundleProvider` boot and registration |
| `src/lexigram/audit/logger.py` | `AuditLogger` (fire-tolerant entry point) |
| `src/lexigram/audit/store/memory.py` | `InMemoryAuditStore` |
| `src/lexigram/audit/store/sql.py` | `SqlAuditStore` |
| `src/lexigram/audit/integrity/hmac.py` | HMAC-SHA256 checksum logic |
| `src/lexigram/audit/retention/policy.py` | `PolicyBasedRetention` |
| `src/lexigram/audit/admin/contributor.py` | `AuditAdminContributor` |