---
title: lexigram-ai-memory How-Tos
description: Task-oriented recipes for common memory patterns.
---

## How to store a memory entry

```python
from datetime import UTC, datetime
from lexigram.contracts.ai.memory import MemoryEntry

entry = MemoryEntry(
    id="mem-001",
    content="User requested a refund for order #1234.",
    role="assistant",
    timestamp=datetime.now(UTC),
    importance=0.7,
    metadata={"order_id": "1234", "type": "refund"},
)
await store.store(entry)
```

## How to retrieve relevant memories

```python
from lexigram.contracts.ai.memory import MemoryQuery

results = await store.retrieve(
    MemoryQuery(
        query="refund policy",
        top_k=5,
        min_relevance=0.3,
        filters={"type": "refund"},
    )
)
for match in results:
    print(f"[{match.score:.2f}] {match.entry.content}")
```

## How to use the episodic memory tier

```python
from datetime import UTC, datetime
from lexigram.contracts.ai.memory import MemoryEntry, MemoryQuery

# Record a conversation turn
await episodic.record(MemoryEntry(
    id="turn-5",
    content="User said they love the new feature.",
    role="assistant",
    timestamp=datetime.now(UTC),
    importance=0.6,
))

# Recall similar past episodes
past = await episodic.recall(MemoryQuery(
    query="feature feedback",
    top_k=3,
    recency_weight=0.4,
    relevance_weight=0.6,
))
```

## How to use the semantic memory tier

```python
# Store a fact
await semantic.store_fact(
    subject="customer_42",
    predicate="preferred_language",
    object_="Python",
    confidence=0.95,
)

# Query facts about an entity
facts = await semantic.query_facts("customer_42")
for fact in facts:
    print(f"{fact['predicate']} → {fact['object']}")

# Update confidence
await semantic.update_fact(fact_id="fact-1", confidence=0.8)
```

## How to assemble working memory context

```python
entries = await working.assemble(
    query="What did we discuss last time?",
    token_budget=4096,
)
for entry in entries:
    print(f"[{entry.role}] {entry.content}")
```

## How to switch backends

```python
from lexigram.ai.memory.config import MemoryConfig

# Use CacheMemoryBackend (requires CacheBackendProtocol)
config = MemoryConfig(default_backend="cache")

# Use DatabaseMemoryBackend (requires DatabaseProviderProtocol)
config = MemoryConfig(default_backend="database")

# Use VectorMemoryBackend (requires VectorStoreProtocol)
config = MemoryConfig(default_backend="vector")
```

## How to run consolidation manually

```python
from lexigram.contracts.ai.memory import MemoryEntry

entries = await store.get_recent(50)
result = await consolidator.consolidate(entries)
print(f"Processed: {result.entries_processed}")
print(f"Consolidated: {result.entries_consolidated}")
print(f"Pruned: {result.entries_pruned}")
print(f"Entities extracted: {result.entities_extracted}")
```

## How to use ConversationMemoryStore for session-scoped conversations

```python
from lexigram.ai.memory import ConversationMemoryStore
from lexigram.contracts.ai.memory import MemoryEntry, MemoryQuery
from datetime import UTC, datetime

store = ConversationMemoryStore(max_turns_per_session=1000)

# Store entries tagged with a session_id
await store.store(MemoryEntry(
    id="s1-1", content="Hello", role="user",
    timestamp=datetime.now(UTC), importance=0.5,
    metadata={"session_id": "session-abc"},
))
await store.store(MemoryEntry(
    id="s1-2", content="Hi! How can I help?", role="assistant",
    timestamp=datetime.now(UTC), importance=0.5,
    metadata={"session_id": "session-abc"},
))

# Retrieve entries for a specific session
results = await store.retrieve(MemoryQuery(
    query="greeting", top_k=10, filters={"session_id": "session-abc"},
))
for r in results:
    print(f"[{r.entry.role}] {r.entry.content}")

# Get full session history in chronological order
session = await store.get_session_entries("session-abc")
```

## How to use EntityMemoryStore for entity-scoped lookups

```python
from lexigram.ai.memory import EntityMemoryStore
from lexigram.contracts.ai.memory import MemoryEntry, MemoryQuery
from datetime import UTC, datetime

store = EntityMemoryStore()

# Store entries indexed by entity names
await store.store(
    MemoryEntry(id="e1", content="Alice prefers dark mode.", role="assistant",
                timestamp=datetime.now(UTC), importance=0.8),
    entities=["alice", "preferences"],
)
await store.store(
    MemoryEntry(id="e2", content="Alice's account is on the pro plan.", role="assistant",
                timestamp=datetime.now(UTC), importance=0.6),
    entities=["alice", "billing"],
)

# Look up all entries mentioning a specific entity
alice_entries = await store.get_by_entity("alice")
for entry in alice_entries:
    print(f"[{entry.importance}] {entry.content}")

# Retrieve scored by importance
results = await store.retrieve(MemoryQuery(
    query="alice", top_k=5,
))
```

## How to use SummaryMemoryStore with an LLM summariser

```python
from lexigram.ai.memory import SummaryMemoryStore
from lexigram.contracts.ai.memory import MemoryEntry, MemoryQuery
from datetime import UTC, datetime

async def llm_summarise(entries: list[MemoryEntry]) -> MemoryEntry:
    """Custom summariser — replace with your LLM call."""
    combined = " | ".join(e.content for e in entries)
    return MemoryEntry(
        id="summary-1",
        content=f"[LLM summary] {combined[:200]}",
        role="system",
        timestamp=datetime.now(UTC),
        importance=0.9,
        metadata={"compressed_ids": [e.id for e in entries], "type": "summary"},
    )

store = SummaryMemoryStore(
    compress_threshold=20,
    compress_batch=10,
    summarise_fn=llm_summarise,
)

# Store conversation turns — oldest batch is auto-compressed when threshold is hit
for i in range(25):
    await store.store(MemoryEntry(
        id=f"turn-{i}", content=f"Conversation turn {i}", role="user",
        timestamp=datetime.now(UTC), importance=0.5,
    ))

# Retrieval returns summaries first, then recent hot entries
results = await store.retrieve(MemoryQuery(query="conversation", top_k=5))
```

## How to prune context dynamically

```python
from lexigram.ai.memory.pruning import DynamicContextPruner

pruner = await app.container.resolve(DynamicContextPruner)
pruned = await pruner.prune(
    entries=recent_entries,
    max_tokens=2048,
    query="current discussion topic",
)
```
