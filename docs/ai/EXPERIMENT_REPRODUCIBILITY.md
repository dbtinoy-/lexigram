# Experiment Reproducibility

The AI evaluation subsystem makes every experiment run **bit-reproducible**:
the same config plus the same seed produces the same run id, the same
metrics, and the same digest — with no external experiment-tracking service.
This document describes how seeding works, what artifacts a run leaves
behind, and how to verify reproducibility end to end.

## The reproducibility contract

```
same config + same seed  =>  same run_id + same metrics + same digest
```

Determinism holds because every value that enters a run is derived from a
single PRNG (`random.Random(seed)`) or from sort-stable canonical JSON:

- Synthetic payloads, latencies, and token counts are drawn from the seeded
  PRNG in a fixed iteration order.
- Metrics snapshots key observations by name plus a canonical, sort-stable
  label key, so identical inputs always serialize identically.
- The run digest is `sha256` over the canonical JSON of
  `{params, metrics, result}` — any divergence flips the digest.

## Seed resolution order

`demos/llm-experiment/run_experiment.py` resolves the seed in this order:

1. `--seed <int>` CLI flag (highest priority),
2. the `LEXIGRAM_EXPERIMENT_SEED` environment variable,
3. the `experiment.seed` value in `experiment.yaml` (fallback).

```bash
# All three are equivalent:
python run_experiment.py --seed 7
LEXIGRAM_EXPERIMENT_SEED=7 python run_experiment.py
# …or seed: 7 in experiment.yaml
```

## Run ids and artifact storage

Run ids come from `lexigram.ai.evaluation.make_run_id(name, seed, variant)`:
a deterministic function of the experiment name, the seed, and the knob
configuration, so re-running an experiment lands on the *same* run
directory instead of accumulating duplicates.

Each run persists its artifacts under `<out>/runs/<run_id>/`:

| Path                 | Contents                                             |
|----------------------|------------------------------------------------------|
| `params.json`        | Resolved config, seed, ablation, config fingerprint. |
| `metrics.json`       | Sort-stable counters/gauges/histograms snapshot.     |
| `result.json`        | Per-iteration summaries and run totals.              |
| `trace.json`         | OpenTelemetry span names and attributes.             |
| `reproducibility.json` | The `run_id` / `digest` pair pinning the run.      |
| `checkpoints/*.json` | Digest-verified iteration checkpoints                |
|                      | (`FileCheckpointStore`) plus the totals checkpoint.  |
| `analysis.json`      | `ErrorAnalysis` summary of the run's error stream.   |

Checkpoints saved through `FileCheckpointStore` are content-addressed: the
stored SHA-256 digest is verified on load, so silently corrupted or
hand-edited artifacts are detected rather than trusted.

## Evaluation harness end to end

`EvaluationHarness` runs an `EvaluatorProtocol` over an
`EvaluationDataset` and produces a `RunReport` (totals, pass rate, average
score, per-sample results). The harness itself adds no randomness; when the
evaluator is seeded, two runs over the same dataset produce identical
reports:

```python
import asyncio

from lexigram.ai.evaluation import (
    EvaluationDataset,
    EvaluationHarness,
    EvaluationSample,
)


async def main() -> None:
    dataset = EvaluationDataset(
        name="demo",
        samples=[EvaluationSample(input="q", reference="a")],
    )
    report = await EvaluationHarness().run(dataset, my_seeded_evaluator)
    assert report.is_ok()
```

The integration test
`tests/integration/extension_tests/test_experiment_reproducibility.py`
locks this contract in: same-seed harness runs must yield identical
`RunReport` totals, run ids must be seed-stable, and checkpoint round-trips
must preserve payload and digest.

## Ablation runs

Adding `--ablate thinking` runs the control and the ablated variant at the
same seed, prints the metric deltas, and persists a digest-verified delta
record through `AblationRunner` — making feature-cost comparisons exactly
reproducible alongside the runs they compare.

## Verifying reproducibility

```bash
# Full demo flow: baseline + rerun; exits non-zero if digests diverge.
make eval-reproduce

# Or directly, with the env-var seed path:
LEXIGRAM_EXPERIMENT_SEED=7 python demos/llm-experiment/run_experiment.py
```

`run_experiment.py` logs `reproducibility=ok` when the second run's digest
matches the first, and exits `1` otherwise.
