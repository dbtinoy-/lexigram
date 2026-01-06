# lexigram-contracts

Core types and protocols for the Lexigram Framework.

---

## Overview

`lexigram-contracts` defines all Protocols, base types, Result types, domain
models, and exception hierarchies used across the Lexigram ecosystem. It has
**zero runtime dependencies** so it can be imported into any package — including
thin integrations — without pulling in the full framework.

This package is the single source of truth for every interface in Lexigram.
All other packages depend on contracts; no implementation package defines its
own protocol that another package depends on.


> Full documentation: [docs.lexigram.dev](https://docs.lexigram.dev)
## Install

```bash
uv add lexigram-contracts
```

## Quick Start

### Result type

```python
from lexigram.result import Result, Ok, Err

async def find_user(user_id: str) -> Result[User, UserNotFound]:
    user = await db.get(user_id)
    if not user:
        return Err(UserNotFound(user_id))
    return Ok(user)

# Safe consumption
result = await find_user("u-123")
name = result.match(ok=lambda u: u.name, err=lambda e: "unknown")
```

### Domain models

```python
from lexigram.contracts.domain.base import Entity, ValueObject
from lexigram.contracts.domain.aggregates import AggregateRoot
from lexigram.contracts.domain.events import DomainEvent

class UserCreated(DomainEvent):
    user_id: str
    email: str

class User(AggregateRoot):
    email: str
```

### Protocols

```python
from lexigram.contracts.cache import CacheBackend
from lexigram.contracts.data import DatabaseProviderProtocol
from lexigram.contracts.security.secrets import SecretStoreProtocol
```

## Key Modules

| Module | What it contains |
|--------|-----------------|
| `lexigram.result` | `Result[T, E]`, `Ok`, `Err`, `ok()`, `err()` |
| `lexigram.contracts.core.container` | ContainerRegistrarImpl, ContainerResolverImpl |
| `lexigram.contracts.core.provider` | Provider, ProviderPriority |
| `lexigram.contracts.core.registry` | Registry for type-keyed dispatch |
| `lexigram.contracts.domain.base` | Entity, ValueObject |
| `lexigram.contracts.domain.aggregates` | AggregateRoot |
| `lexigram.contracts.domain.events` | DomainEvent |
| `lexigram.contracts.cache` | CacheBackend protocol |
| `lexigram.contracts.data` | DatabaseProviderProtocol |
| `lexigram.contracts.security.secrets` | SecretStoreProtocol |
| `lexigram.contracts.exceptions` | LexigramError, full error hierarchy |

## Key Source Files

| File | What it contains |
|------|-----------------|
| `src/lexigram/contracts/__init__.py` | Lazy-loading re-exports of all public types |
| `src/lexigram/result/` | Result type and Ok/Err helpers |
| `src/lexigram/contracts/domain/` | Entity, ValueObject, AggregateRoot, DomainEvent |
| `src/lexigram/contracts/core/` | Container, Provider, Registry protocols |
| `src/lexigram/contracts/exceptions/` | LexigramError and domain error hierarchies |

## Design Principles

- **Zero dependencies** — no third-party runtime imports
- **Protocol-only** — defines interfaces, never implementations
- **Stable contract** — all other Lexigram packages depend on this one; breaking changes are versioned
