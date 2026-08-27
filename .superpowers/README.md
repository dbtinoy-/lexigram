# .superpowers — Program Index

Three active programs. Specs describe **what & why**; plans describe
**how, task-by-task**; templates/checklists keep execution uniform.

## 0. Codegen uplift (2026-08-26)

Framework-pattern parity for `lexigram.codegen` (staging, options,
overrides, option descriptors). Feeds the builder program directly.

| Document | Role |
|---|------|
| [`specs/2026-08-26-codegen-uplift-design.md`](specs/2026-08-26-codegen-uplift-design.md) | What & why — Schematics/Rails/Laravel/Phoenix mechanisms mapped to lexigram |
| [`plans/2026-08-26-codegen-uplift-plan.md`](plans/2026-08-26-codegen-uplift-plan.md) | Tasks 0–7 · **status: Tasks 1–6 committed, Task 7 gates done at session close** |

Sequencing: uplift Tasks 1–3 land before builder Task 3.

## 1. Repository hardening (2026-08-22)

Bug-hunt-driven defect-class remediation. Index + specs:
[`specs/README.md`](specs/README.md).

## 2. Demo showcase program (2026-08-25)

Turn `demos/` into the canonical showcase of Lexigram coding, then grow it.

| Document | Role |
|---|------|
| [`specs/2026-08-25-demos-code-alignment.md`](specs/2026-08-25-demos-code-alignment.md) | **The Demo Blueprint** — binding pattern for all demos: application.yaml-first config, logging, ambient capabilities, Result/ProblemDetail, testing standard |
| [`specs/2026-08-25-demo-wave-2-overview.md`](specs/2026-08-25-demo-wave-2-overview.md) | Wave-2 roster (8 new demos + 1 retrofit), ports, conventions, build order |
| [`plans/2026-08-25-waves-master-roadmap.md`](plans/2026-08-25-waves-master-roadmap.md) | **Execution tracker** — phases, status, definition of done |
| [`plans/2026-08-25-wave0-demos-alignment-plan.md`](plans/2026-08-25-wave0-demos-alignment-plan.md) | Wave 0: retrofit existing fleet to the Blueprint |
| [`templates/demo-acceptance-checklist.md`](templates/demo-acceptance-checklist.md) | Copy-per-demo checklist (Blueprint §6 expanded) |

### Wave-2 specs → plans

| Demo | Spec | Plan | Port |
|------|------|------|------|
| Reproducibility Lab (retrofit) | `demo-reproducibility-lab.md` | `wave2-reproducibility-lab-plan.md` | 7076 |
| Router Playground | `demo-router-playground.md` | `wave2-router-playground-plan.md` | 7077 |
| Workflow Studio | `demo-workflow-studio.md` | `wave2-workflow-studio-plan.md` | 7080 |
| Webhook Hub | `demo-webhook-hub.md` | `wave2-webhook-hub-plan.md` | 7078 |
| Flag Console | `demo-flag-console.md` | `wave2-flag-console-plan.md` | 7086 |
| Trace Waterfall | `demo-trace-waterfall.md` | `wave2-trace-waterfall-plan.md` | 7095 |
| Eval Leaderboard | `demo-eval-leaderboard.md` | `wave2-eval-leaderboard-plan.md` | 7085 |
| Multi-Tenant Notes | `demo-multi-tenant-notes.md` | `wave2-multi-tenant-notes-plan.md` | 7087 |
| MCP Tool Server | `demo-mcp-tools.md` | `wave2-mcp-tools-plan.md` | 7090 |

(All spec files live in `specs/`, plan files in `plans/`, prefix
`2026-08-25-`.)

## Execution order

Wave 0 → Reproducibility Lab → Router → Workflow Studio → Webhook Hub →
Flag Console → Trace Waterfall → Eval Leaderboard → Tenant Notes → MCP Tools.
Track progress in the roadmap file; never start a later phase with an earlier
one open.
