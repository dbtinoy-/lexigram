# Demo Program Master Roadmap

> Single execution tracker for all demo work. Update checkboxes as tasks land;
> one row per plan. Detailed steps live in the linked plans — this file is the
> order + status view only.

## Order & status

| Phase | Plan | Scope | Status |
|-------|------|-------|--------|
| **Wave 0** | `2026-08-25-wave0-demos-alignment-plan.md` | Blueprint retrofit of existing fleet (yaml-first, logging, ambient, mypy gate) | ◐ in progress |
| A | └ Task A reference retrofit | resilient-rates | ☑ done (29 tests, mypy clean, checklist committed; + framework fix 1bc9240: cache stampede envelope/Result bugs) |
| B | └ Task B shared scaffolding | lexigram-testing bootstrap, 15 conftests | ☐ |
| C | └ Task C rollout batches ×5 | remaining 13 web demos | ☐ |
| D | └ Task D gates & CI | type-demos, print ban | ☐ |
| E | └ Task E docs inheritance | overview/README wiring (done in docs) | ☑ |
| **Wave 2** | per-demo plans below — born Blueprint-aligned | | |
| 1 | `2026-08-25-wave2-reproducibility-lab-plan.md` | llm-reproducibility retrofit (:7076), notebook removed | ☐ |
| 2 | `2026-08-25-wave2-router-playground-plan.md` | router-playground (:7077) | ☐ |
| 3 | `2026-08-25-wave2-workflow-studio-plan.md` | workflow-studio (:7080) | ☐ |
| 4 | `2026-08-25-wave2-webhook-hub-plan.md` | webhook-hub (:7078) | ☐ |
| 5 | `2026-08-25-wave2-flag-console-plan.md` | flag-console (:7086) | ☐ |
| 6 | `2026-08-25-wave2-trace-waterfall-plan.md` | trace-waterfall (:7095) | ☐ |
| 7 | `2026-08-25-wave2-eval-leaderboard-plan.md` | eval-leaderboard (:7085) | ☐ |
| 8 | `2026-08-25-wave2-multi-tenant-notes-plan.md` | tenant-notes (:7087) | ☐ |
| 9 | `2026-08-25-wave2-mcp-tools-plan.md` | mcp-tools (:7090), dogfoods fleet tools | ☐ |

## Definition of done (whole program)

- [ ] Every demo passes its plan's gates AND the Blueprint checklist
      (`templates/demo-acceptance-checklist.md`, one filled copy per demo
      committed next to its final task)
- [ ] `make check-demos type-demos` green from repo root
- [ ] Hub at :7000 lists all 23 demos, all cards green when fleet is up
- [ ] `demos/README.md` + docs.lexigram.dev/demos list every demo with correct
      ports and commands
- [ ] No `print(` under `demos/*/src`; zero literal host/port/security in any
      `module.py`

## Rules of engagement

- One phase at a time; never start Wave 2 #n before Wave 0 completes.
- Hidden complexity discovered mid-task → stop, upgrade that task's plan,
  note it here under the affected row.
- Commits follow AGENTS.md emoji convention; commit by pathspec; feature +
  tests together.
