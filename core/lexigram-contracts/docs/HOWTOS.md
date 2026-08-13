---
title: "lexigram-contracts How-Tos"
description: "Practical how-to guides for defining protocols, adding types, and creating exceptions in lexigram-contracts."
---
# How-To Guides

---

## Define a Protocol

Create a `Protocol` class with `@runtime_checkable` in the appropriate domain module:

```python
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class DocumentIndexProtocol(Protocol):
    """Interface for document indexing backends."""

    async def index(self, doc_id: str, content: str) -> None:
        ...

    async def search(self, query: str, top_k: int = 10) -> list[str]:
        ...

    async def delete(self, doc_id: str) -> None:
        ...
```

Place it in the correct domain directory under `lexigram/contracts/` (e.g. `data/index/protocols.py`).

---

## Create a Shared Value Type

If a dataclass appears in a protocol method signature, it belongs in contracts:

```python
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class IndexingStatus(str, Enum):
    PENDING = "pending"
    INDEXING = "indexing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class IndexingResult:
    doc_id: str
    status: IndexingStatus
    error: str | None = None
    chunks_indexed: int = 0
```

Use `@dataclass(frozen=True)` for value types that cross package boundaries.

---

## Add a Domain Exception

Add the **base exception** in contracts, then extend it in the extension package:

```python
# lexigram-contracts/src/lexigram/contracts/ai/exceptions.py
class AIMemoryError(AIError):
    """Base for AI memory system errors. Extended in lexigram-ai-memory."""


# lexigram-ai-memory/exceptions.py
from lexigram.contracts.ai.exceptions import AIMemoryError


class MemoryCapacityExceededError(AIMemoryError):
    """Raised when memory storage exceeds configured capacity."""


class MemoryConsolidationError(AIMemoryError):
    """Raised when memory consolidation fails."""
```

---

## Register a New Config Section

If an extension package needs a config section, define its model and register it with `ConfigRegistry`:

```python
from __future__ import annotations

from dataclasses import dataclass
from lexigram.config import LexigramConfig


@dataclass
class IndexConfig:
    host: str = "localhost"
    port: int = 9200
    timeout: int = 30


config = LexigramConfig.from_yaml("application.yaml")
index_cfg = config.get_section("index", IndexConfig)
# Reads from YAML (index.host). Custom sections are YAML-only; env
# overrides apply to built-in sections, e.g. LEX_LOGGING__LEVEL.
```

---

## Use a Protocol from Contracts in Your Service

```python
from __future__ import annotations

from lexigram.contracts.infra.cache import CacheBackendProtocol
from lexigram.contracts.data import DatabaseProviderProtocol


class UserService:
    def __init__(
        self,
        db: DatabaseProviderProtocol,
        cache: CacheBackendProtocol | None = None,
    ) -> None:
        self.db = db
        self.cache = cache

    async def get_user(self, user_id: str) -> dict | None:
        if self.cache:
            cached = await self.cache.get(f"user:{user_id}")
            if cached:
                return {"id": user_id, "data": cached}
        return await self.db.query("SELECT * FROM users WHERE id = ?", [user_id])
```

---

## Create an Enum for Cross-Package Use

```python
from __future__ import annotations

from enum import Enum


class SyncStrategy(str, Enum):
    FULL = "full"
    INCREMENTAL = "incremental"
    BATCH = "batch"
```

Place it alongside the protocol or type file that uses it. Use `str, Enum` so values are JSON-serializable.

---

## Re-export from Contracts (Ergonomic Imports)

When a type lives deep in the module tree, create a re-export for cleaner import paths:

```python
# lexigram/contracts/ai/vector.py
"""Re-exports from data/vector/ for ergonomic AI imports."""

from lexigram.contracts.data.vector.protocols import (
    VectorStoreProtocol as VectorStoreProtocol,
)

__all__ = ["VectorStoreProtocol"]
```

Re-exports must be **simple aliases** — no added logic or modified signatures.

---

## Catch a Base Exception Without Importing the Extension

```python
from __future__ import annotations

from lexigram.contracts.ai.exceptions import AIError


async def call_llm() -> None:
    try:
        result = await llm_client.complete(prompt)
    except AIError as e:
        # Catches LLMError, RAGError, MemoryError, SkillError, etc.
        # without importing any specific extension package
        log_error(f"AI subsystem failed: {e}")
```
