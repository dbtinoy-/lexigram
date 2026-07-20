---
title: "Audit Trail"
description: "Append-only, HMAC-verified audit logging with retention management."
---

`lexigram-audit` provides append-only audit logging with HMAC-SHA256 tamper detection, retention policies, and scheduled verification. The audit subsystem is designed to be fire-tolerant — a logging failure never blocks the operation that triggered it.

For the full configuration reference, SQL store schema, and CLI commands, see the [`lexigram-audit` package docs](/packages/lexigram-audit/).

---

## 1. The Contracts

Three protocols define the audit stack:

```python
from typing import Protocol, runtime_checkable
from lexigram.contracts.audit import (
    AuditLoggerProtocol,
    AuditStoreProtocol,
    AuditVerifierProtocol,
    RetentionPolicyProtocol,
    AuditEntry,
    AuditQuery,
    AuditEventSeverity,
    AuditMismatch,
    RetentionDecision,
)


@runtime_checkable
class MyAuditLogger(AuditLoggerProtocol, Protocol):
    async def log(self, entry: AuditEntry) -> None: ...   # never raises
    async def query(self, query: AuditQuery) -> list[AuditEntry]: ...


@runtime_checkable
class MyAuditVerifier(AuditVerifierProtocol, Protocol):
    async def verify_recent(self, *, limit: int = 100) -> list[AuditMismatch]: ...
    async def verify_entry(self, entry_id: str) -> bool: ...
```

`AuditEntry` captures the full context of a security-relevant operation:

```python
AuditEntry(
    action="user.update",
    actor_id="user-123",
    resource_type="User",
    resource_id="user-456",
    outcome="success",
    severity=AuditEventSeverity.MEDIUM,
    occurred_at=datetime.now(UTC),
    metadata={"changed_fields": ["email"]},
    old_values={"email": "old@example.com"},
    new_values={"email": "new@example.com"},
    source="admin-api",
)
```

---

## 2. Configuration

Configure the audit subsystem through `AuditModule.configure()`:

```python
from lexigram import Application
from lexigram.audit import AuditModule

app = Application(name="my-app")
app.add_module(AuditModule.configure(
    hmac_key=b"your-hmac-secret-key",
    store_backend="sql",          # "sql" or "memory"
    table_name="audit_log",
    retention_days=365,
    enable_admin=True,
))
```

In `application.yaml`:

```yaml title="application.yaml"
audit:
  store_backend: "sql"
  table_name: "audit_log"
  hmac_key: "${AUDIT_HMAC_KEY}"
  verification_schedule: "0 * * * *"    # hourly
  verification_batch_size: 100
  retention_policy:
    name: "default"
    default_retention_days: 365
    severity_overrides:
      critical: 2555
      high: 1095
```

:::note
The `hmac_key` is required for tamper detection. Without it, verification is a no-op. In production, source it from a secret manager, not config files.
:::

---

## 3. Writing Audit Entries

Inject `AuditLoggerProtocol` and call `log()`:

```python
from lexigram.contracts.audit import (
    AuditLoggerProtocol,
    AuditEntry,
    AuditQuery,
    AuditEventSeverity,
)
from lexigram.result import Result, Ok, Err


class UserService:
    def __init__(self, audit: AuditLoggerProtocol) -> None:
        self._audit = audit

    async def update_email(self, user_id: str, new_email: str) -> Result[str, str]:
        old_email = await self._repo.get_email(user_id)
        if old_email is None:
            return Err("User not found")

        await self._repo.set_email(user_id, new_email)

        await self._audit.log(AuditEntry(
            action="user.update_email",
            actor_id=user_id,
            resource_type="User",
            resource_id=user_id,
            outcome="success",
            severity=AuditEventSeverity.MEDIUM,
            old_values={"email": old_email},
            new_values={"email": new_email},
            source="user-service",
        ))
        return Ok(new_email)
```

`log()` is fire-tolerant — it never raises. If the store is unavailable, the entry is discarded and a warning is logged.

