# AI Evaluation Subsystem

`lexigram-ai-evaluation` provides experiment tracking, evaluation
harnessing, ablation analysis, and post-hoc error analysis for AI workloads
— with reproducibility as a first-class contract (see
[EXPERIMENT_REPRODUCIBILITY.md](EXPERIMENT_REPRODUCIBILITY.md)).

## Architecture

```
lexigram-contracts/ai/evaluation.py    EvaluatorProtocol, EvaluationDataset,
                                       EvaluationSample, EvaluationResult,
                                       RunReport, EvaluationScoreType
lexigram-contracts/ai/experiment.py    ExperimentTrackerProtocol, ExperimentRun,
                                       MetricRecord, ErrorRecord, AnalysisReport,
                                       RunStatus
                ↑
lexigram-ai-evaluation                 Implementations (DI-registered):
├── harness/runner.py                  EvaluationHarness — dataset × evaluator → RunReport
├── tracking.py                        InMemoryExperimentTracker — runs, metrics, errors
├── checkpoints.py                     FileCheckpointStore — digest-verified snapshots
├── ablation.py                        AblationRunner — control vs. ablated deltas
├── analysis.py                        ErrorAnalysis — records → AnalysisReport
└── di/provider.py                     EvaluationProvider + EvaluationModule
```

## Core pieces

### EvaluationHarness

Runs an `EvaluatorProtocol` over an `EvaluationDataset` and returns
`Result[RunReport, Exception]`. The `RunReport` carries totals, pass rate,
average score, and per-sample results; `pass_threshold` decides which
scores count as passed.

```python
from lexigram.ai.evaluation import (
    EvaluationDataset,
    EvaluationHarness,
    EvaluationSample,
)

harness = EvaluationHarness(pass_threshold=0.6)
report = await harness.run(dataset, my_evaluator)
if report.is_ok():
    print(report.unwrap().metadata["pass_rate"])
```

### ExperimentTracker

`InMemoryExperimentTracker` implements `ExperimentTrackerProtocol`: start a
run (`start`), record scalars (`record_metric`) and failures
(`record_error`), snapshot mid-run state, `finish` with a `RunStatus`, and
`resume` a known run later. Runs are keyed by a stable run id from
`make_run_id(name, seed, config)`.

### Checkpoints

`FileCheckpointStore` persists iteration checkpoints under
`<root>/<run_id>/<label>.json`, content-addressed by SHA-256. Loads verify
the stored digest, so corrupted or hand-edited artifacts are rejected.

### AblationRunner

Runs a control configuration and an ablated variant at the same seed and
produces per-metric delta records — persisted through the checkpoint store
so comparisons stay digest-verified.

### ErrorAnalysis

Aggregates a tracked run's metric/error records into an `AnalysisReport`:
error-kind counts, `score` mean/min/max, and the most frequent error per
kind. Raises `AnalysisError` for runs unknown to the tracker.

```python
analysis = ErrorAnalysis(tracker)
report = await analysis.report(run_id)
print(report.error_kinds, report.score_mean)
```

## DI registration

```python
from lexigram.ai.evaluation import EvaluationModule

app.add_module(EvaluationModule.configure())
```

The module exports the tracker, harness, checkpoint store, ablation runner,
and analysis services for container resolution.

## Demo

`demos/llm-experiment/run_experiment.py` ties everything together: seeded
deterministic iterations, tracking, checkpoints, metrics, tracing, error
analysis, and a same-seed rerun that verifies digest identity.
