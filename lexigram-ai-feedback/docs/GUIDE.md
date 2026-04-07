---
title: lexigram-ai-feedback Guide
description: Collect, store, and query feedback on AI responses.
---

## Requirements

| Package | Required | Purpose |
|---------|----------|---------|
| `lexigram` | Yes | Core framework |
| `lexigram-contracts` | Yes | Protocol definitions |
| `lexigram-cache` | Optional | Feedback caching |
| `lexigram-sql` | Optional | Feedback storage |

## The Problem

AI systems generate outputs that need human evaluation — thumbs up/down, ratings, text corrections, or ground-truth labels. Without a structured feedback pipeline, you lose the signal needed for model improvement, quality tracking, and RLHF data collection.

`lexigram-ai-feedback` provides four feedback types, a pluggable storage layer, processor pipelines, and lifecycle hooks — all wired via DI.

## Mental Model

Feedback flows through four layers:

```
User/Action → FeedbackCollector → FeedbackStoreProtocol → Database/Cache
                                            ↓
                                     FeedbackSummary (aggregates)
```

- **Types:** `rating`, `text`, `correction`, `label` — defined by `FeedbackType` enum.
- **Storage:** `DatabaseFeedbackStore` (SQL via `DatabaseProviderProtocol`) or `CachedFeedbackStore` (write-through cache on top of DB).
- **Service:** `FeedbackService` implements `FeedbackProtocol` from contracts — high-level submit/query by trace ID.
- **Processors:** `FeedbackProcessorRegistry` routes each `FeedbackType` to a dedicated processor.

## Core Concepts

### FeedbackItem

A `FeedbackItem` is the unit of feedback — a frozen dataclass with a `FeedbackType`, value, context dict, metadata dict, auto-generated id, and timestamp:

```python
from lexigram.ai.feedback import FeedbackItem, FeedbackType

item = FeedbackItem(
    feedback_type=FeedbackType.RATING,
    value=4.5,
    context={"session_id": "sess-123", "model": "gpt-4o"},
    metadata={"user_id": "user-42"},
)
```

### FeedbackType

```python
from lexigram.ai.feedback import FeedbackType

# Available types
FeedbackType.RATING       # "rating" — numeric score
FeedbackType.TEXT         # "text" — free-text comment
FeedbackType.CORRECTION   # "correction" — original + corrected
FeedbackType.LABEL        # "label" — ground truth label + input
```

### Storage Backends

The store is resolved by `FeedbackProvider.boot()`:

1. If `DatabaseProviderProtocol` is registered → `DatabaseFeedbackStore` (auto-creates `ai_feedback` table).
2. If both `DatabaseProviderProtocol` and `CacheBackendProtocol` are registered → `CachedFeedbackStore` wrapping the DB store (write-through, 5-minute session TTL).

```python
from lexigram.ai.feedback import DatabaseFeedbackStore, CachedFeedbackStore
from lexigram.result import Ok

result = await store.save(feedback_item)
if result.is_ok():
    feedback_id = result.unwrap()
```

## Typical Usage

### Submit Feedback by Trace ID

```python
from lexigram.contracts.ai.feedback import FeedbackProtocol

service: FeedbackProtocol  # resolved from container
await service.submit_feedback(
    trace_id="trace-abc-123",
    score=0.95,
    comment="Great response, very accurate",
    metadata={"user_role": "admin"},
)
```

### Collect Different Types

```python
from lexigram.ai.feedback import FeedbackCollector

collector: FeedbackCollector

# Rating
await collector.collect_rating(rating=5, context={"model": "gpt-4o"})

# Text
await collector.collect_text(
    text="The answer was too verbose",
    context={"query": "summarize this document"},
)

# Correction
await collector.collect_correction(
    original="incorrect output",
    corrected="correct output",
    context={"model_id": "123"},
)

# Label
await collector.collect_label(
    label="SPAM",
    input_data="Buy cheap watches now!",
    context={"classifier": "email-filter"},
)
```

### Query Aggregates

```python
from lexigram.ai.feedback import FeedbackService

service: FeedbackService
stats = await service.get_feedback_stats(
    model="gpt-4o",
    provider="openai",
)
# {"total_count": 142, "average_rating": 4.2, "by_type": {"rating": 100, "text": 42}}
```

## Common Patterns

### Web Middleware Integration

```python
from lexigram.ai.feedback import FeedbackMiddleware, FeedbackCollector

collector: FeedbackCollector
middleware = FeedbackMiddleware(
    collector=collector,
    capture_inputs=True,
    capture_outputs=True,
)
# Register with your web app
```

### Processor Pipeline

Built-in processors handle each `FeedbackType`. Custom processors can be registered:

```python
from lexigram.ai.feedback.processors.processor_registry import (
    FeedbackProcessorRegistry,
    FeedbackProcessor,
)

class SentimentProcessor(FeedbackProcessor):
    async def process(self, value, context, collector):
        score = analyze_sentiment(value)
        return await collector.collect_rating(rating=score, context=context)

registry = FeedbackProcessorRegistry()
registry.register("sentiment", SentimentProcessor())
```

### FeedbackContext for Scoped Operations

```python
from lexigram.ai.feedback import FeedbackContext, FeedbackCollector

collector: FeedbackCollector
async with FeedbackContext(collector, operation="prediction") as ctx:
    result = await model.predict(input_data)
    ctx.set_result(result)
# Context data is stored for later feedback submission
```

## Best Practices

- Use `ASYNC_PROCESSING=true` (default) for non-blocking feedback pipelines.
- Always provide `session_id` in feedback context for session-scoped queries.
- Enable `store_raw_payloads` in production for audit traceability (increases storage).
- Wire `CachedFeedbackStore` for read-heavy dashboards — cache is invalidated on writes.
- Use `FeedbackService.submit_feedback()` for trace-id-correlated feedback from production traffic.
- Register custom processors for domain-specific feedback routing.

## Next Steps

- [How-Tos](./HOWTOS.md) — practical recipes
- [Architecture](./ARCHITECTURE.md) — internal design
- [Configuration](./CONFIGURATION.md) — every config key
