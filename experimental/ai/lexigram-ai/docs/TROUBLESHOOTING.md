---
title: lexigram-ai Troubleshooting
description: Common errors with `lexigram-ai`, their causes, and fixes.
---

## Missing sub-package

```
ImportError: No module named 'lexigram.ai.llm'
```

**Cause:** `lexigram-ai-llm` is not installed.

**Fix:** Install the required sub-package:

```bash
uv add lexigram-ai-llm
```

## LLM client not configured

```
RuntimeError: LLM client not configured. Cannot perform chat.
```

**Cause:** `AIProvider.chat()` called but no `llm` config was provided.

**Fix:** Pass `AIConfig(llm=ClientConfig(...))` to `AIModule.configure()`.

## Insecure API key in production

```
ValueError: CRITICAL SECURITY ERROR: Insecure LLM API key detected in PRODUCTION.
```

**Cause:** The `api_key` field contains a placeholder value (`sk-...`, `sk-test`, `change-me`) and `LEX_ENV=production`.

**Fix:** Set a valid API key via `LEX_AI_LLM__API_KEY` environment variable.

## Governance persistence not configured

```
(log warning) DatabaseProviderProtocol not available; governance persistence disabled
```

**Cause:** No database or cache provider is registered. Governance audit store falls back to in-memory.

**Fix:** Register a provider that binds `DatabaseProviderProtocol` or `CacheBackendProtocol` in the container for persistent governance storage.

## Sub-provider health check fails

```
(log warning) LLM health check failed
```

**Cause:** The LLM provider's `health_check()` threw a `ConnectionError`, `TimeoutError`, or `RuntimeError`.

**Fix:** Verify the LLM API endpoint is reachable and the API key is valid. Check `health.details["components"]["llm"]["error"]` for specifics.

## Entry-point subsystem not loaded

```python
# Subsystem is installed but not wired
```

**Cause:** The package's entry point may fail to load silently.

**Fix:** Check the debug log message `"Registered AI subsystem via entry-point"` to confirm discovery. Verify the entry-point group is `lexigram.ai.subsystems` in the package's `pyproject.toml`.

## TypeError: LLM client does not satisfy LLMClientProtocol

```
TypeError: LLM client for provider 'custom' does not satisfy the LLMClientProtocol protocol.
```

**Cause:** A custom provider's client class does not implement `complete()`, `stream_chat()`, `health_check()`, and `close()` with the correct signatures.

**Fix:** Ensure the client class satisfies `LLMClientProtocol` from `lexigram.contracts.ai.llm`.

## Sub-provider health check fails during boot

**Symptom:** Application starts but `app.health_check()` shows `DEGRADED` status for `ai` component.

**Cause:** `AIProvider.health_check()` calls each sub-provider's health check. If the LLM, vector store, or RAG provider is unreachable (connection refused, timeout), the overall health degrades. This is logged with `LLM health check failed` or `Vector store health check failed`.

**Fix:** Check the `details` dict for per-component error messages:

```python
health = await app.health_check()
print(health.details["components"]["llm"]["error"])
```

Verify each sub-system is running and reachable. Use `health_check(timeout=10.0)` to allow more time for slow backends.

## Entry-point subsystem not discovered

**Symptom:** A `lexigram-ai-*` package is installed but its services are not registered. No `Registered AI subsystem via entry-point` log message appears.

**Cause:** The package's `pyproject.toml` declares the entry point under `[project.entry-points."lexigram.ai.subsystems"]` but the package is not importable, or `importlib.metadata` raised an `ImportError`.

**Fix:** Verify the entry point is correctly declared:

```toml
[project.entry-points."lexigram.ai.subsystems"]
fine_tuning = "lexigram_ai_fine_tuning.di.provider:FineTuningProvider"
```

Confirm the provider module is importable:

```bash
uv run python -c "from lexigram_ai_fine_tuning.di.provider import FineTuningProvider; print('ok')"
```

## Governance audit store not persisting across restarts

**Symptom:** Governance decisions (budget approvals, policy overrides) disappear after application restart.

**Cause:** No `DatabaseProviderProtocol` or `CacheBackendProtocol` is registered, so the governance module falls back to `InMemoryAuditStore`. In-memory data is lost on restart.

**Fix:** Register a database or cache provider to enable persistent governance storage:

```python
from lexigram.sql import DatabaseModule

app.add_module(DatabaseModule.configure("postgresql+asyncpg://..."))
```

The provider logs `DatabaseProviderProtocol not available; governance persistence disabled` when falling back to in-memory mode.

## RAGCache returning stale data

**Symptom:** RAG queries repeatedly return the same (outdated) results even after documents are updated.

**Cause:** The `RAGCache` wraps a `CacheBackendProtocol` with default TTL. If the cache is not invalidated after document updates, stale embeddings are served.

**Fix:** Clear the RAG cache after document ingestion:

```python
from lexigram.ai.rag.cache import RAGCache

cache = await container.resolve(RAGCache)
await cache.clear()
```

Or disable caching during development:

```yaml
ai_rag:
  cache:
    enabled: false
```
