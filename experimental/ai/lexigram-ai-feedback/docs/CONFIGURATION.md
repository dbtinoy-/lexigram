---
title: lexigram-ai-feedback Configuration
description: All config keys, types, defaults, and environment variables.
---

## Config Key

The configuration section is `ai_feedback` (loaded from the `ai_feedback:` key in `application.yaml`).

## Options

| Key | Type | Default | Env Variable | Description |
|-----|------|---------|-------------|-------------|
| `enabled` | `bool` | `true` | `LEX_AI_FEEDBACK__ENABLED` | Master on/off switch for all feedback collection |
| `async_processing` | `bool` | `true` | `LEX_AI_FEEDBACK__ASYNC_PROCESSING` | Process feedback handlers asynchronously in the background |
| `store_raw_payloads` | `bool` | `false` | `LEX_AI_FEEDBACK__STORE_RAW_PAYLOADS` | Persist raw incoming feedback payloads for auditing |

## Example YAML

```yaml
ai_feedback:
  enabled: true
  async_processing: true
  store_raw_payloads: false
```

## Production YAML

```yaml
ai_feedback:
  enabled: true
  async_processing: true
  store_raw_payloads: true  # enable for audit traceability
```

## Env Variable Override

```bash
export LEX_AI_FEEDBACK__ENABLED=true
export LEX_AI_FEEDBACK__ASYNC_PROCESSING=true
export LEX_AI_FEEDBACK__STORE_RAW_PAYLOADS=true
```

## Programmatic

```python
from lexigram.ai.feedback.config import FeedbackConfig

config = FeedbackConfig(
    enabled=True,
    async_processing=True,
    store_raw_payloads=False,
)
```

## Config Model

Loaded as a `BaseConfig` subclass (`FeedbackConfig`) by `FeedbackProvider`. The config instance is registered as a container singleton at `register()` time.

```python
cfg = await container.resolve(FeedbackConfig)
```

## Notes

- `store_raw_payloads` increases storage usage — enable only when audit requirements demand it.
- `async_processing` controls whether feedback processors run in background tasks or block the request path. Default `true` is safe for production.
