---
title: "AI Evaluation"
description: "Evaluate LLM outputs and run reproducible experiments — evaluators, a harness, seed-stable tracking, checkpoints, ablations, and error analysis."
---

`lexigram-ai-evaluation` provides an AI evaluation framework: pluggable evaluators, a harness that runs them over datasets, and reproducible experiment tracking. Run ids are derived deterministically from the experiment name, seed, and knob config, so rerunning the same seed and knobs resumes the same run and produces byte-identical artifacts.

For full configuration details, see the [`lexigram-ai-evaluation` package docs](/packages/lexigram-ai-evaluation/).

---

## 1. The Contracts

Evaluation and experiment types come from `lexigram.contracts.ai`:

- `EvaluatorProtocol`, `EvaluationHarnessProtocol`, `EvaluationDataset`, `EvaluationSample`, `EvaluationResult`, `RunReport`, `EvaluationScoreType` — the evaluation surface.
- `ExperimentTrackerProtocol`, `CheckpointStoreProtocol`, `ExperimentConfig`, `ExperimentRun`, `MetricRecord`, `ErrorRecord`, `RunStatus`, `Checkpoint`, `AblationResult`, `AnalysisReport` — the reproducibility surface.

```python
from lexigram.contracts.ai.evaluation import (
    EvaluationDataset,
    EvaluationSample,
    EvaluatorProtocol,
)
from lexigram.contracts.ai.experiment import (
    CheckpointStoreProtocol,
    ExperimentConfig,
    ExperimentTrackerProtocol,
    RunStatus,
)
```

Every evaluator implements `EvaluatorProtocol`: it takes `input`, `output`, and `reference`, and returns `Result[EvaluationResult, Exception]` with a score in `[0.0, 1.0]`, a `score_type`, and feedback.

---

## 2. Evaluators

| Evaluator | Score type | What it checks |
|-----------|------------|----------------|
| `QAEvaluator` | `partial_match` | Whether the output answers the question, via keyword overlap with the reference (falls back to containment for numeric/stopword-only answers) |
| `StringDistanceEvaluator` | `string_distance` | Levenshtein, Jaccard, or cosine similarity against the reference |
| `EmbeddingDistanceEvaluator` | `semantic_similarity` | Cosine similarity of output and reference embeddings via `EmbeddingClientProtocol` |
| `TrajectoryEvaluator` | `trajectory_fidelity` | Whether an agent's JSON trajectory (`steps`, `final_state`) matches the expected path |
| `CriteriaEvaluator` | `exact_match` | Rule-based checks: `exact_match`, `contains`, `contains_all`, `regex` |

```python
from lexigram.ai.evaluation.evaluators import QAEvaluator, StringDistanceEvaluator

qa = QAEvaluator()
result = await qa.evaluate(
    input="What is the capital of France?",
    output="Paris",
    reference="Paris",
)
assert result.is_ok()
```

Criteria-based checks are declared, not coded:

```python
from lexigram.ai.evaluation.evaluators import CriteriaEvaluator

evaluator = CriteriaEvaluator(
    criteria=[
        {"type": "contains", "expected": "2024"},
        {"type": "regex", "pattern": r"\b\d{4}\b"},
    ]
)
```

---

## 3. The Harness

`EvaluationHarness` runs an evaluator over a dataset and produces a `RunReport` with the average score, pass rate (against a configurable threshold), and per-sample results.

```python
from lexigram.ai.evaluation.harness import EvaluationHarness
from lexigram.contracts.ai.evaluation import (
    EvaluationDataset,
    EvaluationSample,
)

dataset = EvaluationDataset(
    name="rag-baseline",
    samples=[
        EvaluationSample(
            id="1",
            input="What is the capital of France?",
            reference="Paris",
            metadata={},
        ),
    ],
    metadata={},
)

report = await EvaluationHarness(pass_threshold=0.7).run(dataset, qa)
if report.is_ok():
    summary = report.unwrap()
    print(summary.average_score, summary.passed_samples, summary.total_samples)
```

---

## 4. Reproducible Experiment Tracking

`LocalTracker` persists runs as JSON manifests plus JSONL metric/error streams under `<root>/runs/<run_id>/`. The run id is derived from the experiment name, seed, and canonicalized knob config:

