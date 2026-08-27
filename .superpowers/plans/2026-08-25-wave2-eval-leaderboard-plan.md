# Plan: Eval Leaderboard (`demos/eval-leaderboard`)

> Conventions: wave-2 overview. Port 7085, pkg `eval_leaderboard`.

> **Task 0 — recon:** pin `lexigram-ai-evaluation` harness API (suite/case
> structures, evaluator registration, run execution entry point) and which
> `lexigram-testing` fakes fit scripted model clients. Record in
> `src/eval_leaderboard/runs_service.py` docstring.

> **Blueprint:** the acceptance checklist in `specs/2026-08-25-demos-code-alignment.md` §6 applies to this demo end-to-end.

**Goal:** deterministic suite runs over three scripted candidates; leaderboard, case diffing, and a CI-style gate that visibly fails on the regressed model.
**Architecture:** CandidatesService (3 scripted clients) · RunsService (harness execution → persisted EvalRun + pollable progress cursor) · GateService (threshold checks) · LeaderboardController.

### Task 1: Datasets + candidates — TDD
- [ ] Tests: fixture datasets (8 FAQ + 6 JSON cases) load with expected metric sets; each scripted client returns fixed outputs for fixed inputs (golden assertions incl. regressed-v2's broken case); latency simulation respects injected clock.
- [ ] Implement datasets.py + candidates. Gates. Commit `✨ feat(demos): eval fixtures + candidates`.

### Task 2: Run execution — TDD
- [ ] Tests: full run aggregates match hand-computed scores (exact_match 7/8 for base etc.); progress cursor advances monotonically to terminal status; run persisted and retrievable case-by-case.
- [ ] Implement RunsService over harness. Commit `✨ feat(demos): eval run engine`.

### Task 3: Gate + diff
- [ ] Tests: gate passes base run (thresholds from suites endpoint), fails regressed-v2 listing exact failing check names+values; diff of two runs marks only differing cases; diff against unknown id → 404 problem detail.
- [ ] Implement GateService + diff query. Commit `✨ feat(demos): gate + diff`.

### Task 4: HTTP + module
- [ ] Controller per spec table; integration: POST run → poll to done → leaderboard order [base, mini-fast, regressed] for support-faq; module wiring EVAL_PORT. Gates. Commit `✨ feat(demos): leaderboard API`.

### Task 5: Console
- [ ] Left controls + progress bar polling cursor; center leaderboard with score bars + metric chips; run drawer case table (✓/✗ chips); Gate card green/red with check list; two-column diff view with tinted mismatches.
- [ ] Manual walkthrough: run all three on both suites, open diff base↔regressed. Commit `✨ feat(demos): leaderboard console`.

### Task 6: Fleet + docs registration
- [ ] Registry/Makefile/README; `make check-demos`. Commit `📝 docs(demos): register eval-leaderboard`.
