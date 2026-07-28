---
title: lexigram-audit Guide
description: Concepts, mental model, and common usage patterns for lexigram-audit
sidebar:
  order: 2
---

## Requirements

| Package | Required | Purpose |
|---------|----------|---------|
| `lexigram` | Yes | Core framework |
| `lexigram-contracts` | Yes | Protocol definitions |
| `lexigram-sql` | Optional | Audit trail storage |
| `lexigram-queue` | Optional | Async audit events |

## Problem

Security-sensitive and compliance-relevant operations must be recorded in a tamper-evident, append-only log. Without a structured audit trail you cannot:

- Investigate security incidents
- Satisfy compliance requirements (SOC 2, GDPR, HIPAA)
- Detect unauthorized data access or modification

**lexigram-audit** provides an append-only, HMAC-verified, retention-managed audit trail that integrates with the Lexigram DI container.

## Mental Model

```
Operation (e.g. user.login)
    │
    ▼
AuditLogger.log(entry)   ← fire-tolerant, never raises
    │
    ▼
AuditStoreProtocol        ← pluggable backend (SQL or memory)
    │
    ├── Checksum computed (HMAC-SHA256)
    ├── Retention evaluated
    └── Entry persisted
```

- **Append-only** — entries are never modified after writing.
- **Fire-tolerant** — `log()` catches all exceptions. Audit failure never blocks the triggering operation.
- **HMAC-verified** — entries can be checksummed for tamper detection.
- **Retention-managed** — entries expire based on severity and source overrides.
- **Pluggable backends** — SQL (production) or in-memory (testing).

## Core Concepts

### AuditEntry

An immutable record of a security-relevant operation:

```python
from lexigram.contracts.audit import AuditEntry, AuditEventSeverity

entry = AuditEntry(
    action="user.update",           # dot-notation action identifier
    actor_id="user-42",             # who performed the action
    resource_type="User",           # kind of affected resource
    resource_id="user-99",          # affected resource ID
    outcome="success",              # "success" or "failure"
    severity=AuditEventSeverity.MEDIUM,
    metadata={"changed_field": "email"},
    old_values={"email": "old@example.com"},
    new_values={"email": "new@example.com"},
    source="sql",                   # originating subsystem
    tenant_id="tenant-acme",        # optional multi-tenant scope
)
```

### AuditLogger

The primary entrypoint. Implements `AuditLoggerProtocol`. Fire-tolerant — `log()` never raises, `query()` returns an empty list on error.

```python
from lexigram.contracts.audit import AuditLoggerProtocol, AuditQuery

# Resolve from the container
logger = await container.resolve(AuditLoggerProtocol)

# Record
await logger.log(entry)

# Query
results = await logger.query(AuditQuery(actor_id="user-42", limit=50))
```

### AuditStore

Backend persistence layer. Implements `AuditStoreProtocol`. Two implementations:

- **SQL** (`SqlAuditStore`) — production. Requires `lexigram-audit[sql]`.
- **InMemory** (`InMemoryAuditStore`) — testing and development.

The store is append-only — purge operations happen at a higher level through `AuditPurger`.

### Retention

Entries expire based on a `RetentionPolicy`. The `PolicyBasedRetention` implementation supports severity and source overrides:

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

`AuditPurger` evaluates entries against the policy and purges expired ones.

### Verification

HMAC-SHA256 checksums enable tamper detection. Enable by setting `hmac_key` in config:

```python
from lexigram.audit import compute_audit_checksum, verify_audit_checksum

entry_data = {"action": "user.login", "actor_id": "user-42"}
checksum = compute_audit_checksum(entry_data, key=b"secret")
assert verify_audit_checksum(entry_data, key=b"secret", expected=checksum)
```

The `AuditVerifier` (implements `AuditVerifierProtocol`) performs batch verification. Full tamper detection requires the SQL backend which stores checksums in a dedicated column.

## Best Practices

- **Audit every auth event.** Login, logout, privilege escalation, permission changes.
- **Audit data mutations.** Resource creation, update, and deletion with `old_values`/`new_values`.
- **Set HMAC key in production.** Without it, tamper detection is a no-op.
- **Configure retention for compliance.** Match retention periods to your regulatory requirements (SOC 2: 1 year; GDPR: 3 years; HIPAA: 6 years).
- **Use severity consistently.** Reserve `CRITICAL` for compliance-mandated events.
- **Never block on audit failure.** The fire-tolerant design is intentional — audit logging is advisory at the call site.

## Module Wiring

Use `AuditModule.configure()` for the module form:

```python
from lexigram import Application
from lexigram.audit import AuditModule

app = Application(name="my-app")
app.add_module(AuditModule.configure(
    store_backend="sql",
    retention_days=365,
    hmac_key=b"my-hmac-key",
))
```

## Next Steps

- [Architecture](./ARCHITECTURE.md) — internals and extension points
- [Configuration](./CONFIGURATION.md) — all config fields
- [How-Tos](./HOWTOS.md) — common recipes
