# Guide

Learn how to use this package effectively.

---

## Overview

The AI Evaluation package provides evaluator implementations and a harness for benchmarking AI models. Use it to test model outputs against expected answers, criteria, or semantic similarity.

---

## Core Concepts

- **Evaluator** — scoring function that compares model output to ground truth
- **EvaluationHarness** — runner that executes evaluations against a dataset
- **EvaluationSample** — single test case with input, expected output, and metadata
- **EvaluationDataset** — collection of samples for batch evaluation

---

## Typical Usage

```python
from lexigram import Application
from lexigram.di.module import Module, module
from lexigram.ai.evaluation import (
    EvaluationModule,
    EvaluationDataset,
    EvaluationSample,
)

# Define test samples
dataset = EvaluationDataset(
    samples=[
        EvaluationSample(
            id="q1",
            input={"question": "What is 2+2?", "expected": "4"},
        ),
    ]
)

@module(imports=[EvaluationModule.configure()])
class AppModule(Module):
    pass

app = Application(modules=[AppModule])
```

Explain:
- create dataset with samples
- resolve harness and run evaluation

---

## Common Patterns

### Pattern: Basic Criteria Evaluation

```python
from lexigram.ai.evaluation.evaluators import CriteriaEvaluator

evaluator = CriteriaEvaluator(
    target="exact_match",
    expected="4",
)
```

When to use exact string matching.

---

### Pattern: Embedding Similarity

```python
from lexigram.ai.evaluation.evaluators import EmbeddingDistanceEvaluator

evaluator = EmbeddingDistanceEvaluator(
    threshold=0.8,
    model="text-embedding-3-small",
)
```

For semantic similarity evaluation.

---

## Integration

How this package interacts with:
- `lexigram-ai-llm` — evaluate model outputs
- `lexigram-contracts` — uses `EvaluatorProtocol`, `EvaluationHarnessProtocol`
- `EvaluationProvider` — registers services

---

## Best Practices

- use appropriate evaluator for your metric
- set thresholds based on your accuracy requirements
- include metadata in run reports for debugging
- use `EvaluationModule.stub()` for testing

---

## Next Steps

- [How-Tos](./HOWTOS.md)
- [Configuration](./CONFIGURATION.md)
- [Architecture](./ARCHITECTURE.md)