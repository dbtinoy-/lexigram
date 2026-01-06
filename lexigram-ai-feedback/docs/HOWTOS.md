---
title: lexigram-ai-feedback How-Tos
description: Task-oriented recipes for AI feedback collection.
---

## Submit a Rating

```python
from lexigram.ai.feedback import FeedbackCollector

collector: FeedbackCollector
feedback_id = await collector.collect_rating(
    rating=5,
    context={"model": "gpt-4o", "session_id": "sess-xyz"},
    metadata={"user_id": "user-42"},
)
```

## Submit a Text Comment

```python
feedback_id = await collector.collect_text(
    text="The response was too technical. Please simplify.",
    context={"query": "explain quantum computing"},
)
```

## Submit a Correction

```python
feedback_id = await collector.collect_correction(
    original="Lexigram is a framework.",
    corrected="Lexigram is an async Python framework.",
    context={"model_id": "gpt-4o-2024-05-13"},
)
```

## Submit a Label for ML Training

```python
feedback_id = await collector.collect_label(
    label="NOT_SPAM",
    input_data="Hey, check out this article",
    context={"classifier": "email-filter-v2"},
)
```

## Query Feedback Statistics

```python
from lexigram.ai.feedback import FeedbackService

service: FeedbackService
stats = await service.get_feedback_stats(
    model="gpt-4o",
    provider="openai",
)
print(f"Total: {stats['total_count']}, Avg: {stats['average_rating']}")
```

## Wire Cached Feedback Storage

Ensure both a database provider and cache backend are registered:

```python
from lexigram.sql import DatabaseModule
from lexigram.cache import CacheModule
from lexigram.ai.feedback import FeedbackModule

app = Application(name="my-app")
app.add_module(DatabaseModule.configure("postgresql://localhost/mydb"))
app.add_module(CacheModule.configure())
app.add_module(FeedbackModule.configure())
await app.start()
# FeedbackCollector uses CachedFeedbackStore automatically
```

## Register a Custom Feedback Processor

```python
from lexigram.ai.feedback.processors.processor_registry import (
    FeedbackProcessorRegistry,
    FeedbackProcessor,
)

class UrgencyProcessor(FeedbackProcessor):
    async def process(self, value, context, collector):
        urgency_score = len(value) / 1000
        return await collector.collect_rating(
            rating=urgency_score,
            context={**context, "type": "urgency"},
        )

registry: FeedbackProcessorRegistry
registry.register("urgency", UrgencyProcessor())
```

## Use the Web Middleware

```python
from lexigram.ai.feedback import FeedbackMiddleware, FeedbackCollector

collector: FeedbackCollector
middleware = FeedbackMiddleware(
    collector=collector,
    capture_inputs=True,
    capture_outputs=True,
)

# In your web app router
# app.post("/feedback", middleware.create_feedback_endpoint())

## Work with FeedbackItem Directly

Create, inspect, and serialize feedback items without a collector:

```python
from lexigram.ai.feedback import FeedbackItem, FeedbackType

item = FeedbackItem(
    feedback_type=FeedbackType.TEXT,
    value="Great response!",
    context={"session_id": "sess-abc", "model": "gpt-4o"},
    metadata={"user_id": "user-42"},
)
print(item.id)           # auto-generated UUID
print(item.created_at)   # auto-timestamped (UTC)
print(item.type)         # FeedbackType.TEXT

# Serialize to a dict for storage or transmission
payload = item.to_dict()
# {"id": "...", "type": "text", "value": "Great response!", ...}

# Deserialize from stored data
from datetime import datetime

restored = FeedbackItem(
    feedback_type=FeedbackType(payload["type"]),
    value=payload["value"],
    context=payload["context"],
    metadata=payload["metadata"],
    id=payload["id"],
    created_at=datetime.fromisoformat(payload["created_at"]),
)
```

## Use FeedbackContext for Scoped Operations

Wrap an operation in `FeedbackContext` to capture inputs, outputs, and metadata for correlated feedback submission:

```python
from lexigram.ai.feedback import FeedbackContext, FeedbackCollector

collector: FeedbackCollector

async with FeedbackContext(collector, operation="prediction") as ctx:
    ctx.set_input({"text": "Explain quantum computing"})
    result = await model.predict(ctx._input)
    ctx.set_result(result)
# Context data is stored under the auto-generated context_id
# for later feedback submission via the collector
```

## Handle Feedback Errors

Catch domain-specific exceptions from the feedback pipeline:

```python
from lexigram.ai.feedback import (
    FeedbackCollector,
    FeedbackError,
    FeedbackProcessingError,
    FeedbackValidationError,
)

collector: FeedbackCollector
try:
    feedback_id = await collector.collect_rating(
        rating=5,
        context={"session_id": "sess-abc"},
    )
except FeedbackValidationError as e:
    print(f"Invalid feedback data: {e}")
except FeedbackProcessingError as e:
    print(f"Processor pipeline failed: {e}")
except FeedbackError as e:
    print(f"Generic feedback error: {e}")
```

## Create a Feedback Dashboard Endpoint

```python
from lexigram.ai.feedback import FeedbackService
from lexigram.web import get, Controller

class FeedbackController(Controller):
    def __init__(self, service: FeedbackService) -> None:
        self.service = service

    @get("/api/feedback/stats")
    async def stats(self, model: str | None = None) -> dict:
        return await self.service.get_feedback_stats(model=model)
```
