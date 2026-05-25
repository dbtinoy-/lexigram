---
title: lexigram-ai-observability Quickstart
description: Install, wire, and run AI observability for LLM and vector calls.
---

:::note[What you'll get]
`ObservabilityProvider` auto-instruments `LLMClientProtocol` and `VectorStoreProtocol` with distributed tracing, metrics, and health checks — zero code changes to your AI logic.
:::

## Install

```bash
uv add lexigram-ai-observability
```

## Minimal Example

```python
from lexigram import Application, LexigramConfig
from lexigram.ai.observability import ObservabilityModule

async def main() -> None:
    app = Application(name="my-ai-app", config=LexigramConfig.from_yaml())

    app.add_module(ObservabilityModule.configure())
    await app.start()

    # Everything registered — LLM/vector calls are now traced
    await app.stop()
```

## What Just Happened

1. `ObservabilityProvider` registered `AITracer`, `AIMetrics`, and `AIHealthMonitor` as container singletons.
2. During `boot()`, the provider detected any registered `LLMClientProtocol` and `VectorStoreProtocol` instances and wrapped them with `ObservableLLMClient` / `ObservableVectorStore`.
3. Subsequent LLM completions and vector store operations are automatically traced and metered.

## Wiring with Other AI Packages

```python
from lexigram import Application, LexigramConfig
from lexigram.ai.observability import ObservabilityModule
from lexigram.ai.llm import LLMModule

config = LexigramConfig.from_yaml()
app = Application(name="observable-ai", config=config)
app.add_module(LLMModule.configure())
app.add_module(ObservabilityModule.configure())
await app.start()
```

## Next Steps

- [Guide](./GUIDE.md) — tracing, metrics, and health checks in depth
- [How-Tos](./HOWTOS.md) — practical recipes
- [Configuration](./CONFIGURATION.md) — every config key
