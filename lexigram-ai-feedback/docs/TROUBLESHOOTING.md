---
title: lexigram-ai-feedback Troubleshooting
description: Common errors, causes, and fixes for AI feedback collection.
---

## `FeedbackValidationError` — Invalid feedback data

**Exception:** `lexigram.ai.feedback.exceptions.FeedbackValidationError`

**Cause:** Feedback data failed schema validation — e.g. text exceeding `MAX_FEEDBACK_TEXT_LENGTH` (10,000 characters), or rating outside `DEFAULT_RATING_MIN` (1.0) to `DEFAULT_RATING_MAX` (5.0).

**Fix:** Validate input before calling `collect_*` methods:

```python
if len(text) > 10000:
    raise ValueError("Feedback text too long")
```

## `FeedbackProcessingError` — Processor pipeline failure

**Exception:** `lexigram.ai.feedback.exceptions.FeedbackProcessingError`

**Cause:** A feedback processor raised an exception during `process()`. The error is caught and wrapped.

**Fix:** Check the inner exception for details. Ensure your custom processor handles expected failures gracefully:

```python
class SafeProcessor(FeedbackProcessor):
    async def process(self, value, context, collector):
        try:
            return await collector.collect_rating(rating=float(value), context=context)
        except (TypeError, ValueError):
            raise FeedbackProcessingError(f"Cannot parse rating: {value}")
```

## `FeedbackError` — Storage save failed

**Exception:** `lexigram.ai.feedback.exceptions.FeedbackError`

**Cause:** `DatabaseFeedbackStore.save()` failed — typically a database connection issue (`ConnectionError`, `TimeoutError`, `OSError`).

**Fix:** Check database connectivity. The store logs a structured error on failure:

```
feedback_save_failed  feedback_id=...  error=Connection refused
```

Ensure `DatabaseProviderProtocol` is correctly configured and the target database is reachable.

## Feedback items are not persisted

**Symptom:** `FeedbackCollector.get_feedback()` returns items, but they disappear after restart.

**Cause:** No `DatabaseProviderProtocol` was registered — feedback operates in memory-only mode. `FeedbackCollector._feedback` is lost on process restart.

**Fix:** Wire a database provider:

```python
from lexigram.sql import DatabaseModule

async with Application.boot(
    modules=[DatabaseModule.configure(...), FeedbackModule.configure()],
) as app:
    ...
```

## Feedback service returns empty stats

**Symptom:** `get_feedback_stats()` returns `{"total_count": 0, "average_rating": None, "by_type": {}}`.

**Cause 1:** No feedback has been submitted yet, or the store is not wired.

**Cause 2:** The store is in memory-only mode (no DB provider registered).

**Fix:** Collect feedback first, then query. Ensure a database provider is registered for persistent storage.

## Container resolution issues

**Symptom:** `ValueError` or `KeyError` when resolving `FeedbackProtocol` or `FeedbackCollector`.

**Cause:** `FeedbackProvider` was not registered (module not added, or `enabled=False`).

**Fix:** Ensure `FeedbackModule.configure()` is added to your application:

```python
app.add_module(FeedbackModule.configure())
```

Check `enabled` in config:

```yaml
ai_feedback:
  enabled: true
```

## Feedback processor not found in registry

**Symptom:** A custom processor defined with `@feedback_processor` is not invoked when feedback is collected.

**Cause:** The processor module was not imported before `FeedbackProvider.boot()` ran. The processor registry discovers processors via import-time decoration — if the module is never imported, the decorator never runs.

**Fix:** Import the processor module during application setup:

```python
import my_app.feedback.processors  # side effect: registers processors

async with Application.boot(modules=[FeedbackModule.configure()]) as app:
    ...
```

Verify the processor is registered:

```python
from lexigram.ai.feedback.processors import FeedbackProcessorRegistry

registry = await container.resolve(FeedbackProcessorRegistry)
print(registry.list_processors())
```

## Rating outside configured range not validated

**Symptom:** A rating of `6.0` is accepted even though `DEFAULT_RATING_MAX` is `5.0`.

**Cause:** Validation only occurs when `FeedbackCollector.collect_rating()` receives the rating value. If the value is already parsed as a float and passed directly, no range check may be applied depending on the pipeline path.

**Fix:** Validate the rating before passing to the collector:

```python
from lexigram.ai.feedback.constants import DEFAULT_RATING_MIN, DEFAULT_RATING_MAX


def validate_rating(rating: float) -> float:
    if rating < DEFAULT_RATING_MIN or rating > DEFAULT_RATING_MAX:
        raise FeedbackValidationError(
            f"Rating {rating} outside allowed range "
            f"[{DEFAULT_RATING_MIN}, {DEFAULT_RATING_MAX}]"
        )
    return rating
```

## Database store connection failure not surfaced

**Symptom:** `FeedbackCollector.collect_rating()` returns successfully, but the feedback item is not found after a subsequent `get_feedback()` call. No error is raised.

**Cause:** `DatabaseFeedbackStore.save()` catches all `ConnectionError`, `TimeoutError`, and `OSError` exceptions internally. A connection failure is logged as `feedback_save_failed` but never propagated to the caller.

**Fix:** Check the application logs for the `feedback_save_failed` message:

```bash
# Enable debug logging to see store errors
export LEX_LOG_LEVEL=DEBUG
```

If persistence is critical, periodically verify the store health:

```python
health = await feedback_store.health_check()
if health.status != "healthy":
    logger.warning("feedback_store_unhealthy", status=health.status)
```

## Processor execution order not guaranteed

**Symptom:** Two registered processors produce different results depending on execution order — e.g. an anonymization processor runs after a sentiment analysis processor that expects raw text.

**Cause:** The `FeedbackProcessorRegistry` does not guarantee processor ordering. Processors are stored in a dict keyed by name; iteration order depends on insertion order (Python 3.7+) but explicit ordering is not enforced.

**Fix:** If ordering matters, chain processors manually in a single custom processor:

```python
class OrderedFeedbackProcessor(FeedbackProcessor):
    async def process(self, value, context, collector):
        # Run anonymization first, then sentiment
        anonymized = await anonymize(value)
        result = await sentiment_analysis(anonymized)
        return result
```

Or modify the registry to use an ordered list of processor names.
