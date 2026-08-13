---
title: lexigram-ai-memory Guide
description: Mental model, core concepts, and end-to-end usage of the three-tier memory system.
---

## Requirements

| Package | Required | Purpose |
|---------|----------|---------|
| `lexigram` | Yes | Core framework |
| `lexigram-contracts` | Yes | Protocol definitions |
| `lexigram-ai-llm` | Optional | Summary memory |
| `lexigram-vector` | Optional | Semantic memory |

## Problem & Mental Model

LLM conversations are stateless — each call is independent. AI systems need **memory** to remember past interactions, learn from experience, and manage limited context windows. lexigram-ai-memory provides three tiers:

| Tier | What it stores | Retention | Analogy |
|------|---------------|-----------|---------|
| **Working** | Current conversation context | Single request | Scratchpad |
| **Episodic** | Past conversations, events | Hours–days | Diary |
| **Semantic** | Extracted facts, entities | Days–forever | Encyclopedia |

Memory entries are stored with **importance** and **temporal** metadata, enabling hybrid scoring (recency + relevance + importance) during retrieval.

## Core Concepts

### Memory Entry

Every piece of memory is a `MemoryEntry`:

```python
from lexigram.contracts.ai.memory import MemoryEntry
from datetime import UTC, datetime

entry = MemoryEntry(
    id="entry-123",
    content="User prefers dark mode.",
    role="assistant",
    timestamp=datetime.now(UTC),
    importance=0.8,                       # 0.0–1.0
    metadata={"source": "preferences"},
)
```

### Working Memory

Working memory assembles the context window for the current request. It allocates a token budget across system prompt, recent turns, episodic recall, and semantic facts:

```python
from lexigram.ai.memory.working import WorkingMemoryManager
from lexigram.ai.memory.config import WorkingMemoryConfig

config = WorkingMemoryConfig(
    system_prompt_tokens=512,
    recent_turns_fraction=0.4,
    episodic_fraction=0.3,
    semantic_fraction=0.2,
    max_recent_turns=20,
)
```

### Episodic Memory

Episodic memory stores timestamped conversation history with hybrid retrieval:

- **Recency** — how recent the entry is
- **Relevance** — semantic similarity to the query
- **Importance** — how important the entry was marked

```python
from lexigram.contracts.ai.memory import MemoryQuery

results = await episodic.recall(
    MemoryQuery(
        query="previous booking",
        top_k=5,
        recency_weight=0.3,
        relevance_weight=0.5,
        importance_weight=0.2,
    )
)
```

### Semantic Memory

Semantic memory stores facts as subject-predicate-object triples with confidence scores:

```python
await semantic.store_fact(
    subject="Alice",
    predicate="prefers",
    object_="dark_mode",
    confidence=0.95,
)

facts = await semantic.query_facts("Alice")
```

### Consolidation

The consolidation pipeline periodically promotes important episodic memories into semantic storage, deduplicates, prunes low-importance entries, and extracts entities:

```python
from lexigram.ai.memory.consolidation import (
    MemoryConsolidator,
    ConsolidationScheduler,
)
```

Scheduling is configured via `ConsolidationConfig` and activated through `MemoryProvider.boot()`.

## Typical Usage

### Full setup with all tiers

```python
from lexigram import Application
from lexigram.ai.memory import MemoryModule, MemoryConfig

config = MemoryConfig(
    default_backend="in_memory",
    ttl_seconds=86400 * 30,
)

async with Application.boot(
    name="app",
    modules=[MemoryModule.configure(config, enable_consolidation=True)],
) as app:
    # Resolve individual tiers
    working = await app.container.resolve(WorkingMemoryProtocol)
    episodic = await app.container.resolve(EpisodicMemoryProtocol)
    semantic = await app.container.resolve(SemanticMemoryProtocol)
    store = await app.container.resolve(MemoryStoreProtocol)
    consolidator = await app.container.resolve(MemoryConsolidatorProtocol)
```

### Assembling context for an LLM

```python
from datetime import UTC, datetime

# Store conversation turns
await episodic.record(MemoryEntry(
    id="turn-1", content="User: Hello", role="user",
    timestamp=datetime.now(UTC), importance=0.5,
))

# Assemble context for the next LLM call
entries = await working.assemble(
    query="What was my last question?",
    token_budget=4096,
)
for entry in entries:
    print(f"[{entry.role}] {entry.content}")
```

### Multi-source retrieval

```python
from lexigram.ai.memory.retrieval import MemoryRetriever

retriever = await app.container.resolve(MemoryRetriever)
results = await retriever.retrieve(
    MemoryQuery(query="user preferences", top_k=10),
)
for r in results:
    print(f"[{r.source}] {r.entry.content} (score: {r.score:.2f})")
```

### Dynamic context pruning

```python
from lexigram.ai.memory.pruning import DynamicContextPruner

pruner = await app.container.resolve(DynamicContextPruner)
pruned = await pruner.prune(
    entries=all_entries,
    max_tokens=2048,
    query="current topic",
)
```

## Result Handling

`MemoryStoreProtocol` methods are fire-and-forget (`None` return) or return lists directly — they do not use `Result` for expected operations. Exceptions (`MemoryStoreError`, `MemoryCapacityError`) are raised for infrastructure failures.

## Next Steps

- [How-Tos](./HOWTOS.md) — recipes for backends, pruning, consolidation
- [Architecture](./ARCHITECTURE.md) — internal design and extension points
- [API Reference](./API.md) — full API docs
