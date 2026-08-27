# Spec: Reproducibility Lab (llm-reproducibility retrofit)

Slug `llm-reproducibility` (unchanged) · package `llm_reproducibility` · **new port 7076** (`REPRO_PORT`)
Subsystems: `lexigram-ai-llm` relay mappers, `lexigram-contracts` metrics/tracing, `lexigram-ai-evaluation` run tracking

## Why

This demo is the odd one out: script entry (`run_experiment.py`) instead of
`python -m <pkg> serve`, no web console, no hub card, and a notebook that
duplicates the walkthrough. Retrofit it onto the standard demo pattern so it
matches every other demo in the fleet — and give determinism a visible,
clickable proof: same seed ⇒ byte-identical digest, on screen.

## Changes

1. **Pattern alignment**: root `module.py` (`WebModule.configure`, CSRF off),
   `main.py` with `serve` (:7076) and `demo` subcommands, controllers under
   `controllers/`, static console under `ui/` — same skeleton as
   resilient-rates.
2. **Notebook removed**: `reproducibility.ipynb` deleted; its guided-tour role
   moves to the console's walkthrough panel and the README's demo script.
3. **Script absorbed**: `run_experiment.py` logic extracted into
   `DigestExperimentService`; the file is deleted; Makefile (`smoke-demos`,
   `eval-reproduce`) and any CI references switch to module invocations.
4. **Improvements over the script**:
   - **Runs store** — every execution persisted in-memory (seed, config,
     digest, tokens, latency, cost, artifacts list) and browsable.
   - **One-click verify** — re-run a stored seed and compare digests; badge
     shows ✓ identical or ✗ drift with expected/actual.
   - **Ablation compare** — control vs `--ablate thinking` totals side-by-side
     with delta arrows (tokens, cost, duration).
   - **Error-analysis pane** — renders the per-run `analysis.json`
     (`ErrorAnalysis`) that previously required opening files.
   - **Hub integration** — registry entry flips `cli → web`; the fleet card
     links into `/demos/llm-reproducibility/`.

## API

| Route | Purpose |
|---|---|
| `POST /api/runs {seed?, ablate?}` | execute experiment (defaults from config.yaml), returns RunRecord |
| `GET /api/runs` | recent runs w/ digest chips |
| `POST /api/verify {seed}` | rerun + compare against stored digest for that seed |
| `GET /api/runs/{id}` | full record: metrics, checkpoints list, analysis |
| `GET /api/config` | effective experiment config readout |

Determinism contract preserved exactly: same seed + config ⇒ same digest;
verification failure is a first-class result, not an exception.

## Console

Left: run form (seed input, ablate toggle, config summary). Center: runs table
(digest chips monospace/click-copy, Verify buttons, ✓/✗ badges). Right tabs:
Ablation compare (delta table) · Error analysis · Config.

## Testing

Golden-digest fixtures for seeds {42, 7} and ablated variant; drift detection
via tampered store; ASGI round-trips for run→list→verify; hub count test
updated 13→14 web services; existing four tests migrated off script internals.
Gates unchanged.

## Non-goals

Real network/LLM calls (unchanged); artifact download endpoints (files stay on
disk); multi-config matrix runner UI.
