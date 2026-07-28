---
title: "AI Sessions"
description: "Conversation sessions with branching, checkpointing, and multi-agent coordination."
---

`lexigram-ai-session` provides stateful conversation session management with branching, checkpointing, and multi-agent coordination. Sessions track turns, metadata, and lifecycle state, supporting fork-and-branch workflows and point-in-time restoration.

For the full configuration reference and advanced features (analytics, middleware, context pruning), see the [`lexigram-ai-session` package docs](/packages/lexigram-ai-session/).

---

## 1. The Contracts

Sessions are managed through two protocols from `lexigram.contracts.ai.session`:

```python
from typing import Any, Protocol, runtime_checkable
from lexigram.contracts.ai.session import (
    SessionState, SessionStatus, SessionTurn, SessionCheckpoint,
)


class SessionStoreProtocol(Protocol):
    async def save(self, state: SessionState) -> None: ...
    async def load(self, session_id: str) -> SessionState | None: ...
    async def delete(self, session_id: str) -> None: ...
    async def list_sessions(self, user_id: str) -> list[SessionState]: ...
    async def save_checkpoint(self, checkpoint: SessionCheckpoint) -> None: ...
    async def load_checkpoint(self, checkpoint_id: str) -> SessionCheckpoint | None: ...
    async def list_checkpoints(self, session_id: str) -> list[SessionCheckpoint]: ...


class SessionManagerProtocol(Protocol):
    async def create(
        self, user_id: str, metadata: dict[str, Any] | None = None
    ) -> SessionState: ...
    async def resume(self, session_id: str) -> SessionState | None: ...
    async def add_turn(self, session_id: str, turn: SessionTurn) -> None: ...
    async def get_state(self, session_id: str) -> SessionState | None: ...
    async def checkpoint(self, session_id: str) -> SessionCheckpoint: ...
    async def restore(self, checkpoint_id: str) -> SessionState: ...
    async def close(self, session_id: str) -> None: ...
    async def suspend(self, session_id: str) -> SessionState: ...
```

`SessionState` is a frozen dataclass capturing the full session snapshot:

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class SessionState:
    session_id: str
    user_id: str
    status: SessionStatus
    turns: list[SessionTurn] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    total_tokens: int = 0
    total_cost: float = 0.0
    turn_count: int = 0
    parent_session_id: str | None = None
    branch_name: str | None = None
```

Sessions progress through `SessionStatus` values:

```python
from enum import StrEnum


class SessionStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CLOSED = "closed"
    EXPIRED = "expired"
```

---

## 2. Configuration

Add `SessionModule` and configure persistence and lifecycle:

```python
from lexigram import Application
from lexigram.ai.session import SessionModule, SessionConfig

app = Application(name="my-app")
app.add_module(SessionModule.configure(
    SessionConfig(
        backend="cache",
        session_ttl=86400,
        max_sessions_per_user=100,
        auto_checkpoint_interval=5,
    ),
))
```

```yaml title="application.yaml"
ai_session:
  enabled: true
  backend: cache
  name: ai-session
  session_ttl: 86400
  cleanup_interval_s: 3600
  max_turns_per_session: 1000
  max_sessions_per_user: 100
  auto_checkpoint_interval: 5
  max_checkpoints_per_session: 50
  max_branches_per_session: 10
  default_turn_strategy: round_robin
  consolidate_on_close: true
```

:::note
In production, use `backend: cache` or `backend: database`. The `in_memory` backend is suitable for development but will emit a `ConfigIssue` error in production environments.
:::

---

## 3. Creating and Managing Sessions

Create a session, add turns, and close it through `SessionManagerProtocol`:

```python
from lexigram import Application
from lexigram.ai.session import SessionModule, SessionConfig
from lexigram.contracts.ai.session import (
    SessionManagerProtocol, SessionTurn,
)
from datetime import datetime, UTC


