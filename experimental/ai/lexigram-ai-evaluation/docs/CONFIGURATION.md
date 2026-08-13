# Configuration

Configuration options for this package.

---

## Overview

Configuration is loaded from YAML, environment variables, or programmatically via `EvaluationConfig`.

---

## Basic Example

```python
from lexigram.ai.evaluation.config import EvaluationConfig

config = EvaluationConfig(
    enabled=True,
    default_threshold=0.8,
    embedding_model="text-embedding-3-small",
)
EvaluationModule.configure(config)
```

---

## Options

| Option | Type | Default | Description |
|-------|------|---------|------------|
| `enabled` | bool | `True` | Enable the evaluation subsystem |
| `default_threshold` | float | `0.8` | Default pass threshold |
| `embedding_model` | str | `text-embedding-3-small` | Model for embeddings |
| `include_metadata` | bool | `True` | Include metadata in reports |
| `max_samples` | int | `None` | Max samples per run |
| `max_retries` | int | `3` | Max evaluation retries |
| `timeout_seconds` | int | `30` | Execution timeout |

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `LEX_AI_EVALUATION__ENABLED` | Enable/disable subsystem |
| `LEX_AI_EVALUATION__DEFAULT_THRESHOLD` | Default threshold |
| `LEX_AI_EVALUATION__EMBEDDING_MODEL` | Embedding model |
| `LEX_AI_EVALUATION__INCLUDE_METADATA` | Include metadata |
| `LEX_AI_EVALUATION__MAX_SAMPLES` | Max samples |
| `LEX_AI_EVALUATION__MAX_RETRIES` | Max retries |
| `LEX_AI_EVALUATION__TIMEOUT_SECONDS` | Timeout |

---

## Advanced Configuration

```python
from lexigram.ai.evaluation.config import EvaluationConfig

config = EvaluationConfig(
    enabled=True,
    default_threshold=0.95,
    embedding_model="text-embedding-3-large",
    max_samples=100,
    max_retries=5,
    timeout_seconds=60,
)
```

---

## Best Practices

- set thresholds based on your accuracy requirements
- choose embedding model based on your quality/speed needs
- configure timeouts appropriately for batch runs