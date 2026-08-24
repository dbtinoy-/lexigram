# LLM Reproducibility Demo

A tiny, fully reproducible ML-style experiment over the Lexigram LLM relay
mapper — no API keys, no network, no external experiment-tracking service.

It answers a simple question in a **seeded, config-driven, auditable** way:
*what do conversions through `ClaudeMapper` cost and how do they behave?*
Every run records `AIMetrics` (requests, tokens, latency, cost) and
OpenTelemetry `AITracer` spans, pins itself with a SHA-256 digest, and
persists digest-verified checkpoints per iteration.

## Reproducibility path

1. **Config-driven** — `config.yaml` holds every knob (seed, model,
   iterations, sampling, recording switches).
2. **Seeded** — all synthetic payloads, latencies, and token counts come from
   `random.Random(seed)` (stdlib, stable).
3. **Digest-pinned** — `sha256(params + metrics + results)`; same seed +
   same config ⇒ identical `run_id` and digest.
4. **Tracked** — runs are tracked through `lexigram-ai-evaluation`:
   seed-stable run ids, metric/error streams (`metrics.jsonl`), and an
   `ErrorAnalysis` summary (`analysis.json`) per run.
5. **Checkpointed** — every iteration writes digest-verified
   `checkpoints/iteration_NN.json`; control and ablated variants also write
   totals checkpoints (`baseline.json`, `ablated-<knob>.json`).

Same-seed reruns are self-verified: the CLI refuses to exit 0 if the digest
drifts.

## Run it

```bash
# baseline, config seed (42)
python run_experiment.py

# explicit seed (env override also supported)
LEXIGRAM_EXPERIMENT_SEED=7 python run_experiment.py

# ablation: drop thinking blocks and compare deltas vs the control run
python run_experiment.py --seed 42 --ablate thinking
```

## Notebook

`reproducibility.ipynb` walks the same experiment interactively: config →
seeded runs → digest equality assertion → metrics table → ablation deltas.

## Artifacts

Each run writes `runs/<experiment>-<seed>-<confighash8>/`:

| File | Contents |
|---|---|
| `run.json` | tracking manifest (status, config, seed) |
| `metrics.jsonl` | metric stream (name → value per step) |
| `analysis.json` | `ErrorAnalysis` summary (kinds, top errors, score band) |
| `params.json` | pinned config + seed + ablation + config fingerprint |
| `metrics.json` | `AIMetrics` snapshot (counters, gauges, histograms) |
| `trace.json` | OTel span list (name + attributes) |
| `result.json` | per-iteration conversions + totals + loss count |
| `checkpoints/iteration_NN.json` | per-step checkpoints (digest-verified) |
| `checkpoints/baseline.json` | totals checkpoint of the control run |
| `checkpoints/ablated-<knob>.json` | totals checkpoint of the ablated run |
| `reproducibility.json` | run_id + digest |

## Why this design

- **Offline and deterministic** — usable in CI as a regression gate for the
  relay mappers (a mapper change that alters conversion output or cost will
  change the digest).
- **Native tracking** — runs are tracked through the framework's own
  evaluation subsystem (`lexigram-ai-evaluation`) instead of an external
  experiment-tracking service; adapters (MLflow, Weights & Biases,
  Prometheus) can be layered on without changing the harness.
- **Ablation support** — `--ablate thinking` runs a feature-off variant,
  reports metric deltas, and persists a digest-verified `AblationRunner`
  delta record across the control and ablated totals checkpoints.