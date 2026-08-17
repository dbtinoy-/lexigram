---
title: lexigram-ai-session Guide
description: Core concepts, common workflows, and best practices for AI conversation sessions.
sidebar:
  order: 2
---

## Requirements

| Package | Required | Purpose |
|---------|----------|---------|
| `lexigram` | Yes | Core framework |
| `lexigram-contracts` | Yes | Protocol definitions |
| `lexigram-cache` | Optional | Persistent session store |
| `lexigram-sql` | Optional | Database session store |

## Problem

AI conversations are stateful — each turn depends on previous turns. A session might need to be paused and resumed, forked into alternative branches, restored from a checkpoint, or shared across multiple agents. **lexigram-ai-session** provides the infrastructure for managing conversation state throughout its lifecycle — creation, turns, checkpointing, branching, context pruning, and multi-agent coordination.

## Mental model

Think of a session like a **document with version history**:

1. **Create a session** (open a new document)
2. **Add turns** (append paragraphs — each turn records role, content, tokens)
3. **Checkpoint** (save a snapshot you can restore to later)
4. **Branch** (fork the session to explore alternatives)
5. **Suspend / resume** (pause work and come back)
6. **Close** (finalize the document)

The session manager is the editor that orchestrates these operations, the session store is the file system that persists them.

## Core concepts

### Session lifecycle

A session moves through four states defined by `SessionStatus`:

```
ACTIVE → SUSPENDED → ACTIVE → CLOSED / EXPIRED
```

- **ACTIVE** — accepting turns
- **SUSPENDED** — paused, can be resumed
- **CLOSED** — terminated, no more modifications
- **EXPIRED** — TTL exceeded, automatically closed

### SessionManagerProtocol

The primary entrypoint is `SessionManagerProtocol` from `lexigram.contracts.ai.session`. The default implementation is `SessionManagerImpl`.

```python
from lexigram.ai.session import SessionManagerImpl
from lexigram.ai.session import SessionConfig, InMemorySessionStore

config = SessionConfig()
store = InMemorySessionStore()
manager = SessionManagerImpl(config=config, store=store)

# Create session
state = await manager.create(user_id="user-42", metadata={"topic": "support"})

# Add turn
from lexigram.contracts.ai.session import SessionTurn
from datetime import datetime, UTC

turn = SessionTurn(
    turn_id="turn-1",
    role="user",
    content="Hello!",
    timestamp=datetime.now(UTC),
)
await manager.add_turn(state.session_id, turn)

# Checkpoint
checkpoint = await manager.checkpoint(state.session_id)

# Suspend
suspended = await manager.suspend(state.session_id)

# Resume
resumed = await manager.resume(state.session_id)

# Close
await manager.close(state.session_id)
```

### SessionStoreProtocol

Sessions are persisted through `SessionStoreProtocol`. Three backends:

| Backend | Class | Use case |
|---|---|---|
| In-memory | `InMemorySessionStore` | Testing, single-process dev |
| Cache | `CacheSessionStore` | Distributed, ephemeral (Redis) |
| Database | `DatabaseSessionStore` | Production persistence (Postgres) |

```python
from lexigram.ai.session.stores.in_memory import InMemorySessionStore
from lexigram.ai.session import CacheSessionStore, DatabaseSessionStore

store = InMemorySessionStore()
await store.save(state)
loaded = await store.load(session_id)
await store.list_sessions(user_id)
await store.delete(session_id)
```

### Checkpointing

Checkpoints are immutable snapshots of `SessionState`. They enable restore and branching.

```python
# Create a checkpoint
cp = await manager.checkpoint(session_id)

# Restore from checkpoint
restored = await manager.restore(cp.checkpoint_id)

# Auto-checkpointing
# Enabled via config: auto_checkpoint_interval=10
# Creates a checkpoint every N turns
```

### Branching

Branching forks a session to explore alternative conversation paths. The `BranchManager` handles creating and managing branches.

```python
from lexigram.ai.session import BranchManager

branch_mgr = BranchManager(store=store, manager=manager)
branch = await branch_mgr.create_branch(state.session_id, name="alt-approach")
```

Branches can be merged back with merge strategies:

```python
from lexigram.ai.session import AppendMerge, SelectiveMerge

append = AppendMerge()
merged = await append.merge(source_session_id, target_session_id)
```

### Multi-agent group sessions

Multiple agents can participate in the same session with role isolation and turn management strategies.

```python
from lexigram.ai.session import GroupSession, RoundRobinTurnManager

turn_mgr = RoundRobinTurnManager()
session = GroupSession(
    session_id=state.session_id,
    turn_manager=turn_mgr,
)

await session.add_agent(agent_a, role="researcher")
await session.add_agent(agent_b, role="writer")
await session.tick()  # next agent's turn
```

Available turn managers:

| Manager | Strategy |
|---|---|
| `RoundRobinTurnManager` | Agents take turns in fixed order |
| `PriorityTurnManager` | Higher-priority agents go first |
| `TopicBasedTurnManager` | Turn assigned based on topic relevance |

### Context management

`SessionContext` provides per-request session binding using `ContextVar`:

```python
from lexigram.ai.session import SessionContext

ctx = SessionContext()
await ctx.bind(session_id)
current = ctx.session_id
```

`RelevanceContextPruner` intelligently prunes conversation history by scoring turn relevance instead of naive sliding-window truncation.

```python
from lexigram.ai.session import RelevanceContextPruner

pruner = RelevanceContextPruner()
pruned = await pruner.prune(history, current_query, max_turns=20)
```

### Web middleware

The `SessionMiddleware` extracts and binds session IDs from HTTP requests via cookie or header:

```python
from lexigram.ai.session import SessionMiddleware
```

Configured with `cookie_name` and `header_name` in `SessionConfig`.

### Analytics

`SessionAnalytics` tracks session metrics — active counts, average turns, checkpoint rates, cost accumulation:

```python
from lexigram.ai.session import SessionAnalytics

analytics = SessionAnalytics(store=store)
stats = await analytics.get_session_stats(user_id="user-42")
```

## Best practices

- **Use `database` backend for production** — `in_memory` is for development only
- **Enable auto-checkpointing** for long-running sessions to prevent data loss
- **Set a reasonable `session_ttl`** — 24 hours (86400s) is the default; adjust per use case
- **Use `SessionModule.stub()` in tests** — provides in-memory store with cleanup disabled
- **Handle session exceptions explicitly** — catch `SessionNotFoundError`, `SessionClosedError`, `SessionCapacityError`
- **Choose the right turn strategy** — `round_robin` for balanced teams, `priority` for lead-agent patterns

## Next steps

- [Architecture](/packages/lexigram-ai-session/architecture/) — provider lifecycle, module mapping, extension points
- [Configuration](/packages/lexigram-ai-session/configuration/) — full config reference
- [How-tos](/packages/lexigram-ai-session/howtos/) — task-oriented recipes
- [Troubleshooting](/packages/lexigram-ai-session/troubleshooting/) — common errors and fixes
