# Plan: Wave 0 — Fleet-wide Code Alignment

> Executes `specs/2026-08-25-demos-code-alignment.md` (the Demo Blueprint).
> **Runs before any Wave 2 build**; Wave 2 docs already updated to inherit it.
> Conventions (commits, gates, no-branch) per repo AGENTS.md and wave-2
> overview.

**Goal:** every existing demo passes the Blueprint acceptance checklist, with
YAML-first configuration as the headline change; the fleet becomes the
reference showcase of Lexigram coding.

### Task A: Reference retrofit — resilient-rates (flagship)

> Recon first: pin the exact yaml-binding idiom (`lexigram.config.base`
> `from_yaml(..., section=...)`) and confirm orchestrator injection of
> `WebConfig` via `config_key="web"` when `module.configure()` omits it;
> record both in `src/rates/module.py` docstring as THE reference example.

- [ ] Add `demos/resilient-rates/application.yaml` (server/csrf + demo knobs:
      scenario, cache ttl, default pair); create `config.py` `DemoConfig`
      frozen dataclass + binding test.
- [ ] Strip literals from `module.py`; provider injects `DemoConfig` into
      service/repository.
- [ ] Replace 22 `print()` in `main.py` walkthrough with structured logger
      events (act/title/data fields); verify CLI output stays readable.
- [ ] Ambient clock in `simulated_upstream.py` latencies (seeded Random kept,
      annotated deterministic-by-design).
- [ ] Sweep: ProblemDetail on all non-2xx; no blind unwrap; mypy clean.
- [ ] Acceptance checklist (spec §6) fully ticked; `make check-demos`.
- [ ] Commit `✨ feat(demos): blueprint reference retrofit — resilient-rates`.

### Task B: Promote shared scaffolding

- [ ] Add `lexigram.testing.demo.install_demo_src()` helper +
      `DemoConfig.bind(path)` test util in `lexigram-testing` (optional deps
      respected); unit tests in lexigram-testing.
- [ ] Convert all 15 `conftest.py` to two-liners using the helper.
- [ ] Commit `♻️ refactor(testing): shared demo bootstrap`.

### Task C: Mechanical rollout — remaining web demos

Per-demo sub-tasks (each = checklist from spec §6 + commit
`✨ feat(demos): blueprint align <slug>`), batched:

1. event-driven-orders, realtime-monitor (print removals + yaml + ambient ids)
2. rag-docs, support-agent, memory-chat
3. ai-guardrails, prompt-lab, feedback-loop
4. auth-web, auth-rbac, auth-apikeys, auth-mfa (ambient already partial —
   finish sweep)
5. demo-hub (yaml for its own port/registry knobs; subsite shim untouched)

Each batch: gates + `make check-demos` before committing the batch. Any demo
surfacing hidden complexity mid-rollout gets its own fix commit, not scope
creep.

### Task D: Gates & CI wiring

- [ ] Makefile: `type-demos` target (uv run mypy per demo src, incremental
      ignore file if needed) added to `check-demos`; grep gate `grep -L` style
      check banning `print(` under `demos/*/src` (allowlist: none).
- [ ] ci.yml: add type-demos step; keep runtime budget sane (<2 min added).
- [ ] Commit `👷 ci(demos): blueprint gates`.

### Task E: Wave-2 inheritance + docs closeout

- [ ] Edit wave-2 overview §Shared conventions: constraint #1 now reads "follow
      `specs/2026-08-25-demos-code-alignment.md` Blueprint" (yaml-first,
      logging, ambient); each wave-2 plan's Task 0 gains one line: "Blueprint
      checklist applies".
- [ ] Demos README: add "Architecture" section describing the Blueprint once
      instead of per-demo repetition.
- [ ] Full sweep: `make check-demos type-demos`, hub boot smoke, all 16 cards.
- [ ] Commit `📝 docs(demos): blueprint is binding for future demos`.

### Risk notes

- WebConfig yaml-injection semantics are the single unknown; Task A recon
  resolves it before any mass edit — if orchestrator injection proves unusable
  for demos, fallback is explicit `WebConfig.from_yaml_section()` inside
  configure() (still yaml-first, still zero literals).
- print→logger changes CLI output shape; smoke targets that assert on stdout
  must be checked (rates/orders `demo` walks are piped to /dev/null today —
  safe).
