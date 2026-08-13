---
title: lexigram-ai Guide
description: Mental model, core concepts, and typical usage of `lexigram-ai`.
---

## Requirements

| Package | Required | Purpose |
|---------|----------|---------|
| `lexigram` | Yes | Core framework |
| `lexigram-contracts` | Yes | Protocol definitions |
| `lexigram-ai-llm` | Yes | LLM client integration |
| `lexigram-ai-rag` | Yes | RAG pipeline integration |
| `lexigram-ai-feedback` | Yes | Feedback collection |
| `lexigram-ai-observability` | Yes | Observability |
| `lexigram-ai-agents` | Optional | Agent system (runtime discovery) |
| `lexigram-ai-skills` | Optional | Skills system (runtime discovery) |
| `lexigram-ai-memory` | Optional | Memory system (runtime discovery) |
| `lexigram-ai-session` | Optional | Session management (runtime discovery) |
| `lexigram-ai-mcp` | Optional | MCP protocol (runtime discovery) |
| `lexigram-ai-workers` | Optional | Background workers (runtime discovery) |

## What problem does it solve?

`lexigram-ai` is the **orchestration layer** for the AI subsystem. Instead of wiring LLM clients, vector stores, RAG pipelines, and observability providers individually, you configure a single `AIConfig` and `AIModule` wires everything through the DI container.

It discovers sub-packages via Python entry points (`lexigram.ai.subsystems`), so installing a supported extension (e.g., `lexigram-ai-llm`) is enough — no manual registration.

## Mental model

```
AIConfig ──► AIModule.configure()
                  │
           AIProvider (register)
           ├── LLMProvider        (lexigram-ai-llm)
           ├── VectorProvider     (lexigram-vector, optional)
           ├── RAGProvider        (lexigram-ai-rag, optional)
           ├── Observability      (always on: metrics, tracing, health)
           ├── Governance         (optional)
           └── Entry-point discovery (any subsystem with ep group)
```

`AIModule` is the **public entrypoint**. `AIProvider` is the internal orchestrator that delegates to sub-providers.

## Core concepts

### AIConfig

The single config object that drives the entire AI subsystem. It nests sub-configs for each subsystem:

```python
from lexigram.ai.config import AIConfig
from lexigram.ai.llm import ClientConfig

config = AIConfig(
    enabled=True,
    llm=ClientConfig(provider="openai", model="gpt-4o"),
    # vector=VectorConfig(...),
    # rag=RAGConfig(...),
)
```

Config is read from `LEX_AI__*` environment variables or the `ai:` section of `application.yaml`.

### AIProvider

The provider class that orchestrates sub-providers. In `register()` it:
1. Registers monitoring singletons (`AIHealthMonitor`, `AIMetrics`, `AITracer`, `CallbackManagerProtocol`)
2. Delegates LLM, Vector, and RAG to their respective sub-providers
3. Discovers additional subsystems via `lexigram.ai.subsystems` entry points
4. Wires governance and RAG cache when the relevant config is present

```python
from lexigram.ai.di.provider import AIProvider

provider = AIProvider(config=AIConfig(llm=ClientConfig(provider="openai")))
# Used internally by AIModule — you normally don't instantiate it directly
```

### Entry-point discovery

Any installed package declaring the `lexigram.ai.subsystems` entry-point group is automatically discovered:

```toml
# pyproject.toml of a subsystem package
[project.entry-points."lexigram.ai.subsystems"]
llm = "lexigram.ai.llm.di.provider:LLMProvider"
```

The `AIProvider.register()` method loads each entry point and calls `sub_provider.register(container)`.

## Typical usage

### 1. Basic LLM access

```python
from lexigram import Application
from lexigram.ai.module import AIModule
from lexigram.ai.llm import ClientConfig
from lexigram.contracts.ai import LLMClientProtocol


async def main() -> None:
    config = AIConfig(llm=ClientConfig(provider="openai", model="gpt-4o"))
    async with Application.boot(
        name="ai-demo",
        modules=[AIModule.configure(config)],
    ) as app:
        llm = await app.container.resolve(LLMClientProtocol)
        result = await llm.complete([{"role": "user", "content": "Hello!"}])
        if result.is_ok():
            print(result.unwrap().content)
```

### 2. Health check

```python
from lexigram.contracts.core import HealthStatus

health = await app.health_check()
print(health.status)  # HealthStatus.HEALTHY or .DEGRADED
```

### 3. Manual provider wiring (no module)

```python
from lexigram import Application
from lexigram.ai.di.provider import AIProvider
from lexigram.ai.config import AIConfig

app = Application(name="ai-demo")
app.add_provider(AIProvider(config=AIConfig(llm=ClientConfig(provider="openai"))))
await app.start()
```

## Best practices

- **Start with `AIModule.configure()`** — it's the intended public API. Only drop to `AIProvider` directly when you need fine-grained control over sub-provider configuration.
- **One AIConfig per app** — the AI subsystem is designed as a singleton. Creating multiple instances will register duplicate bindings.
- **Use env vars for secrets** — set `LEX_AI_LLM__API_KEY` instead of hardcoding API keys. `AIConfig` reads environment variables automatically.
- **Enable governance in production** — `AIConfig(governance=GovernanceConfig(enabled=True))` provides an audit trail for AI operations.
- **Don't import sub-packages directly** — resolve `LLMClientProtocol` through the container instead of importing `LLMProvider` or individual clients.

## Next steps

- [Architecture](/packages/lexigram-ai/architecture/) — provider lifecycle and entry-point discovery
- [Configuration](/packages/lexigram-ai/configuration/) — every config key
- [How-tos](/packages/lexigram-ai/howtos/) — common recipes
- [LLM Package](/packages/lexigram-ai-llm/) — the LLM client layer in depth
