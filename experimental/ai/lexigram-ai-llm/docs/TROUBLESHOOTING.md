---
title: lexigram-ai-llm Troubleshooting
description: Common errors with `lexigram-ai-llm`, their causes, and fixes.
---

## Missing API key

```python
# No error at startup, but requests fail
LLMError: Authentication failed
```

**Cause:** `ClientConfig.api_key` is not set for a provider that requires it (OpenAI, Anthropic, Groq, etc.).

**Fix:** Set the API key via config or env var:

```bash
export LEX_AI_LLM__API_KEY=sk-...
```

The `boot()` method logs a warning when a required key is missing.

## Unsupported provider

```
ValueError: Unsupported LLM provider: 'custom_provider'
```

**Cause:** The provider name is not registered in `ProviderRegistry`.

**Fix:** Register it:

```python
from lexigram.ai.llm import ProviderRegistry
registry = ProviderRegistry()
registry.register("custom_provider", CustomClient)
```

Or check the exact provider name — use one of: `openai`, `anthropic`, `ollama`, `groq`, `cohere`, `mistral`, `openrouter`.

## Client does not satisfy LLMClientProtocol

```
TypeError: LLM client for provider 'x' does not satisfy the LLMClientProtocol protocol.
```

**Cause:** Your custom client is missing `complete()`, `stream_chat()`, `health_check()`, or `close()`.

**Fix:** Implement all four methods with the correct signatures.

## Rate limit exceeded

`LLMRateLimitError` returned from `complete()`:

```
Err(LLMRateLimitError("rate_limit_exceeded"))
```

**Cause:** API rate limit hit.

**Fix:** Implement backoff/retry or use `RateLimiter`:

```python
from lexigram.ai.llm import RateLimiter
limiter = RateLimiter(max_calls=60, window_seconds=60)
await limiter.acquire()
```

## Content filtered

`LLMContentFilterError` returned from `complete()`:

```
Err(LLMContentFilterError("content_filter"))
```

**Cause:** The provider's safety filter blocked the response.

**Fix:** Reformulate the prompt or inform the user. This is a recoverable error — the caller should handle it gracefully.

## Model not found

`LLMModelNotFoundError` returned from `complete()`:

```
Err(LLMModelNotFoundError("model_not_found: gpt-4o"))
```

**Cause:** The model name is not available for the configured provider.

**Fix:** Check the model name and provider compatibility. Route to a different model if using the routing layer.

## Cache requires CacheBackendProtocol

```
ValueError: CacheBackendProtocol required for LLM caching but not found in container
```

**Cause:** `ClientConfig.enable_cache=True` but no `CacheBackendProtocol` is registered.

**Fix:** Install and register a cache provider (e.g., `lexigram-cache` with Redis).

## Token limit exceeded

`TokenLimitError`:

```
TokenLimitError: Request exceeds token limit
```

**Cause:** The input exceeds the model's context window.

**Fix:** Truncate messages, summarize context, or use a model with a larger context window.

## ImportError: optional dependency missing

```
ImportError: No module named 'openai'
```

**Cause:** The provider extra is not installed.

**Fix:** Install it:

```bash
uv add "lexigram-ai-llm[openai]"
```
