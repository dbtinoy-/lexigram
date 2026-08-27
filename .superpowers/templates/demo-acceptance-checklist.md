# Demo Acceptance Checklist (copy per demo)

> Copy this file into the demo's final task commit as
> `demos/<slug>/CHECKLIST.md` (delete any line that genuinely does not apply,
> never leave it half-ticked). Source of truth: Blueprint §6 in
> `specs/2026-08-25-demos-code-alignment.md`.

Demo: `<slug>` · Port: `<port>` · Reviewed: `<date>`

## Configuration

- [ ] `application.yaml` present with `web:` (server + csrf off) and `demo:`
      sections
- [ ] Zero literal host/port/security values anywhere in `src/**.py`
      (`grep -rn "127.0.0.1\|enable_csrf" src/` → comments only)
- [ ] `config.py` holds frozen `DemoConfig`; binding test covers defaults +
      yaml override
- [ ] Env override documented in README (e.g. `RATES_PORT`)

## Code standards

- [ ] `grep -rn "print(" src/` → zero hits
- [ ] Walkthrough/CLI narration uses `get_logger` structured events
- [ ] Wall-clock via `lexigram.primitives.clock`; ids via identity ambient;
      digests via hashing ambient
- [ ] Deterministic scripted randomness annotated `# deterministic-by-design`
- [ ] All non-2xx API paths return RFC-9457 ProblemDetail
- [ ] Domain failures are `Result[T, SpecificError]`; no blind `.unwrap()`
- [ ] Controllers stateless; providers logic-free; services behind contracts
- [ ] No file over 500 lines (`make lint-loc` clean for this tree)

## Testing

- [ ] Happy-path service test
- [ ] Failure-path Result test
- [ ] ASGI round-trip test for every public API route
- [ ] fakes/mockito only at contract boundaries
- [ ] `conftest.py` uses shared `install_demo_src` bootstrap (two lines)

## Gates

- [ ] `uv run --group tooling pytest demos/<dir>/tests -q`
- [ ] `uv run ruff check demos/<dir> && uv run ruff format --check demos/<dir>`
- [ ] `uv run mypy demos/<dir>/src` (via `make type-demos`)
- [ ] `python -m compileall -q demos/<dir>`
- [ ] smoke entry exercised (`make smoke-demos`)

## Fleet & docs

- [ ] Registered in hub `registry.py` (correct slug/port/module triple)
- [ ] Makefile `DEMO_TEST_DIRS`, `DEMO_COMPILE_DIRS`, `smoke-demos` updated
- [ ] `demos/README.md`: at-a-glance section + running command row
- [ ] docs.lexigram.dev/demos table row added
- [ ] README follows Blueprint skeleton (run / API / tour / standalone note)
