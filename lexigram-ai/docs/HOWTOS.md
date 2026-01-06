---
title: lexigram-ai How-Tos
description: Common usage patterns for `lexigram-ai`.
---

## 1. Wire AIModule with LLM only

```python
from lexigram import Application
from lexigram.ai.module import AIModule
from lexigram.ai.llm import ClientConfig

config = AIConfig(llm=ClientConfig(provider="openai", model="gpt-4o"))
async with Application.boot(name="chat", modules=[AIModule.configure(config)]):
    ...
```

## 2. Make an LLM completion and handle Result

```python
from lexigram.contracts.ai import LLMClientProtocol

llm = await app.container.resolve(LLMClientProtocol)
result = await llm.complete([{"role": "user", "content": "Hello!"}])

if result.is_ok():
    reply = result.unwrap().content
else:
    error = result.unwrap_err()
    print(f"LLM call failed: {error}")
```

## 3. Check AI subsystem health

```python
health = await app.health_check()
if health.status == HealthStatus.DEGRADED:
    for component, info in health.details.get("components", {}).items():
        if info.get("status") != "healthy":
            print(f"{component}: {info}")
```

## 5. Use AIProvider directly (no module)

```python
from lexigram import Application
from lexigram.ai.di.provider import AIProvider

app = Application(name="ai-demo")
provider = AIProvider(config=AIConfig(llm=ClientConfig(provider="openai")))
app.add_provider(provider)
await app.start()
```

## 6. Override LLM config at construction

```python
provider = AIProvider(
    config=base_config,
    llm_config=ClientConfig(provider="anthropic", model="claude-sonnet-4-20250514"),
)
```

## 7. Configure from env vars only

```python
# Set LEX_AI_LLM__PROVIDER=openai LEX_AI_LLM__MODEL=gpt-4o
config = AIConfig()  # Reads from environment automatically
```

## 8. Use AIModule.stub() in tests

```python
import pytest
from lexigram.ai.module import AIModule


@pytest.fixture
def ai_module():
    # Stub module with no-op sub-modules and no background scheduler
    return AIModule.stub()


@pytest.mark.asyncio
async def test_without_real_llm(ai_module) -> None:
    # Use within an Application for integration tests
    from lexigram import Application

    async with Application.boot(name="test-ai", modules=[ai_module]) as app:
        health = await app.health_check()
        assert health is not None
```

## 9. Register custom callback handlers

```python
from lexigram.contracts.ai.callbacks import (
    CallbackHandlerProtocol,
    CallbackManagerProtocol,
)
from lexigram.contracts.ai.llm import ChatMessage, Completion


class LoggingHandler(CallbackHandlerProtocol):
    async def on_llm_start(
        self, messages: list[ChatMessage], model: str, **kwargs: object
    ) -> None:
        print(f"LLM call started — model: {model}")

    async def on_llm_end(
        self, response: Completion, **kwargs: object
    ) -> None:
        print(f"LLM call finished — tokens: {response.usage.total_tokens}")

    async def on_llm_error(
        self, error: Exception, **kwargs: object
    ) -> None:
        print(f"LLM call failed: {error}")


# After booting the app, resolve and register
manager = await app.container.resolve(CallbackManagerProtocol)
manager.register(LoggingHandler())
```

## 10. Trace AI operations with AITracer

```python
from lexigram.ai.observability import AITracer


tracer = await app.container.resolve(AITracer)

# Trace an LLM call
async with tracer.trace_llm_call("openai", "gpt-4o") as span:
    result = await llm.complete([{"role": "user", "content": "Hello!"}])
    if result.is_ok():
        span.set_attribute("tokens", result.unwrap().usage.total_tokens)

# Trace a vector store operation
async with tracer.trace_vector_operation("search", "pgvector") as span:
    results = await vector_store.search(query, limit=10)
    span.set_attribute("results.count", len(results))
```

## 11. Register a custom subsystem

```toml
# pyproject.toml
[project.entry-points."lexigram.ai.subsystems"]
my_subsystem = "my_package.provider:MyProvider"
```

The provider class must accept `config` and implement `register(container)`.
