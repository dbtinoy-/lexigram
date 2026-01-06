# lexigram-ai-evaluation

AI Evaluation framework for the Lexigram Framework.

---

## Overview

AI Evaluation framework for the Lexigram Framework. Provides evaluators harness, and metrics — all wired through the DI container via `EvaluationModule`. Zero-config usage starts with sensible defaults.

## Install

```bash
uv add lexigram-ai-evaluation
# Optional extras
uv add "lexigram-ai-evaluation[openai,anthropic]"
```

## Quick Start

```python
from lexigram import Application
from lexigram.di.module import Module, module

from lexigram.ai.evaluation import EvaluationModule
from lexigram.ai.evaluation.config import EvaluationConfig

@module(imports=[
    EvaluationModule.configure(
        EvaluationConfig(default_threshold=0.8)
    )
])
class AppModule(Module):
    pass

app = Application(modules=[AppModule])
if __name__ == "__main__":
    app.run()
```

## Configuration

> **Zero-config usage:** Call `EvaluationModule.configure()` with no arguments to use defaults.

### Option 1 — YAML file

```yaml
# application.yaml
ai_evaluation:
  enabled: true
  default_threshold: 0.8
  embedding_model: "text-embedding-3-small"
```

### Option 2 — Profiles + Environment Variables *(recommended)*

```bash
export LEX_AI_EVALUATION__DEFAULT_THRESHOLD=0.8
# Environment variables for each field
```

### Option 3 — Python

```python
from lexigram.ai.evaluation.config import EvaluationConfig
from lexigram.ai.evaluation import EvaluationModule

config = EvaluationConfig(
    default_threshold=0.8,
    embedding_model="text-embedding-3-small",
)
EvaluationModule.configure(config)
```

### Config reference

| Field | Default | Env var | Description |
|-------|---------|---------|-------------|
| `enabled` | `True` | `LEX_AI_EVALUATION__ENABLED` | Enable the evaluation subsystem |
| `default_threshold` | `0.8` | `LEX_AI_EVALUATION__DEFAULT_THRESHOLD` | Score threshold for passing |
| `embedding_model` | `text-embedding-3-small` | `LEX_AI_EVALUATION__EMBEDDING_MODEL` | Model for embedding evaluations |
| `include_metadata` | `True` | `LEX_AI_EVALUATION__INCLUDE_METADATA` | Include metadata in reports |
| `max_samples` | `None` | `LEX_AI_EVALUATION__MAX_SAMPLES` | Max samples per run |
| `max_retries` | `3` | `LEX_AI_EVALUATION__MAX_RETRIES` | Max retries for failed evaluations |
| `timeout_seconds` | `30` | `LEX_AI_EVALUATION__TIMEOUT_SECONDS` | Execution timeout |

## Module Factory Methods

| Method | Description |
|--------|-------------|
| `EvaluationModule.configure(config)` | Configure with explicit settings |
| `EvaluationModule.stub()` | No-op for testing |

## Key Features

- **5 evaluator types**: Criteria, QA, Embedding Distance, String Distance, Trajectory
- **Evaluation harness**: Run datasets against models with configurable evaluators
- **Metrics**: Pass/fail, score-based, and threshold evaluation
- **Embedding support**: Semantic similarity via embeddings

## Testing

```python
async with Application.boot(modules=[EvaluationModule.stub()]) as app:
    # your test code
    ...
```

## Key Source Files

| File | What it contains |
|------|-----------------|
| `src/lexigram/ai/evaluation/module.py` | `EvaluationModule.configure()` and `EvaluationModule.stub()` |
| `src/lexigram/ai/evaluation/config.py` | `EvaluationConfig` |
| `src/lexigram/ai/evaluation/di/provider.py` | `EvaluationProvider` — registers and boots |
| `src/lexigram/ai/evaluation/evaluators/` | Evaluator implementations |
| `src/lexigram/ai/evaluation/harness/` | Evaluation harness and runner |
| `src/lexigram/ai/evaluation/exceptions.py` | Full exception hierarchy |