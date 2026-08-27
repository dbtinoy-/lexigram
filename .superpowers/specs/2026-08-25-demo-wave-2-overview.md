# Demo Wave 2 — Overview & Shared Conventions

> Eight new demos plus one retrofit showcasing framework subsystems that
> Wave 1 did not cover. Each has a focused spec (`specs/2026-08-25-demo-*.md`)
> and a TDD implementation plan (`plans/2026-08-25-wave2-*-plan.md`).

## The wave

| # | Demo | Directory / package | Port | Subsystems showcased |
|---|------|--------------------|------|----------------------|
| 1 | Router Playground | `demos/router-playground/` `router_playground` | 7077 | `lexigram-ai-relay-gateway`, routing contracts, resilience |
| 2 | MCP Tool Server | `demos/mcp-tools/` `mcp_tools` | 7090 | `lexigram-ai-mcp` (server + client), web |
| 3 | Workflow Studio | `demos/workflow-studio/` `workflow_studio` | 7080 | `lexigram-workflow` (sagas, state machines, durable history) |
| 4 | Trace Waterfall | `demos/trace-waterfall/` `trace_waterfall` | 7095 | `lexigram-ai-observability` |
| 5 | Eval Leaderboard | `demos/eval-leaderboard/` `eval_leaderboard` | 7085 | `lexigram-ai-evaluation`, `lexigram-testing` |
| 6 | Webhook Hub | `demos/webhook-hub/` `webhook_hub` | 7078 | `lexigram-webhook` (signing, retries, DLQ, rotation) |
| 7 | Flag Console | `demos/flag-console/` `flag_console` | 7086 | `lexigram-features` (FlagManager, gates, audit) |
| 8 | Multi-Tenant Notes | `demos/tenant-notes/` `tenant_notes` | 7087 | `lexigram-tenancy` (resolvers, isolation, lifecycle) |
| 9 | Reproducibility Lab (retrofit) | `demos/llm-reproducibility/` `llm_reproducibility` | **7076** (new) | `lexigram-ai-llm`, evaluation tracking — joins the standard pattern; notebook removed |

Ports are chosen clear of Wave 1 ({7000, 7071, 7073–7075, 8081–8086, 8090–8092}).
The retrofit (#9) also flips the hub registry's only `cli` entry to `web`
(hub tests assert 13 → 14 web services).

## Shared conventions (binding for every demo)

1. **Blueprint binding**: every demo follows
   `specs/2026-08-25-demos-code-alignment.md` — `application.yaml`-first
   configuration (zero literal host/port/security in Python), structured
   logging (no `print`), ambient clock/identity capabilities, Result +
   ProblemDetail error paths, shared test bootstrap. Wave 0 retrofits the
   existing fleet first; Wave 2 demos are born aligned.
2. **Pattern parity**: directory `demos/<slug>/` with `src/<pkg>/`
   (`module.py` root module wiring `WebModule.configure(controllers=[...])`),
   `tests/test_*.py`; test bootstrap via the shared helper from Blueprint §5
   once Wave 0 lands.
3. **Offline-deterministic**: no external network ever. LLM-shaped behaviour
   comes from scripted/fake clients (see `support-agent`,
   `llm-reproducibility`). Every failure mode is a button or seeded scenario,
   never a coincidence.
4. **Vanilla-JS consoles**: `ui/pages.py` static controller + `ui/views/*.html`
   + `ui/static/{style.css,app.js}`. Root-relative asset paths are fine — the
   demo-hub subsite shim rewrites HTML attributes and JS navigations.
   Avoid dynamic URL construction outside `fetch`/`location.href` idioms.
5. **Fleet integration**: register the child in
   `demo-hub/src/demo_hub/services/registry.py` (slug, name, port, blurb,
   demo_dir, module_path, module_name), add to Makefile `DEMO_TEST_DIRS`,
   `DEMO_COMPILE_DIRS`, `smoke-demos` import line, and demos README table +
   running section. Hub card links work automatically via `/demos/<slug>/`.
6. **Gates per demo**: `uv run --group tooling pytest demos/<dir>/tests -q`;
   `uv run ruff check . && uv run ruff format .`; `compileall`; `type-demos` mypy gate (from Wave 0); boot smoke
   (`python -c "import <pkg>.main"` or a scripted walkthrough).
7. **Commits**: emoji convention from AGENTS.md, one logical unit per commit
   (feature + its tests together). No worktrees/branches. Commit by pathspec.
8. **Docs**: after implementation, add a row to
   `lexigram-docs/src/content/docs/demos/index.md` and a section in
   `demos/README.md` ("at a glance" + running commands).

## Suggested build order

Reproducibility Lab retrofit → Router Playground → Workflow Studio →
Webhook Hub → Flag Console → Trace Waterfall → Eval Leaderboard →
Tenant Notes → MCP Tools.

Rationale: the retrofit is small and immediately normalizes the fleet (every
demo born from one blueprint); Router next because its fake-provider plumbing
gets reused; MCP last because it dogfoods the largest surface area against
finished demos' tools.
