---
title: lexigram-ai-session How-tos
description: Task-oriented recipes for common session operations.
sidebar:
  order: 5
---

## Create and interact with a session

```python
from lexigram.ai.session import SessionManagerImpl
from lexigram.ai.session import SessionConfig, InMemorySessionStore
from lexigram.contracts.ai.session import SessionTurn
from datetime import datetime, UTC

store = InMemorySessionStore()
manager = SessionManagerImpl(config=SessionConfig(), store=store)

state = await manager.create(user_id="user-42", metadata={"topic": "support"})

turn = SessionTurn(
    turn_id="t1", role="user", content="Hello!",
    timestamp=datetime.now(UTC),
)
await manager.add_turn(state.session_id, turn)

latest = await manager.get_state(state.session_id)
print(f"Turn count: {latest.turn_count}")
```

## Checkpoint and restore

```python
state = await manager.create(user_id="user-42")

# After some turns, create a checkpoint
await manager.add_turn(state.session_id, turn_1)
await manager.add_turn(state.session_id, turn_2)
cp = await manager.checkpoint(state.session_id)

# Add more turns
await manager.add_turn(state.session_id, turn_3)

# Restore to the checkpoint
restored = await manager.restore(cp.checkpoint_id)
assert len(restored.turns) == 2  # turn_3 is gone
```

## Branch a session

```python
from lexigram.ai.session import BranchManager

branch_mgr = BranchManager(store=store, manager=manager)
branch = await branch_mgr.create_branch(
    state.session_id,
    name="what-if-scenario",
)

# Branch is a new session with the same history up to the branch point
branch_state = await manager.get_state(branch.session_id)
print(f"Branch: {branch_state.branch_name}")
```

## Merge branches

```python
from lexigram.ai.session import AppendMerge

merge = AppendMerge()
merged = await merge.merge(branch_id, original_session_id)
```

## Set up a multi-agent group session

```python
from lexigram.ai.session import GroupSession, RoundRobinTurnManager

turn_mgr = RoundRobinTurnManager()
session = GroupSession(
    session_id=state.session_id,
    turn_manager=turn_mgr,
)

await session.add_agent(researcher_agent, role="researcher")
await session.add_agent(writer_agent, role="writer")

# Cycle through agents
await session.tick()  # researcher's turn
await session.tick()  # writer's turn
```

## Use the SessionModule with a custom config

```python
from lexigram import Application, LexigramConfig
from lexigram.ai.session import SessionModule
from lexigram.ai.session import SessionConfig

config = LexigramConfig.from_yaml()
app = Application(name="my-app", config=config)
app.add_module(SessionModule.configure(
    SessionConfig(backend="cache", session_ttl=3600),
    enable_cleanup_scheduler=True,
))
```

## Set up session middleware for web apps

```python
from lexigram.ai.session import SessionMiddleware
```

Configure via `SessionConfig`:

```yaml
ai_session:
  cookie_name: lexigram_session
  header_name: X-Session-ID
```

The middleware extracts the session ID from request headers or cookies and binds it to the current context via `SessionContext`.

## Prune conversation history by relevance

```python
from lexigram.ai.session import RelevanceContextPruner

pruner = RelevanceContextPruner()
pruned = await pruner.prune(
    history=full_history,
    current_query="What was the price?",
    max_turns=20,
)
```

## Use the session state machine

```python
from lexigram.ai.session import SessionStateMachine, SessionError

sm = SessionStateMachine(initial_status="created")

await sm.transition("activate")
assert sm.current_status == "active"

await sm.transition("close")
assert sm.current_status == "closed"

# Invalid transitions raise SessionTransitionError
try:
    await sm.transition("close")  # already closed
except SessionError:
    pass
```

## React to session lifecycle events and hooks

```python
from lexigram.ai.session import (
    SessionCreatedEvent,
    SessionClosedEvent,
    SessionStartedHook,
    SessionClosedHook,
)
from lexigram.contracts.ai.session import SessionTurn
from datetime import datetime, UTC

manager = await env.resolve(SessionManagerProtocol)

# SessionCreatedEvent is emitted via the event bus on creation
event_bus.subscribe(SessionCreatedEvent, lambda e: print(f"New session: {e.session_id}"))

state = await manager.create(user_id="user-42")

# SessionStartedHook fires on the hook registry
hook_registry.publish(SessionStartedHook(session_id=state.session_id))

turn = SessionTurn(
    turn_id="t1", role="user", content="Hi",
    timestamp=datetime.now(UTC),
)
await manager.add_turn(state.session_id, turn)
await manager.end(state.session_id)

# SessionClosedEvent is emitted when a session ends
# SessionClosedHook fires when the session is closed for writes
```

## Persist sessions with CacheSessionStore or DatabaseSessionStore

```python
from lexigram.ai.session import (
    SessionManagerImpl,
    SessionConfig,
    CacheSessionStore,
    DatabaseSessionStore,
    InMemorySessionStore,
)

# In-memory (default — dev / testing)
store = InMemorySessionStore()
manager = SessionManagerImpl(config=SessionConfig(), store=store)

# Cache-backed (e.g. Redis via CacheBackendProtocol)
from lexigram.contracts.infra.cache import CacheBackendProtocol
cache_backend = await container.resolve(CacheBackendProtocol)
cache_store = CacheSessionStore(cache=cache_backend)
manager = SessionManagerImpl(config=SessionConfig(), store=cache_store)

# SQL database (via DatabaseProviderProtocol)
from lexigram.contracts.data.sql.database import DatabaseProviderProtocol
db = await container.resolve(DatabaseProviderProtocol)
db_store = DatabaseSessionStore(db=db)
manager = SessionManagerImpl(config=SessionConfig(), store=db_store)
```

## Track session analytics

```python
from lexigram.ai.session import SessionAnalytics

analytics = SessionAnalytics(store=store)
stats = await analytics.get_session_stats(user_id="user-42")
print(f"Active sessions: {stats.get('active_count')}")
```
