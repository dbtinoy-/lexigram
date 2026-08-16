---
title: lexigram-audit How-Tos
description: Common recipes for lexigram-audit
sidebar:
  order: 5
---

## Record a User Login Event

```python
from lexigram.contracts.audit import AuditEntry, AuditEventSeverity, AuditLoggerProtocol

logger = await container.resolve(AuditLoggerProtocol)
await logger.log(AuditEntry(
    action="user.login",
    actor_id="user-42",
    severity=AuditEventSeverity.HIGH,
    metadata={"ip": "10.0.0.1", "user_agent": "Mozilla/..."},
))
```

## Record a Resource Mutation with Old/New Values

```python
await logger.log(AuditEntry(
    action="user.update",
    actor_id="admin-1",
    resource_type="User",
    resource_id="user-99",
    outcome="success",
    severity=AuditEventSeverity.MEDIUM,
    old_values={"email": "old@example.com", "role": "viewer"},
    new_values={"email": "new@example.com", "role": "editor"},
    source="sql",
))
```

## Query Recent Entries for an Actor

```python
from lexigram.contracts.audit import AuditQuery

entries = await logger.query(AuditQuery(
    actor_id="user-42",
    limit=20,
))
for entry in entries:
    print(f"{entry.occurred_at}: {entry.action} ({entry.outcome})")
```

## Verify Audit Trail Integrity

```python
from lexigram.audit import compute_audit_checksum, verify_audit_checksum

entry_data = {
    "action": "user.create",
    "actor_id": "admin-1",
    "occurred_at": "2026-01-01T00:00:00Z",
}
key = b"my-hmac-key"

checksum = compute_audit_checksum(entry_data, key)
# Store checksum alongside the entry...

# Later: verify
is_valid = verify_audit_checksum(entry_data, key, checksum)
```

## Purge Expired Entries

```python
from lexigram.audit import AuditPurger
from lexigram.contracts.audit import RetentionPolicyProtocol

purger = await container.resolve(AuditPurger)
count = await purger.purge_expired()
print(f"Purged {count} expired entries")
```

## Configure a Custom Retention Policy

```python
from lexigram.contracts.audit import RetentionPolicy

policy = RetentionPolicy(
    name="hipaa",
    default_retention_days=2555,  # 7 years
    severity_overrides={
        "critical": 2555,
        "high": 2555,
    },
    source_overrides={
        "billing": 2190,  # 6 years
    },
)
```

## Use In-Memory Backend for Tests

```python
from lexigram.audit import AuditBundleProvider, AuditConfig

config = AuditConfig(store_backend="memory")
provider = AuditBundleProvider(config=config)
# Use in your test Application.boot(...)
```

## How do I auto-log audit events with a decorator?

```python
from lexigram.audit.decorators import audited

# Decorate an async function — audit metadata is attached automatically
@audited("user.update", resource_type="User", severity="medium")
async def update_user(self, user_id: str, data: dict) -> User:
    return await self.repo.update(user_id, data)

# Audit middleware reads __audited__ attributes from the function
# and records an AuditEntry on successful execution
```

## How do I schedule periodic audit trail verification?

```python
from lexigram.audit import AuditVerifier, AuditConfig
from lexigram.audit.scheduling.scheduler import AuditScheduler
from lexigram.contracts.audit import AuditVerifierProtocol
from lexigram.contracts.observability.audit import (
    AuditVerifierSchedulerProtocol,
)

# Manual construction (without a container)
config = AuditConfig(
    hmac_key=b"my-hmac-key",
    verification_schedule="0 */6 * * *",   # every 6 hours
    verification_batch_size=500,
)

verifier: AuditVerifier  # resolved from container
scheduler = AuditScheduler(verifier=verifier, config=config)

# Register the handler with a task provider (e.g. from lexigram-tasks)
scheduler.register_handler(task_provider)

# Or schedule the periodic job
job_id = scheduler.schedule(task_provider)
```

## How do I subscribe to audit domain events?

```python
from lexigram.audit.events import (
    AuditEntryLoggedEvent,
    AuditPurgeCompletedEvent,
    AuditVerificationCompletedEvent,
)
from lexigram.contracts.events.protocols import EventBusProtocol

bus: EventBusProtocol  # resolved from container

async def on_entry_logged(event: AuditEntryLoggedEvent) -> None:
    notify_security_team(event.action, event.actor_id)

async def on_purge_completed(event: AuditPurgeCompletedEvent) -> None:
    log_purge(event.entries_purged, event.entries_archived)

async def on_verification_completed(
    event: AuditVerificationCompletedEvent,
) -> None:
    if event.mismatches_found > 0:
        alert_tamper_detected(event.mismatches_found)

bus.subscribe(AuditEntryLoggedEvent, on_entry_logged)
bus.subscribe(AuditPurgeCompletedEvent, on_purge_completed)
bus.subscribe(AuditVerificationCompletedEvent, on_verification_completed)
```

## Wire Audit via Module

```python
from lexigram import Application
from lexigram.audit import AuditModule

app = Application(name="my-app")
app.add_module(AuditModule.configure(
    store_backend="sql",
    hmac_key=b"my-key",
    retention_days=365,
))
```
