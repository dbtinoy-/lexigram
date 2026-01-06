---
title: lexigram-audit Quickstart
description: Get started with lexigram-audit — append-only, HMAC-verified audit trails
sidebar:
  order: 1
---

Install, wire, and record audit events in under 5 minutes.

## Install

```bash
uv add lexigram-audit
```

For the SQL backend (recommended for production):

```bash
uv add "lexigram-audit[sql]"
```

## Minimal Wiring (Memory Backend)

```python
import asyncio
from lexigram import Application
from lexigram.audit import AuditBundleProvider, AuditConfig

config = AuditConfig(store_backend="memory")
provider = AuditBundleProvider(config=config)

async def main() -> None:
    async with Application.boot(
        name="demo",
        providers=[provider],
        config=config,
    ) as app:
        print("Audit provider ready")

asyncio.run(main())
```

## Record and Query an Audit Entry

```python
import asyncio
from datetime import UTC, datetime
from lexigram import Application
from lexigram.audit import AuditBundleProvider, AuditConfig
from lexigram.contracts.audit import (
    AuditEntry, AuditQuery, AuditEventSeverity, AuditLoggerProtocol,
)

config = AuditConfig(store_backend="memory")
provider = AuditBundleProvider(config=config)

async def main() -> None:
    async with Application.boot(
        name="demo",
        providers=[provider],
        config=config,
    ) as app:
        logger = await app.resolve(AuditLoggerProtocol)

        await logger.log(AuditEntry(
            action="user.login",
            actor_id="user-42",
            severity=AuditEventSeverity.HIGH,
            metadata={"ip": "10.0.0.1"},
        ))

        results = await logger.query(AuditQuery(actor_id="user-42", limit=10))
        print(f"Found {len(results)} entries")

asyncio.run(main())
```

## Next Steps

- [Guide](./GUIDE.md) — concepts and mental model
- [Configuration](./CONFIGURATION.md) — all config fields
- [How-Tos](./HOWTOS.md) — common recipes
