---
title: lexigram-ai-agents Quickstart
description: Install, configure, and run your first AI agent in under 5 minutes.
---

Agent system for Lexigram — AI agents with tools, strategies, and execution.

:::note[Maturity]
Alpha (0.1.x) — public APIs may change before 1.0.
:::

## Install

```bash
uv add lexigram-ai-agents
```

## Minimal Agent

```python
import asyncio

from lexigram import Application
from lexigram.ai.agents import AgentBase, AgentConfig, tool
from lexigram.ai.agents import AgentsModule
from lexigram.contracts.ai import AgentExecutorProtocol


@tool
async def get_weather(city: str) -> str:
    """Get the current weather for a city."""
    return f"Sunny, 22°C in {city}"


class WeatherAgent(AgentBase):
    name = "weather_agent"
    system_prompt = "You are a helpful weather assistant."

    @property
    def tools(self):
        return [get_weather]


async def main():
    config = AgentConfig(max_iterations=10, default_temperature=0.3)
    async with Application.boot(
        name="agent-demo",
        modules=[AgentsModule.configure(config)],
    ) as app:
        executor = await app.container.resolve(AgentExecutorProtocol)
        result = await executor.run(
            agent=WeatherAgent(),
            message="What is the weather in Tokyo?",
        )
        if result.is_ok():
            print(result.unwrap().message)


asyncio.run(main())
```

## What Just Happened

1. **`@tool`** decorated a function — auto-generated its JSON schema for the LLM.
2. **`AgentBase`** subclass declared identity, persona, and tools.
3. **`AgentsModule.configure(config)`** wired `AgentsProvider` into the container.
4. **`AgentExecutorProtocol`** resolved the executor from DI.
5. **`executor.run()`** returned `Result[AgentResponse, AgentError]`.

## Next Steps

- [Guide](./GUIDE.md) — agents, strategies, execution in depth
- [How-Tos](./HOWTOS.md) — common agent patterns
- [Configuration](./CONFIGURATION.md) — all config keys
