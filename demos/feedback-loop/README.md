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

## Layout

House flat structure, CLI-first (event-driven-orders anatomy). State is
per-process; the `demo` subcommand plays the whole loop.

## Run

```bash
PYTHONPATH=demos/feedback-loop/src uv run python -m feedback_loop demo
# subcommands: ask / rate / stats / regress / report / demo / serve
PYTHONPATH=demos/feedback-loop/src uv run python -m feedback_loop serve   # web console :8086
```

## Tests

```bash
uv run pytest demos/feedback-loop/tests -q
```

