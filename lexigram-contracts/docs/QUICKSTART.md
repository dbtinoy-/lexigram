---
title: "lexigram-contracts Quickstart"
description: "Get started with lexigram-contracts — the zero-dependency protocol layer shared by every Lexigram package."
---
# Quickstart

Get started with `lexigram-contracts` — the zero-dependency protocol layer shared by every Lexigram package.

:::caution[Alpha]
`lexigram-contracts` is **alpha (0.1.x)** — public APIs may change before 1.0.
:::

---

## Install

`lexigram-contracts` is installed automatically as a dependency of `lexigram`. Install it directly only if you need the protocols without the full framework:

```bash
uv add lexigram-contracts
# or
pip install lexigram-contracts
```

Zero dependencies — just Python 3.11+.

---

## Minimal Example

Import and use a protocol:

```python
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class MyServiceProtocol(Protocol):
    async def execute(self, command: str) -> bytes: ...


# Use a contracts protocol
from lexigram.contracts.infra.cache import CacheBackendProtocol


class InMemoryCache:
    """Minimal in-memory implementation of CacheBackendProtocol."""

    def __init__(self) -> None:
        self._store: dict[str, bytes] = {}

    async def get(self, key: str) -> bytes | None:
        return self._store.get(key)

    async def set(self, key: str, value: bytes, ttl: int) -> None:
        self._store[key] = value


cache: CacheBackendProtocol = InMemoryCache()
```

---

## What Just Happened

| Step | Description |
|------|-------------|
| `from lexigram.contracts.infra.cache import ...` | Imported a protocol from the contracts layer |
| `InMemoryCache` | Implemented the protocol structurally (no explicit inheritance needed) |
| `cache: CacheBackendProtocol` | Used the protocol as a type annotation — the container will enforce conformance |

---

## Next Steps

- [Guide](./GUIDE.md) — what contracts are, the zero-dependency rule, mental model
- [Architecture](./ARCHITECTURE.md) — domain organization, protocol placement, exception hierarchy
- [How-Tos](./HOWTOS.md) — define a protocol, create shared types, add domain exceptions