```python
from lexigram.ai.evaluation import LocalTracker, make_run_id

assert make_run_id("probe", 42, {"model": "gpt-4o"}) == make_run_id(
    "probe", 42, {"model": "gpt-4o"}
)  # stable — never two ids for the same seed + knobs
```

Because the id is a pure function of config, calling `start()` again with the same seed and knobs **resumes the same run** instead of creating a duplicate — byte-identical artifacts on rerun.

```python
tracker = LocalTracker(root="runs")
run = await tracker.start(
    ExperimentConfig(
        name="probe",
        seed=42,
        config={"model": "gpt-4o", "temperature": 0.2},
    )
)
await tracker.log_metric(run.run_id, "score", 0.87, step=0)
await tracker.log_error(run.run_id, "LLM_RATE_LIMITED", "429", step=3)
await tracker.finish(run.run_id, RunStatus.COMPLETED)

snapshot = await tracker.snapshot(run.run_id)
# {"run_id": ..., "seed": 42, "metrics": {"score": 0.87}, "error_kinds": {...}}
```

---

## 5. Checkpoints

`FileCheckpointStore` persists run state under `<root>/runs/<run_id>/checkpoints/<slug>.json`. Every payload is written with a SHA-256 digest of its canonicalized JSON; loads re-verify that digest, so tampered or corrupted checkpoints are never returned as valid state.

```python
from lexigram.ai.evaluation import FileCheckpointStore

store = FileCheckpointStore(root="runs")
await store.save(run.run_id, "baseline", {"score": 0.87, "latency_ms": 120.5})
checkpoint = await store.load(run.run_id, "baseline")  # digest-verified
```

---

## 6. Ablations

`AblationRunner` compares a baseline checkpoint against an ablated one — a rerun with one knob removed or changed — and produces per-metric deltas plus a digest-stable `AblationResult`.

```python
from lexigram.ai.evaluation import AblationRunner

runner = AblationRunner(store)
result = await runner.compare(
    knob="thinking",
    baseline_run_id="probe-42-a1b2c3d4", baseline_slug="baseline",
    ablated_run_id="probe-42-9f8e7d6c", ablated_slug="ablated-thinking",
)
if result.is_ok():
    ablation = result.unwrap()
    print(ablation.deltas)  # {"score": -0.02, "latency_ms": -30.1}
```

---

## 7. Error Analysis

`ErrorAnalysis` aggregates a tracked run's metric and error records into an `AnalysisReport`: error-kind counts, score mean/min/max, and the most frequent errors — the input for post-hoc analysis of failed trials.

```python
from lexigram.ai.evaluation import ErrorAnalysis

report = await ErrorAnalysis(tracker).report(run.run_id)
print(report.error_kinds, report.score_mean, report.top_errors)
```

---

## 8. Wiring It Up

Register the subsystem through `EvaluationModule` — the container provides `EvaluatorProtocol`, `EvaluationHarnessProtocol`, `ExperimentTrackerProtocol`, and `CheckpointStoreProtocol`.

```python
from lexigram.ai.evaluation import EvaluationModule
from lexigram.ai.evaluation.config import EvaluationConfig
from lexigram.di.module import Module, module


@module(
    imports=[EvaluationModule.configure(EvaluationConfig(experiment_dir="runs"))]
)
class AppModule(Module):
    pass
```

`EvaluationModule.stub()` returns a variant with in-memory/no-op evaluator implementations for unit and integration tests.

`EvaluationConfig` defaults: `enabled=true`, `default_threshold=0.8`, `embedding_model="text-embedding-3-small"`, `default_seed=null`, `experiment_dir="runs"`, `max_retries=3`, `timeout_seconds=30`. Configure it from YAML under the `ai_evaluation` section:

```yaml title="application.yaml"
ai_evaluation:
  enabled: true
  experiment_dir: runs
  default_seed: 42
  default_threshold: 0.8
```

Resolve and use the services:

```python
from lexigram.contracts.ai.experiment import ExperimentTrackerProtocol

tracker = await container.resolve(ExperimentTrackerProtocol)
```

---

## 9. Reproducible Demo

`demos/llm-experiment` is a runnable, seeded end-to-end experiment: it generates prompts with a seeded RNG, pins prompt digests (SHA-256), runs LLM completion probes, records metrics and errors through `LocalTracker`, checkpoints intermediate state, and produces an `AblationResult` comparing a control run against an ablated one. It is CI-gated, so the reproducibility story is continuously verified rather than aspirational.