---

## 4. The `@audited` Decorator

For common patterns, the `@audited` decorator attaches metadata that an interceptor reads to log automatically:

```python
from lexigram.audit.decorators import audited


class ProductService:
    @audited("product.delete", resource_type="Product", severity="high")
    async def delete_product(self, product_id: str) -> None:
        await self._repo.delete(product_id)
```

The decorator sets `__audited__`, `__audit_action__`, `__audit_resource_type__`, and `__audit_severity__` attributes on the function.

---

## 5. Querying the Trail

Query entries with the composable `AuditQuery`:

```python
from lexigram.contracts.audit import AuditQuery, AuditEventSeverity


async def find_recent_failures(self, actor_id: str) -> list[AuditEntry]:
    query = AuditQuery(
        actor_id=actor_id,
        outcome="failure",
        severity=AuditEventSeverity.HIGH,
        since=datetime.now(UTC) - timedelta(hours=24),
        limit=50,
    )
    return await self._audit.query(query)
```

---

## 6. HMAC Verification

Every entry appended to the store gets an HMAC-SHA256 checksum over its serialised content. Verification detects tampering:

```python
from lexigram.audit import AuditVerifier, verify_audit_checksum


async def verify_integrity(verifier: AuditVerifier) -> None:
    mismatches = await verifier.verify_recent(limit=1000)
    for m in mismatches:
        print(f"TAMPERED: entry {m.entry_id} — stored {m.expected_checksum}, actual {m.actual_checksum}")

    is_valid = await verifier.verify_entry("entry-abc-123")
    assert is_valid
```

:::tip
Checksum verification uses constant-time comparison (`hmac.compare_digest`) to prevent timing attacks.
:::

---

## 7. Retention & Purging

Define a retention policy with severity-based overrides:

```python
from lexigram.contracts.audit import RetentionPolicy

policy = RetentionPolicy(
    name="default",
    default_retention_days=365,
    severity_overrides={
        "critical": 2555,  # 7 years
        "high": 1095,      # 3 years
    },
)
```

Run the purger manually or via cron:

```python
from lexigram.audit import AuditPurger

purger = AuditPurger(store, policy)
purged = await purger.purge_expired()
print(f"Purged {purged} expired entries")
```

The purger logs its own activity as audit entries — meta-audit.

Run a dry run before the first real purge on an existing deployment —
the audit log may contain a backlog that was never actually purged
before this fix shipped (purge previously counted expired entries but
did not delete them). A dry run reports exactly the count a real run
would report, without deleting anything:

```python
would_purge = await purger.purge_expired(dry_run=True)
print(f"Would purge {would_purge} expired entries")
```

The purger logs its own activity as audit entries — meta-audit, including
the `dry_run` flag on each purger run.

---

## 8. Testing

For unit tests, configure the module with `store_backend="memory"`:

```python
from lexigram import Application
from lexigram.audit import AuditModule
from lexigram.contracts.audit import AuditLoggerProtocol, AuditEntry


async def test_logs_audit_entry() -> None:
    async with Application.boot(
        modules=[AuditModule.configure(hmac_key=b"test", store_backend="memory")]
    ) as app:
        logger = await app.container.resolve(AuditLoggerProtocol)
        await logger.log(AuditEntry(action="test.event", actor_id="tester"))
        results = await logger.query(AuditQuery(limit=10))
        assert len(results) == 1
        assert results[0].action == "test.event"
```

:::note
The in-memory store uses a bounded `deque` (max 10,000 entries). For larger test suites, use `SqlAuditStore` backed by SQLite.
:::

---

## Next Steps

- [Dependency Injection](/fundamentals/dependency-injection/) — binding protocols to implementations
- [Providers](/fundamentals/providers/) — how `AuditBundleProvider` hooks into application boot
- [Testing](/guides/testing/) — substituting stubs for infrastructure
- [`lexigram-audit` package](/packages/lexigram-audit/) — CLI commands, SQL store schema, admin dashboard
