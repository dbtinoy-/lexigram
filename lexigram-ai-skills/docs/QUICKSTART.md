---
title: lexigram-ai-skills Quickstart
description: Install, wire, and run your first skill in under 5 minutes.
sidebar:
  order: 1
---

**lexigram-ai-skills** provides a composable skill/tool registry, executor, built-in tools, and discovery for the Lexigram AI subsystem.

```bash
uv add lexigram-ai-skills
```

## Minimal example

```python
import asyncio
from lexigram import Application, LexigramConfig
from lexigram.ai.skills import SkillsModule


async def main() -> None:
    config = LexigramConfig.from_yaml()
    app = Application(name="skills-demo", config=config)
    app.add_module(SkillsModule.configure())
    async with app.boot():
        from lexigram.contracts.ai.skills import SkillExecutorProtocol
        executor = await app.container.resolve(SkillExecutorProtocol)
        result = await executor.execute("current_datetime", {})
        if result.is_ok():
            print(result.unwrap().output)
        else:
            print("Error:", result.unwrap_err())


asyncio.run(main())
```

## Wiring with a provider

```python
from lexigram import Application, LexigramConfig
from lexigram.ai.skills import SkillsProvider
from lexigram.ai.skills import SkillsConfig


async def main() -> None:
    config = LexigramConfig.from_yaml()
    app = Application(name="skills-demo", config=config)
    app.add_provider(SkillsProvider(config=SkillsConfig(enable_builtin=True)))
    async with app.boot():
        ...

```

## Next steps

- [Guide](/packages/lexigram-ai-skills/guide/) — mental model, core concepts, common patterns
- [Architecture](/packages/lexigram-ai-skills/architecture/) — internal design and extension points
- [Configuration](/packages/lexigram-ai-skills/configuration/) — every config option
- [API Reference](/packages/lexigram-ai-skills/api/) — generated API docs
