---
title: lexigram-audit Troubleshooting
description: Common errors, causes, and fixes for lexigram-audit
sidebar:
  order: 6
---

## Audit Log Fails Silently

No exception raised — `log()` catches all exceptions internally.

**Cause:** By design. Audit failure must never block the triggering operation. `log()` emits a `WARNING` log instead.

**Fix:** Check application logs for `"audit.log_failed"` entries. If the store backend is unavailable, address the backend issue (database connection, table permissions, etc.).

**Exception:** None (fire-tolerant). The warning message is emitted via structlog.

---

## Query Returns Empty Results

`query()` returns `[]` instead of expected entries.

**Cause:** Either the store backend is unavailable (returns empty silently) or the filter criteria are too restrictive.

**Fix:** Check application logs for `"audit.query_failed"`. Verify query parameters against stored entries. Use fewer filter fields to narrow down the issue.

**Exception:** None (fire-tolerant). On error, `query()` logs a warning and returns `[]`.

---

## SQL Backend Not Available

```
ImportError: No module named 'lexigram.audit.store.sql'
```

**Cause:** The SQL backend requires `lexigram-audit[sql]` which adds `lexigram-sql` as a dependency. Without it, `AuditCoreProvider` falls back to `InMemoryAuditStore`.

**Fix:** Install the optional dependency:

```bash
uv add "lexigram-audit[sql]"
```

---

## Verification Returns No Mismatches

`verify_recent()` returns `[]` even after tampered data.

**Cause:** HMAC-based verification requires a configured `hmac_key`. Without it, verification is a no-op. Additionally, `AuditEntry` is a pure protocol type and does not carry a stored checksum field — full tamper detection requires the SQL backend which persists checksums in a column.

**Fix:** Set `hmac_key` in `AuditConfig`. Use the SQL backend for checksum storage. Verify checksums directly via `verify_audit_checksum()` for individual entries.

---

## Retention Policy Not Applied

Entries are not being purged.

**Cause:** `AuditPurger.purge_expired()` must be called explicitly (or scheduled). The module does not auto-purge.

**Fix:** Schedule periodic purges:

```python
from lexigram.audit import AuditPurger

# Called from a scheduled task or cron job
purger = await container.resolve(AuditPurger)
await purger.purge_expired()
```

---

## HMAC Key Not Set

```
Warning: hmac_key is None — checksum verification disabled
```

**Cause:** `AuditVerifierProtocol` is only registered when `hmac_key` is configured.

**Fix:** Set `hmac_key` in `AuditConfig`:

```yaml
audit:
  hmac_key: "c2VjdXJlLWhtYWMta2V5"
```

Or via module config:

```python
AuditModule.configure(hmac_key=b"my-key")
```

---

## Exception Reference

| Exception | Raised When |
|-----------|-------------|
| `AuditError` | Base for all audit domain errors |
| `AuditStoreError` | Store persistence or query fails unexpectedly (infrastructure) |
| `AuditVerificationError` | Verification encounters an unexpected failure |
| `AuditRetentionError` | Retention purge encounters an unexpected failure |

All audit exceptions inherit from `AuditError` → `DomainError`. They are infrastructure-level exceptions — domain operations should use `Result` types where applicable, but the audit logger itself is fire-tolerant and returns `None`/`[]` instead of `Result`.
