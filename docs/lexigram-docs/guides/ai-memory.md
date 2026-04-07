---
title: "AI Memory"
description: "Episodic, semantic, and working memory for intelligent agents."
---

`lexigram-ai-memory` provides a three-tier memory system for AI agents: **working memory** (the current context window), **episodic memory** (timestamped conversation history), and **semantic memory** (extracted facts and entities). A consolidation pipeline periodically promotes episodic entries into semantic knowledge.

For full configuration details, see the [`lexigram-ai-memory` package docs](/packages/lexigram-ai-memory/).

---

## 1. The Contracts

Each memory tier has its own protocol. All memory operations return `Result` for explicit error handling:

```python
from typing import Any, Protocol, runtime_checkable
from lexigram.contracts.ai.memory import (
    MemoryEntry, MemoryQuery, MemorySearchResult, ConsolidationResult,
)
from lexigram.contracts.core import HealthCheckResult


class MemoryStoreProtocol(Protocol):
    async def store(self, entry: MemoryEntry) -> None: ...
    async def retrieve(self, query: MemoryQuery) -> list[MemorySearchResult]: ...
    async def get_recent(self, n: int) -> list[MemoryEntry]: ...
    async def delete(self, entry_id: str) -> None: ...
    async def clear(self) -> None: ...
    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult: ...


class WorkingMemoryProtocol(Protocol):
    async def assemble(self, query: str, token_budget: int) -> list[MemoryEntry]: ...
    async def add(self, entry: MemoryEntry) -> None: ...
    async def get_context_entries(self) -> list[MemoryEntry]: ...
    async def flush(self) -> None: ...


class EpisodicMemoryProtocol(Protocol):
    async def record(self, entry: MemoryEntry) -> None: ...
    async def recall(self, query: MemoryQuery) -> list[MemorySearchResult]: ...
    async def forget(self, entry_id: str) -> None: ...
    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult: ...


class SemanticMemoryProtocol(Protocol):
    async def store_fact(
        self, subject: str, predicate: str, object_: str, confidence: float
    ) -> None: ...
    async def query_facts(self, subject: str) -> list[dict[str, Any]]: ...
    async def get_entity_facts(self, entity: str) -> list[dict[str, Any]]: ...


class MemoryConsolidatorProtocol(Protocol):
    async def consolidate(
        self, entries: list[MemoryEntry]
    ) -> ConsolidationResult: ...
```

`MemoryEntry` is the core data type:

```python
from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class MemoryEntry:
    id: str
    content: str
    role: str
    timestamp: datetime
    importance: float = 0.5
    metadata: dict[str, Any] = field(default_factory=dict)
    embedding: list[float] | None = None
```

---

## 2. Configuration

Add `MemoryModule` with the three-tier configuration:

```python
from lexigram import Application
from lexigram.ai.memory import MemoryModule, MemoryConfig

app = Application(name="my-app")
app.add_module(MemoryModule.configure(
    MemoryConfig(default_backend="vector", ttl_seconds=86400),
))
```

```yaml title="application.yaml"
ai_memory:
  enabled: true
  default_backend: vector
  ttl_seconds: 86400
  working:
    system_prompt_tokens: 1024
    recent_turns_fraction: 0.4
    episodic_fraction: 0.3
    semantic_fraction: 0.2
    tool_descriptions_fraction: 0.1
    max_recent_turns: 10
  episodic:
    default_top_k: 5
    recency_weight: 0.3
    importance_weight: 0.3
    relevance_weight: 0.4
    ttl_seconds: 604800
  semantic:
    min_confidence: 0.75
    max_facts_per_entity: 50
  consolidation:
    enabled: true
    interval_seconds: 3600
    age_threshold_hours: 24
    importance_prune_threshold: 0.2
    batch_size: 100
```

:::tip
Set `enable_consolidation=False` in `MemoryModule.configure()` to disable background consolidation. This is useful during testing.
:::

---

## 3. Working Memory

Working memory assembles the context window for each LLM call, fitting entries from episodic and semantic memory within a token budget:

