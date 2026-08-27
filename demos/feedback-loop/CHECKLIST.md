# Demo Acceptance Checklist (copy per demo)

> Copy this file into the demo's final task commit as
> `demos/<slug>/CHECKLIST.md` (delete any line that genuinely does not apply,
> never leave it half-ticked). Source of truth: Blueprint §6 in
> `specs/2026-08-25-demos-code-alignment.md`.

Demo: `feedback-loop` · Port: `8086` · Reviewed: `2026-08-25` (Wave 0 rollout)

## Configuration

- [x] `application.yaml` present with `web:` (server + csrf off) and `demo:`
      sections
- [x] Zero literal host/port/security values anywhere in `src/**.py`
      (`grep -rn "127.0.0.1\|enable_csrf" src/` → comments only)
- [x] `config.py` holds frozen `DemoConfig`; binding test covers defaults +
      yaml override
- [x] Env override documented in README (e.g. `RATES_PORT`)

## Code standards

- [x] `grep -rn "print(" src/` → zero hits
- [x] Walkthrough narration uses `get_logger` structured events
- [x] Wall-clock via `lexigram.primitives.clock`; ids via identity ambient;
      digests via hashing ambient
- [x] Deterministic scripted randomness annotated `# deterministic-by-design`
- [x] All non-2xx API paths return RFC-9457 ProblemDetail
- [x] Domain failures are `Result[T, SpecificError]`; no blind `.unwrap()`
- [x] Controllers stateless; providers logic-free; services behind contracts
- [x] No file over 500 lines (`make lint-loc` clean for this tree)

## Testing

- [x] Happy-path service test
- [x] Failure-path Result test
- [x] ASGI round-trip test for every public API route
- [x] fakes/mockito only at contract boundaries
- [x] `conftest.py` uses shared `install_demo_src` bootstrap (two lines)

## Gates

- [x] `uv run --group tooling pytest demos/<dir>/tests -q`
- [x] `uv run ruff check demos/<dir> && uv run ruff format --check demos/<dir>`
- [x] `uv run mypy demos/<dir>/src` (via `make type-demos`)
- [x] `python -m compileall -q demos/<dir>`
- [x] smoke entry exercised (`make smoke-demos`)

## Fleet & docs

- [x] Registered in hub `registry.py` (correct slug/port/module triple)
- [x] Makefile `DEMO_TEST_DIRS`, `DEMO_COMPILE_DIRS`, `smoke-demos` updated
- [x] `demos/README.md`: at-a-glance section + running command row
- [x] docs.lexigram.dev/demos table row added
- [x] README follows Blueprint skeleton (run / API / tour / standalone note)
