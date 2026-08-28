# 🔁 feedback-loop — ratings become regression suites

> Close the quality loop without a model call: users rate canned answers,
> low ratings promote into an evaluation dataset, the real harness scores
> it, and a seeded tracker persists the run for error analysis.

## What it proves

- **Feedback capture** — `FeedbackCollector.collect_rating` with trace-id
  context, aggregated per owner (in-memory degraded mode: no DB bound)
- **Ratings → dataset** — ≤2-rated exchanges become duck-typed
  `ScoredSample`s through the verified harness contract
- **Real harness runs** — `QAEvaluator` via `EvaluationHarness`; failing
  set is exactly the two deliberately poor answers
- **Seeded tracking** — same name+seed+config ⇒ same run id
  (`make_run_id`); artifacts under `.runs/`
- **Error analysis** — score mean/min/max + top failures from the tracker

## How results are derived (no LLM)

This demo uses **no language model**. A static `BOT` dictionary in
`repository/bot.py` maps question keys to pre-written answer strings.
`LoopService.ask()` looks up the key and returns the canned answer with a
stable trace ID. Low-rated answers are promoted to a regression dataset and
scored by `QAEvaluator` (keyword overlap). No model calls, no network —
all outputs are deterministic.

## Layout — read it in this order

Start at the composition root and follow the wiring outward.
Each file has teaching comments explaining the Lexigram convention it follows.

| # | File | Lesson |
|---|------|--------|
| 1 | `src/feedback_loop/app.py` | ⭐ Composition root: config → modules → providers |
| 2 | `src/feedback_loop/main.py` | Lifecycle: boots app, runs web server |
| 3 | `src/feedback_loop/di/provider.py` | `register()` (bind) vs `boot()` (initialize); DI wiring |
| 4 | `src/feedback_loop/errors.py` | Domain errors subclassing contracts |
| 5 | `src/feedback_loop/schemas.py` | Request DTOs as `DomainModel` (frozen dataclasses) |
| 6 | `src/feedback_loop/services/loop_service.py` | Core orchestration: ask → rate → stats → regress → report |
| 7 | `src/feedback_loop/services/regression.py` | Dataset builder: ratings → evaluation samples |
| 8 | `src/feedback_loop/repository/bot.py` | Canned Q→A registry; in-memory protocol impl |
| 9 | `src/feedback_loop/controllers/api.py` | Result-returning handlers → auto HTTP status mapping |
| 10 | `src/feedback_loop/ui/pages.py` | Page controllers: serve HTML/assets only, no logic |

```
src/feedback_loop/
├── __init__.py          # Public exports
├── __main__.py          # Thin shim → main.main()
├── main.py              # Entry point: boots app, runs web server
├── app.py               # Composition root: modules + providers
├── errors.py            # Domain errors (subclass contracts)
├── schemas.py           # Request DTOs (DomainModel)
├── controllers/
│   └── api.py           # JSON API endpoints
├── services/
│   ├── loop_service.py  # Ask → rate → stats → regress → report
│   └── regression.py    # Dataset builder
├── repository/
│   └── bot.py           # Canned Q→A registry
├── di/
│   └── provider.py      # DI wiring
└── ui/
    ├── pages.py         # Page controller (serves HTML)
    ├── views/
    │   └── loop.html    # Single-page console
    └── static/
        ├── app.js       # Vanilla-JS client
        └── style.css    # Stylesheet
```

## Run

```bash
# Web console
PYTHONPATH=demos/feedback-loop/src uv run python -m feedback_loop
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/ask` | Answer a canned question, issuing its stable trace id |
| POST | `/api/rate` | Capture a rating for a previously issued trace id |
| GET | `/api/stats/{owner}` | Aggregate this owner's captured ratings |
| POST | `/api/regress` | Promote low-rated exchanges into a tracked regression run |
| GET | `/api/report/{run_id}` | Post-hoc error analysis for a tracked run |

## Lexigram Concepts

| Concept | Where in this demo | Your app |
|---------|-------------------|----------|
| Composition root | `app.py` | Replace controllers/providers list |
| Module pattern | `FeedbackModule` | Add your own modules |
| Provider lifecycle | `di/provider.py` | Replace with your registrations |
| Result<T,E> pattern | `controllers/api.py` | Return Result from handlers |
| Protocol binding | `repository/bot.py` | Swap impl for real Q&A backend |
| Constructor injection | Everywhere | Declare deps as typed params |
| Domain models | `schemas.py` | Frozen dataclasses as request DTOs |
| Registry dispatch | `repository/bot.py` | Keyed strategy selection |

## Tests

```bash
uv run pytest demos/feedback-loop/tests -q
```