async def session_lifecycle() -> None:
    async with Application.boot(
        modules=[SessionModule.configure(SessionConfig(backend="cache"))]
    ) as app:
        manager = await app.container.resolve(SessionManagerProtocol)

        session = await manager.create(user_id="user-123")
        print(f"Session: {session.session_id}, status: {session.status}")

        await manager.add_turn(
            session.session_id,
            SessionTurn(
                turn_id="turn-1",
                role="user",
                content="What is the weather?",
                timestamp=datetime.now(UTC),
            ),
        )

        state = await manager.get_state(session.session_id)
        print(f"Turns: {state.turn_count}")

        await manager.close(session.session_id)
        print(f"Closed, status: {state.status}")
```

---

## 4. Checkpointing

Create checkpoints at key points and restore later:

```python
async def checkpoint_example(manager: SessionManagerProtocol, session_id: str) -> None:
    checkpoint = await manager.checkpoint(session_id)
    print(f"Created checkpoint: {checkpoint.checkpoint_id}")

    checkpoints = await manager.list_checkpoints(session_id)
    print(f"Total checkpoints: {len(checkpoints)}")

    restored = await manager.restore(checkpoints[0].checkpoint_id)
    print(f"Restored session: {restored.session_id}, status: {restored.status}")
```

Checkpoints are immutable snapshots. The `SessionStoreProtocol` persists them separately from the active session state.

:::tip
Enable `auto_checkpoint_interval` in config to automatically create a checkpoint every N turns, giving you a safety net for session rollback.
:::

---

## 5. Branching

Fork a session into branches for exploratory conversations:

```python
async def branching_example(session_id: str) -> None:
    # Create a branch from an existing session
    branch = await manager.create(
        user_id="user-123",
        metadata={"parent_session_id": session_id, "branch_name": "exploration"},
    )

    # The branch copies session state and continues independently
    print(f"Branch session: {branch.session_id}")
    print(f"Parent: {branch.parent_session_id}")

    # List all branches for a session
    branches = [s for s in await store.list_sessions("user-123")
                if s.parent_session_id == session_id]
    print(f"Branches: {len(branches)}")
```

Branching is useful for exploring alternative conversation paths, testing different agent configurations, or A/B testing responses.

---

## 6. Multi-Agent Sessions

Sessions support multi-agent coordination with turn management:

```python
from lexigram.ai.session.multi_agent.turn_manager import RoundRobinTurnManager
from lexigram.ai.session.multi_agent.group_session import GroupSession


async def multi_agent_session() -> None:
    turn_manager = RoundRobinTurnManager(agent_ids=["agent-alpha", "agent-beta", "agent-gamma"])
    group = GroupSession(
        session_id="group-1",
        agents=["agent-alpha", "agent-beta", "agent-gamma"],
        turn_manager=turn_manager,
    )

    next_agent = await group.determine_next_agent()
    print(f"Next agent: {next_agent}")
```

Role isolation (`RoleIsolation`) ensures agents only access turns and context relevant to their role, preventing information leakage in multi-agent configurations.

---

## 7. Testing

Use `SessionModule.stub()` for isolated tests:

```python
from lexigram import Application
from lexigram.ai.session import SessionModule
from lexigram.contracts.ai.session import SessionManagerProtocol


async def test_session_lifecycle() -> None:
    async with Application.boot(modules=[SessionModule.stub()]) as app:
        manager = await app.container.resolve(SessionManagerProtocol)

        session = await manager.create(user_id="test-user")
        assert session.status.value == "active"

        result = await manager.resume(session.session_id)
        assert result is not None
```

:::caution
The stub uses an in-memory store with the cleanup scheduler disabled. Data is not persisted between test runs.
:::

---

## Next Steps

- [AI Agents](/guides/ai-agents/) — running agents within sessions
- [AI Memory](/guides/ai-memory/) — consolidating sessions into episodic and semantic memory
- [Dependency Injection](/fundamentals/dependency-injection/) — binding protocols to implementations
- [Providers](/fundamentals/providers/) — how `SessionProvider` hooks into application boot
- [`lexigram-ai-session` package](/packages/lexigram-ai-session/) — analytics, middleware, pruning
