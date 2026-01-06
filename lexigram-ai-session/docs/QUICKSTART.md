---
title: lexigram-ai-session Quickstart
description: Install, wire, and create your first AI session in under 5 minutes.
sidebar:
  order: 1
---

**lexigram-ai-session** provides stateful conversation session management — branching, checkpointing, multi-agent group sessions, and context pruning.

```bash
uv add lexigram-ai-session
```

## Minimal example

```python
import asyncio
from lexigram import Application, LexigramConfig
from lexigram.ai.session import SessionModule


async def main() -> None:
    config = LexigramConfig.from_yaml()
    app = Application(name="session-demo", config=config)
    app.add_module(SessionModule.configure())
    async with app.boot():
        from lexigram.contracts.ai.session import SessionManagerProtocol
        manager = await app.container.resolve(SessionManagerProtocol)
        state = await manager.create(user_id="user-42")
        print(f"Session {state.session_id} created ({state.status})")


asyncio.run(main())
```

## Wiring with a provider

```python
from lexigram import Application, LexigramConfig
from lexigram.ai.session import SessionProvider
from lexigram.ai.session import SessionConfig


async def main() -> None:
    config = LexigramConfig.from_yaml()
    app = Application(name="session-demo", config=config)
    app.add_provider(SessionProvider(config=SessionConfig(backend="in_memory")))
    async with app.boot():
        ...
```

## Next steps

- [Guide](/packages/lexigram-ai-session/guide/) — mental model, core concepts, common patterns
- [Architecture](/packages/lexigram-ai-session/architecture/) — internal design and extension points
- [Configuration](/packages/lexigram-ai-session/configuration/) — every config option
- [API Reference](/packages/lexigram-ai-session/api/) — generated API docs
