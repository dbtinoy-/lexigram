# How-To Guides

Task-oriented recipes.

---

## Run a Basic Evaluation

```python
from lexigram import Application
from lexigram.di.module import Module, module
from lexigram.ai.evaluation import (
    EvaluationModule,
    EvaluationSample,
    BatchEvaluationResult,
)

# Simple evaluation example
sample = EvaluationSample(
    id="test-1",
    input={"query": "What is AI?"},
    expected={"answer": "Artificial Intelligence"},
)

async with Application.boot(
    modules=[EvaluationModule.configure()]
) as app:
    harness = await app.container.resolve("EvaluationHarnessProtocol")
    result: BatchEvaluationResult = await harness.run(sample)
```

---

## Use Criteria Evaluator

```python
from lexigram.ai.evaluation.evaluators import CriteriaEvaluator

evaluator = CriteriaEvaluator(
    target="exact_match",
    expected="42",
)
# Compares output using exact match
```

---

## Use Embedding Distance Evaluator

```python
from lexigram.ai.evaluation.evaluators import EmbeddingDistanceEvaluator

evaluator = EmbeddingDistanceEvaluator(
    threshold=0.85,
    model="text-embedding-3-small",
)
# Uses semantic embeddings for similarity
```

---

## Customize Threshold

```python
from lexigram.ai.evaluation.config import EvaluationConfig

config = EvaluationConfig(
    default_threshold=0.9,
    embedding_model="text-embedding-3-large",
)
EvaluationModule.configure(config)
```

---

## Advanced Scenario: Custom Evaluator

```python
from lexigram.contracts.ai.evaluation import EvaluatorProtocol
from lexigram.ai.evaluation import EvaluationResult
from dataclasses import dataclass

@dataclass
class CustomEvaluator(EvaluatorProtocol):
    name: str = "custom"

    async def evaluate(
        self,
        input: dict,
        output: str,
        expected: dict,
    ) -> EvaluationResult:
        # Your custom logic
        score = 1.0 if "correct" in output.lower() else 0.0
        return EvaluationResult(
            sample_id="",
            score=score,
            passed=score >= 0.8,
        )
```

---

## Notes

- Evaluators must implement `EvaluatorProtocol`
- Always set appropriate thresholds for your use case
- Embedding models require provider setup