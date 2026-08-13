---
title: lexigram-ai-memory Troubleshooting
description: Common errors, causes, and fixes.
---

## `MemoryStoreError: Backend operation failed`

**Cause:** The underlying storage backend raised an error during `store()`, `retrieve()`, or `delete()`.

**Fix:** Check the backend connection. For custom backends, verify they implement `MemoryStoreProtocol` correctly:

```python
from lexigram.contracts.ai.memory import MemoryStoreProtocol

assert isinstance(backend, MemoryStoreProtocol)
```

**Exception:** `lexigram.ai.memory.exceptions.MemoryStoreError`

---

## `MemoryCapacityError: Memory store at capacity`

**Cause:** A backend with a fixed size limit is full and cannot accept new entries.

**Fix:** Prune old entries, increase capacity, or switch to a backend with higher capacity:

```python
from lexigram.ai.memory.exceptions import MemoryCapacityError

try:
    await store.store(entry)
except MemoryCapacityError as e:
    print(f"Store full (capacity: {e.capacity}), pruning old entries...")
    # Clear old entries
    await store.clear()
```

**Exception:** `lexigram.ai.memory.exceptions.MemoryCapacityError`

---

## `EmbeddingError`

**Cause:** Generating or storing a vector embedding for a memory entry failed. This typically occurs when using `VectorMemoryBackend` without a configured embedding service or when the embedding service is unavailable.

**Fix:** Ensure an embedding client is available and configured:

```python
# When using vector backends, verify EmbeddingClientProtocol is registered
```

**Exception:** `lexigram.ai.memory.exceptions.EmbeddingError`

---

## `FactExtractionError`

**Cause:** Entity/fact extraction from text during consolidation or semantic memory storage failed — usually due to malformed input or a downstream NLP service error.

**Fix:** Validate input text before storing. Ensure text has sufficient content for extraction.

**Exception:** `lexigram.ai.memory.exceptions.FactExtractionError`

---

## Consolidation scheduler not running

**Cause:** Either `enable_consolidation=False` was passed to `MemoryModule.configure()`, or `config.consolidation.enabled` is `False`.

**Fix:** Check both settings:

```python
from lexigram.ai.memory import MemoryModule, MemoryConfig

# Both must be True for consolidation to run
config = MemoryConfig()
config.consolidation.enabled = True

module = MemoryModule.configure(config, enable_consolidation=True)
```

---

## Working memory returns no entries

**Cause:** Token budget may be too low for the configured fractions, or no memory tiers have data.

**Fix:** Increase the token budget or add entries to episodic/semantic tiers before assembling:

```python
# Check budget allocation
from lexigram.ai.memory.config import WorkingMemoryConfig

config = WorkingMemoryConfig(
    system_prompt_tokens=256,  # reduce if budget is tight
    recent_turns_fraction=0.5,
    episodic_fraction=0.3,
    semantic_fraction=0.2,
)
```
