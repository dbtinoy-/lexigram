# lexigram-ai-feedback

AI feedback collection for the Lexigram Framework — collection, processing, and storage

---

## Overview

AI feedback collection and continuous-learning loop for the Lexigram Framework. Captures user ratings, corrections, text feedback, and ground-truth labels from LLM interactions and routes them through an extensible processor pipeline to configurable storage backends. Zero-config usage starts with sensible defaults.


> Full documentation: [docs.lexigram.dev](https://docs.lexigram.dev)
## Install

```bash
uv add lexigram-ai-feedback
```

## Quick Start

```python
from lexigram import Application
from lexigram.di.module import Module, module

from lexigram.ai.feedback import FeedbackModule
from lexigram.ai.feedback.config import FeedbackConfig

@module(imports=[
    FeedbackModule.configure(
        FeedbackConfig(
            enabled=True,
            async_processing=True,
            store_raw_payloads=False,
        )
    )
])
class AppModule(Module):
    pass

async with Application.boot(modules=[AppModule]) as app:
    # use app.container to resolve services
    ...
```

## Configuration

> **Zero-config usage:** Call `FeedbackModule.configure()` with no arguments to use defaults.

### Option 1 — YAML file

```yaml
# application.yaml
ai_feedback:
  enabled: true
  async_processing: true
  store_raw_payloads: false
```

### Option 2 — Profiles + Environment Variables *(recommended)*

```bash
export LEX_AI_FEEDBACK__ENABLED=true
# Environment variables for each field
```

### Option 3 — Python

```python
from lexigram.ai.feedback.config import FeedbackConfig
from lexigram.ai.feedback import FeedbackModule

config = FeedbackConfig(
    enabled=True,
    async_processing=True,
    store_raw_payloads=False,
)
FeedbackModule.configure(config)
```

### Config reference

| Field | Default | Env var | Description |
|-------|---------|---------|-------------|
| `enabled` | `True` | `LEX_AI_FEEDBACK__ENABLED` | Master on/off switch for all feedback collection |
| `async_processing` | `True` | `LEX_AI_FEEDBACK__ASYNC_PROCESSING` | Process feedback handlers asynchronously in the background |
| `store_raw_payloads` | `False` | `LEX_AI_FEEDBACK__STORE_RAW_PAYLOADS` | Persist raw incoming feedback payloads for auditing |

## Module Factory Methods

| Method | Description |
|--------|-------------|
| `FeedbackModule.configure(config)` | Configure with explicit config |
| `FeedbackModule.stub()` | Minimal config for testing |

## Key Features

- **Four feedback types**: Rating, free-text, correction (original → corrected), and ground-truth labels
- **Extensible processor pipeline**: Custom processors via `FeedbackProcessorRegistry`
- **Storage backends**: In-memory, database (`DatabaseFeedbackStore`), and cache (`CachedFeedbackStore`)
- **Middleware integration**: `FeedbackMiddleware` and `FeedbackContext` for request/response capture
- **Lifecycle hooks**: `FeedbackSubmittedHook`, `FeedbackProcessedHook`, `FeedbackStoredHook`

## Testing

```python
async with Application.boot(modules=[FeedbackModule.stub()]) as app:
    # your test code
    ...
```

## Key Source Files

| File | What it contains |
|------|-----------------|
| `src/lexigram/ai/feedback/module.py` | `FeedbackModule.configure()`, `.stub()` |
| `src/lexigram/ai/feedback/config.py` | `FeedbackConfig` |
| `src/lexigram/ai/feedback/services/collector.py` | `FeedbackCollector` core service |
| `src/lexigram/ai/feedback/storage/database.py` | `DatabaseFeedbackStore` |
| `src/lexigram/ai/feedback/storage/cache.py` | `CachedFeedbackStore` |
| `src/lexigram/ai/feedback/processors/processor_registry.py` | `FeedbackProcessorRegistry` |
| `src/lexigram/ai/feedback/di/provider.py` | `FeedbackProvider` boot and registration |
