# Spec: Eval Leaderboard

Slug `eval-leaderboard` · package `eval_leaderboard` · port 7085 (`EVAL_PORT`)
Subsystems: `lexigram-ai-evaluation` (harness, evaluators, metrics), `lexigram-testing`

## Story

Three candidate "models" (scripted, deterministic) compete on two datasets.
Click Run suite → a run executes case-by-case with live progress, then the
leaderboard reorders with scores, per-metric breakdowns, and a regression
gate verdict. Open any two runs side-by-side: identical cases, differing
verdicts, diff highlighted. A "CI gate" panel evaluates thresholds and shows
the exact check that fails — evaluation as an enforceable pipeline stage.

## Candidates (scripted clients)

| Model | Behaviour |
|---|---|
| `gpt-base` | solid exact answers, slow-ish latency |
| `mini-fast` | paraphrases (fails strict match, passes semantic), fastest |
| `regressed-v2` | current champ minus one broken case — exists to make gates red |

## Datasets & metrics

- `support-faq` (8 cases) — exact_match, contains, latency_budget(<250 ms)
- `extract-json` (6 cases) — json_schema_valid, field_accuracy

Harness + evaluators come from `lexigram-ai-evaluation`; scripted model
clients implement its model-call seam like `lexigram-testing` fakes (recon
task pins harness API).

## Architecture

- `CandidatesService` — registry of scripted clients.
- `RunsService` — executes suite via evaluation harness; persists
  `EvalRun {id, suite, model, started, results[case→scores], aggregates,
  gate_verdict}` in-memory store; emits progress events to a simple pollable
  cursor (no SSE needed).
- `GateService` — threshold config per suite (e.g. exact_match ≥ 0.85,
  p95 latency ≤ 400 ms); produces pass/fail with failing-check details.
- `LeaderboardController` — API + UI.

## API

| Route | Purpose |
|---|---|
| `POST /api/runs {suite, model}` / `GET /api/runs/{id}/progress` | start & poll |
| `GET /api/leaderboard?suite=` | ranked aggregates across latest run per model |
| `GET /api/runs/{id}` | full case-level results |
| `GET /api/diff?left=&right=` | case-by-case comparison of two runs |
| `POST /api/gate {run_id}` | evaluate CI gate for a run |
| `GET /api/suites` | suites, cases count, metric set, thresholds |

## Console

Left: suite/model pickers + Run button + progress bar. Center: leaderboard
table (rank, model, score bars, per-metric chips); run detail drawer with
case table. Right: Gate card (green/red checks). Diff view: two columns,
mismatched rows tinted.

## Testing

Unit: each evaluator against known pairs; gate logic boundary cases;
persistence round-trip. Integration: full run produces aggregates matching
hand-computed fixture; regressed-v2 trips exact_match gate. Progress cursor:
poll returns increasing completed counts, terminal status once. Console smoke.

## Non-goals

Real models/network; dataset authoring UI; historical trend charts beyond
per-run storage.
