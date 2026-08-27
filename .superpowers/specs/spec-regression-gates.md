# Spec: Framework Regression Gates

**Status:** approved · **Date:** 2026-08-22
**Plan:** `2026-08-22-regression-gates-plan.md`

## Problem

Three defect classes reached `main` this month because no automated gate
observed them:

1. **Stub-shadowed MRO resolution** — endpoint mixins of `AuthController`
   declared `render_admin` / `generate_breadcrumbs` as
   `raise NotImplementedError` typing stubs. They sat earlier in the MRO than
   `AdminController`'s real implementations, so every MFA page render raised
   at runtime. (Fixed in `95e9656`; the scanner prototype found zero other
   instances, but nothing prevents a regression.)
2. **Route shadowing by extension contributors** — the relay-gateway
   contributor registered `GET /health` before lexigram-web's canonical
   health route; Starlette first-match wins, so probes received the wrong
   payload and status contract. (Fixed in `32de8bb`.)
3. **Unresolvable DI construction discovered only under minimal containers** —
   `AuthController` failed to instantiate in the contributor test because
   inherited-`__init__` string annotations could not resolve. Provider-level
   smoke tests would have caught the composition break immediately.

## Requirements

### R1 — Stub-shadow gate (`dev/check_stub_shadows.py`)

- Runtime scanner: import every `lexigram*` package under `core/`,
  `packages/`, `experimental/` (tolerating import errors), walk each class's
  MRO, and fail when the *first* owner of an attribute is a function/property
  whose body is exactly `raise NotImplementedError` while a later owner has a
  real implementation.
- CLI shape mirrors siblings: `python dev/check_stub_shadows.py [--root PATH]`;
  exit `0` clean, exit `1` with one line per finding
  `CLASS.attr -> stub in Owner shadows real in RealOwner`.
- Skip names starting with `__`; skip abstract methods (they are declared,
  not shadowing).
- Wired into the `quality` job of `.github/workflows/ci.yml` immediately after
  the `check_dep_pins.py` step.

### R2 — Duplicate route-path gate

- Permanent test in `packages/lexigram-web/tests/unit/routing/` that boots a
  `WebProvider` via `TestEnvironment`, collects
  `[getattr(r, "path", None) for r in web.starlette.routes]`, and asserts no
  path appears more than once.
- Failure message lists each duplicated path with its count.

### R3 — Provider contract smoke harness

- New helper `lexigram.testing.lib.smoke.assert_contracts_resolve(container,
  contracts: list[type]) -> None` resolving each type with
  `bypass_visibility=True` and raising `AssertionError` with the failing
  contract name otherwise.
- Unit test for the helper itself in `packages/lexigram-testing/tests/unit/`.
- One consumer proof: smoke test booting `AdminProvider` through
  `TestEnvironment` and asserting its exported contracts
  (`AdminContributorRegistryProtocol`, `AdminDashboardProtocol`) resolve.

## Constraints

- Python 3.11+ syntax, `from __future__ import annotations`, absolute imports.
- No `print()` in library code; the dev-tool script prints its report (CLI
  convention, same as `check_tier_boundary.py`).
- Ruff + `ruff format --check` clean on all touched files.
- Commits follow repo convention: `<emoji> <type>(<scope>): <summary>`,
  committed by pathspec.
