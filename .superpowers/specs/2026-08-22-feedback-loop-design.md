# Demo Spec — `feedback-loop` (iterate II: feedback → regression eval, CLI)

**Date:** 2026-08-22
**Status:** Draft for review
**Showcases:** `lexigram-ai-feedback` (capture, aggregate) + `lexigram-ai-evaluation` (datasets, harness, experiment tracking, error analysis).
**Portfolio position:** Fifth AI demo — second half of the "iterate" story: user feedback becomes a reproducible regression suite.
**Structure rationale:** **No UI.** The artifact is a sequential pipeline with printed reports — same shape rationale as event-driven-orders (argparse CLI) and llm-experiment (scripted runs). Flat house Pattern-2 package, CLI-first.

---

## 1. Scenario

A mini support bot answers questions with canned replies (two good, two
deliberately poor). A user rates each answer 1–5. Low-rated exchanges are
promoted into an evaluation dataset, run through the harness, tracked as a
seeded experiment run, and summarized via error analysis — closing the
loop: **bad ratings today ⇒ enforced regression tomorrow.**

Fully offline: feedback stays in its in-memory mode (provider degrades to
memory when no database is bound — the intended configuration here);
evaluators and tracker are pure-Python.

## 2. Layout

```
demos/feedback-loop/
├── conftest.py                        # sys.path shim only (no app/client — no server)
├── README.md
└── src/feedback_loop/
    ├── __init__.py
    ├── __main__.py                    # python -m feedback_loop
    ├── main.py                        # argparse: ask / rate / stats / regress / report / demo
    ├── module.py                      # @module FeedbackLoopModule
    ├── bot.py                         # BOT registry: question_key → canned answer (+ trace ids t1..t4)
    ├── regression.py                  # low-rated items → EvaluationDataset builder (ScoredSample)
    ├── loop_service.py                # LoopService orchestration
    ├── di/provider.py                 # LoopProvider (internal)
    └── errors.py                      # UnknownTraceError etc. (typed CLI-boundary errors)
tests/
├── __init__.py
├── test_bot.py                        # registry surface + trace ids
├── test_regression.py                 # ≤2 threshold, field mapping, owner filter
├── test_loop_service.py               # capture→stats→regress→report e2e on tmp_path
└── test_cli.py                        # parser routing + run() smoke via capsys
```

## 3. Module wiring

```python
@module()
class FeedbackLoopModule(Module):
    @classmethod
    def configure(cls, experiment_dir: str = ".runs") -> DynamicModule:
        return DynamicModule(
            module=cls,
            imports=[
                FeedbackModule.configure(FeedbackConfig(async_processing=False)),
                EvaluationModule.configure(EvaluationConfig(
                    default_threshold=0.6,
                    default_seed=7,
                    experiment_dir=experiment_dir,
                )),
            ],
            providers=[LoopProvider],
            exports=[LoopService],
        )
```

- No `DatabaseProviderProtocol` bound ⇒ `FeedbackProvider.boot` logs
  `feedback_store_not_wired` and leaves collector/service in-memory — the
  intended mode, asserted by a wiring test.
- `experiment_dir=".runs"` keeps tracker artifacts demo-local; tests pass
  a tmp_path dir via `configure(experiment_dir=str(tmp_path))`.

`LoopProvider.boot()` resolves `FeedbackCollector`, `FeedbackProtocol`,
the harness binding, named evaluators (`criteria`, `qa`),
`ExperimentTrackerProtocol`, `CheckpointStoreProtocol` (all registered by
`EvaluationProvider.register()`; note `EvaluationHarness` is bound under
its concrete class — resolve whichever exists).

**Sample contract (verified):** the harness runner duck-types
(`sample.output if hasattr(sample, "output") else ""`, runner.py:49);
contracts' `EvaluationSample` has no `output` field ⇒ `regression.py`
defines a local frozen dataclass mirroring it plus `output: str`.

## 4. Components

| Component | Implementation |
|---|---|
| `bot.py` | dict registry `question_key → answer`, fixed trace ids (`t1..t4`); two answers deliberately miss obvious quality bars |
| rating flow | `collector.collect_rating(rating, owner_id=…, context={"trace_id", "question_key", "answer"})` returns item id |
| `regression.py` | items rated ≤2 → dataset of ScoredSample(id=trace, input=question, output=answer, reference=missed bar); owner-filtered; empty ⇒ empty dataset handled gracefully |
| scoring | `CriteriaEvaluator([{type:"contains", expected:…}])` for bar-checks + `QAEvaluator` keyword overlap for open questions — both offline; embedding evaluator unused |
| tracking | `tracker.start/log_metric/finish` seeded via config; run id stable across invocations (`make_run_id(name, seed, config)`); `ErrorAnalysis(tracker).report(run_id)` summary |

## 5. CLI & demo acts

```
uv run python -m feedback_loop ask good-refund --owner alice     # prints answer + trace id
uv run python -m feedback_loop rate t1 1 --comment "wrong policy" --owner alice
uv run python -m feedback_loop stats --owner alice               # count / average / by-type
uv run python -m feedback_loop regress --owner alice             # builds dataset, runs harness both evaluators, starts tracked run, prints RunReport table
uv run python -m feedback_loop report <run_id>                   # score mean/min/max, error kinds, top failing cases
uv run python -m feedback_loop demo                              # full loop: 4 asks → 4 ratings (2 low) → stats → regress → report
```

`demo` ends asserting (in printout) that exactly the two poor answers are
the failing samples.

## 6. Error handling

- Unknown trace id / out-of-range rating ⇒ typed package errors
  caught at CLI boundary, printed, exit code 1.
- Harness `Result` unwrapped after `is_ok()`; tracker I/O errors propagate
  (infrastructure).
- Owner scoping everywhere — bob's ratings never enter alice's dataset.

## 7. Tests

- `test_bot.py` — registry keys, trace id stability.
- `test_regression.py` — threshold selection, sample mapping incl.
  local `output` field, owner filtering, empty-dataset edge.
- `test_loop_service.py` — end-to-end on tmp_path experiment dir:
  deterministic run id across identical invocations, exact report numbers,
  failing set == {poor answers}, degraded-mode wiring asserted (collector
  store stays None).
- `test_cli.py` — parser routing; `run(args)` smoke per subcommand via
  capsys; error paths exit non-zero.

## 8. Integration

Makefile:114-115 append `demos/feedback-loop/tests` /
`demos/feedback-loop`; demos/README.md section (CLI commands shown).
`.gitignore`: add `demos/feedback-loop/.runs/`.

## 9. Acceptance criteria

- [ ] `PYTHONPATH=demos/feedback-loop/src uv run python -m feedback_loop
      demo` completes offline, byte-stable stdout (run ids stable).
- [ ] Same seed ⇒ same run id ⇒ identical reports across invocations.
- [ ] `make check-demos` green; ruff/format clean; files <500 LOC;
      changes confined to `demos/**` + `Makefile` (+ one .gitignore line).
- [ ] Own commit(s) including tests.

## 10. Gotchas

- `FeedbackModule` exports only `FeedbackProtocol`; the collector resolves
  as concrete class (registered singleton) — no collector protocol exists.
- Degraded mode: verify actual no-store behavior when ratings flow through
  `FeedbackService`; if its store-less path drops data, route all captures
  through `FeedbackCollector` and compute stats from collector queries —
  decided at implementation against provider code.
- `async_processing=False` keeps capture synchronous/deterministic.
- Keep `.runs/` artifacts out of byte-stability assertions — filesystem
  state, not stdout.
