---
title: lexigram-ai-feedback Quickstart
description: Install, wire, and collect AI response feedback in minutes.
---

:::note[What you'll get]
`FeedbackProvider` registers a `FeedbackProtocol` service, a `FeedbackCollector`, and a processor registry — ready to persist ratings, text comments, corrections, and labels via `FeedbackStoreProtocol`.
:::

## Install

```bash
uv add lexigram-ai-feedback
```

## Minimal Example

```python
from lexigram import Application, LexigramConfig
from lexigram.ai.feedback import FeedbackModule

async def main() -> None:
    app = Application(name="feedback-app", config=LexigramConfig.from_yaml())
    app.add_module(FeedbackModule.configure())
    await app.start()
    # FeedbackProtocol is registered — ready to submit feedback
    await app.stop()
```

## Collect Your First Rating

```python
from lexigram.ai.feedback import FeedbackCollector

collector: FeedbackCollector  # resolved from container
feedback_id = await collector.collect_rating(
    rating=4.5,
    context={"model": "gpt-4o", "session_id": "session-123"},
)
print(f"Stored feedback: {feedback_id}")
```

## What Just Happened

1. `FeedbackProvider` registered `FeedbackCollector`, `FeedbackProcessorRegistry`, and `FeedbackService` (as `FeedbackProtocol`) in the container.
2. During `boot()`, the provider detected `DatabaseProviderProtocol` and optionally `CacheBackendProtocol` to wire a durable `DatabaseFeedbackStore` (and optionally a `CachedFeedbackStore`).
3. `FeedbackCollector` is now ready to persist feedback through the wired store.

## Wiring with Database Storage

```python
from lexigram import Application, LexigramConfig
from lexigram.ai.feedback import FeedbackModule
from lexigram.sql import DatabaseModule

app = Application(name="my-app")
app.add_module(DatabaseModule.configure("postgresql://localhost/mydb"))
app.add_module(FeedbackModule.configure())
await app.start()
# FeedbackCollector now persists to Postgres via DatabaseFeedbackStore
```

## Next Steps

- [Guide](./GUIDE.md) — collecting, storing, and querying feedback
- [How-Tos](./HOWTOS.md) — practical recipes
- [Configuration](./CONFIGURATION.md) — every config key