```python
from lexigram.contracts.ai.memory import (
    WorkingMemoryProtocol,
    MemoryEntry,
)
from datetime import datetime, UTC


async def add_turn(working: WorkingMemoryProtocol, user_msg: str, assistant_msg: str) -> None:
    await working.add(
        MemoryEntry(
            id="turn-1",
            content=user_msg,
            role="user",
            timestamp=datetime.now(UTC),
        )
    )
    await working.add(
        MemoryEntry(
            id="turn-2",
            content=assistant_msg,
            role="assistant",
            timestamp=datetime.now(UTC),
        )
    )

    context = await working.assemble(query=user_msg, token_budget=4096)
    for entry in context:
        print(f"[{entry.role}] {entry.content[:50]}...")
```

The `TokenBudgetAllocator` divides the budget across recent turns, episodic recall, semantic facts, and tool descriptions according to the fractions in `WorkingMemoryConfig`.

---

## 4. Episodic Memory

Episodic memory stores timestamped conversation turns and retrieves them by recency and relevance:

```python
from lexigram.contracts.ai.memory import EpisodicMemoryProtocol, MemoryQuery


async def recall_recent(episodic: EpisodicMemoryProtocol, query: str) -> None:
    results = await episodic.recall(
        MemoryQuery(
            query=query,
            top_k=5,
            recency_weight=0.3,
            relevance_weight=0.4,
            importance_weight=0.3,
        )
    )
    for result in results:
        entry = result.entry
        print(f"  [{entry.timestamp}] {entry.role}: {entry.content[:60]}... (score: {result.score:.2f})")
```

Episodic entries have a configurable TTL. Expired entries are pruned during consolidation.

---

## 5. Semantic Memory

Semantic memory stores extracted facts as subject-predicate-object triples:

```python
from lexigram.contracts.ai.memory import SemanticMemoryProtocol


async def store_and_query(semantic: SemanticMemoryProtocol) -> None:
    await semantic.store_fact(
        subject="Alice",
        predicate="works_at",
        object_="Acme Corp",
        confidence=0.95,
    )
    await semantic.store_fact(
        subject="Alice",
        predicate="role",
        object_="Engineer",
        confidence=0.90,
    )

    facts = await semantic.query_facts("Alice")
    for fact in facts:
        print(f"{fact['subject']} {fact['predicate']} {fact['object_']} ({fact['confidence']})")
```

---

## 6. Consolidation

The consolidation pipeline moves episodic into semantic storage:

```python
from lexigram.contracts.ai.memory import MemoryConsolidatorProtocol


async def run_consolidation(consolidator: MemoryConsolidatorProtocol, entries: list) -> None:
    result = await consolidator.consolidate(entries)
    print(f"Processed: {result.entries_processed}")
```
---

## 7. Testing

Use `MemoryModule.stub()` for isolated tests:

```python
from lexigram import Application
from lexigram.ai.memory import MemoryModule
from lexigram.contracts.ai.memory import (
    MemoryStoreProtocol,
    EpisodicMemoryProtocol,
    SemanticMemoryProtocol,
    WorkingMemoryProtocol,
    MemoryEntry,
)
from datetime import datetime, UTC


async def test_memory_store() -> None:
    async with Application.boot(modules=[MemoryModule.stub()]) as app:
        store = await app.container.resolve(MemoryStoreProtocol)
        entry = MemoryEntry(
            id="test-1",
            content="Hello world",
            role="user",
            timestamp=datetime.now(UTC),
        )
        await store.store(entry)
        recent = await store.get_recent(5)
        assert len(recent) == 1
        assert recent[0].content == "Hello world"
```

:::note
The stub uses in-memory backends with consolidation disabled.
:::

## Next Steps

- [AI Agents](/guides/ai-agents/) — memory-backed conversations
- [AI Sessions](/guides/ai-sessions/) — session lifecycle with checkpointing
- [Dependency Injection](/fundamentals/dependency-injection/) — binding memory protocols in the container
- [Vector Stores](/guides/vector-stores/) — vector backends for memory
