---
title: lexigram-ai-llm Guide
description: Mental model, core concepts, and typical usage of `lexigram-ai-llm`.
---

## Requirements

| Package | Required | Purpose |
|---------|----------|---------|
| `lexigram` | Yes | Core framework |
| `lexigram-contracts` | Yes | Protocol definitions |
| `lexigram-cache` | Optional | Response caching |
| `lexigram-resilience` | Optional | Retry and rate limiting |

## What problem does it solve?

`lexigram-ai-llm` provides a **unified, async LLM client interface** across multiple providers (OpenAI, Anthropic, Ollama, Groq, Cohere, Mistral, OpenRouter, Gemini, and more). It handles:

- Client creation and lifecycle via `LLMProvider`
- Provider-specific authentication and connection management
- Response caching, rate limiting, and token counting
- Multi-provider routing (via `LLMRoutingProvider`)
- Structured output extraction
- Streaming with thinking/reasoning support
- Provider registry for custom model providers

## Mental model

```
LLMModule.configure(config)
         │
    LLMProvider
    ├── ProviderRegistry  →  create_llm_client(config, registry)
    ├── TokenCounterRegistry  →  token counting per model
    ├── ParserRegistry  →  output parsing
    ├── LLMModelManager (optional)  →  local model lifecycle
    └── LLMCache (optional)  →  response caching
         │
         ▼
    LLMClientProtocol  ←  injectable via container
    ├── complete()  →  Result[CompletionProtocol, LLMError]
    └── stream_chat()  →  AsyncStream[StreamChunk, LLMError]
```

## Core concepts

### LLMClientProtocol

The central protocol. Every provider client implements this:

```python
class LLMClientProtocol(Protocol):
    async def complete(
        self,
        messages: Sequence[ChatMessageProtocol],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        tools: Sequence[ToolDefinition] | None = None,
        stop_sequences: Sequence[str] | None = None,
        **kwargs: Any,
    ) -> Result[CompletionProtocol, LLMError]: ...

    def stream_chat(
        self,
        messages: list[ChatMessageProtocol],
        ...
    ) -> AsyncStream[StreamChunk, LLMError]: ...
```

`complete()` returns `Result` — check `is_ok()`/`is_err()` to handle expected failures (rate limits, content filters, model not found).

### ClientConfig

Typed configuration with `SecretStr` for API keys:

```python
from lexigram.ai.llm import ClientConfig

config = ClientConfig(
    provider="openai",
    model="gpt-4o",
    api_key="sk-...",
    temperature=0.7,
    max_tokens=2000,
    timeout=60,
    thinking=ThinkingConfig(budget_tokens=5000),
)
```

### Provider Registry

A central `ProviderRegistry` maps provider names to client classes. Built-in providers (OpenAI, Anthropic, Ollama, etc.) are registered by default. Custom providers can be added at runtime.

### Conversation Manager

For multi-turn conversations, use `ConversationManager`:

```python
from lexigram.ai.llm import ConversationManager, ConversationConfig

manager = ConversationManager(
    config=ConversationConfig(max_turns=10),
    llm_client=llm,
)
await manager.add_message({"role": "user", "content": "Hello"})
response = await manager.get_response()
```

## Typical usage

### 1. Basic completion with error handling

```python
from lexigram.contracts.ai import LLMClientProtocol
from lexigram.contracts.ai.llm import LLMError
from lexigram.result import Result

llm = await container.resolve(LLMClientProtocol)
result: Result[CompletionProtocol, LLMError] = await llm.complete(
    [{"role": "user", "content": "Tell me a joke"}],
)

reply = result.match(
    ok=lambda c: c.content,
    err=lambda e: f"Failed: {e}",
)
print(reply)
```

### 2. Streaming

```python
stream = llm.stream_chat([{"role": "user", "content": "Write a poem"}])

async for chunk in stream:
    if chunk.delta:
        print(chunk.delta, end="")
```

### 3. Structured output (JSON)

```python
from lexigram.ai.llm import JSONExtractor

extractor = JSONExtractor(llm_client=llm)
schema = {"type": "object", "properties": {"name": {"type": "string"}}}
result = await extractor.extract("Extract a name", schema=schema)
if result.is_ok():
    print(result.unwrap())
```

### 4. Multi-provider routing

```python
from lexigram.ai.llm import LLMModule
from lexigram.ai.llm.routing import LLMConfig

module = LLMModule.configure(routing=LLMConfig())
```

## Best practices

- **Always handle the `Result`** — `complete()` returns expected failures. Don't `unwrap()` without checking `is_ok()`.
- **Set `api_key` via env var** — use `LEX_AI_LLM__API_KEY` instead of hardcoding.
- **Install only the provider extras you need** — `pip install lexigram-ai-llm[openai]` keeps dependencies minimal.
- **Use streaming for long responses** — `stream_chat()` returns an `AsyncStream` that yields tokens incrementally.
- **Enable caching for repeated queries** — set `enable_cache=True` in `ClientConfig` and provide a `CacheBackendProtocol`.

## Next steps

- [Architecture](/packages/lexigram-ai-llm/architecture/) — client classes, caching, model management
- [Configuration](/packages/lexigram-ai-llm/configuration/) — all config keys
- [How-tos](/packages/lexigram-ai-llm/howtos/) — streaming, conversation management, structured output
- [Troubleshooting](/packages/lexigram-ai-llm/troubleshooting/) — common errors and fixes
