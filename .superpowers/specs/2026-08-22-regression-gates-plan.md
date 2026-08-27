# Regression Gates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add three automated gates that permanently detect stub-shadowed MRO
methods, duplicated route paths, and unresolvable provider contracts.

**Architecture:** One dev-tool CLI scanner (`dev/`) wired into the existing
`quality` CI job, plus two pytest-level gates living next to the code they
protect (lexigram-web routing; lexigram-testing smoke helper consumed by
lexigram-admin).

**Tech Stack:** Python 3.11+, ast/inspect, pytest, starlette TestClient via
`lexigram.testing.fixtures.bed.TestEnvironment`, argparse dev-tool convention.

**Spec:** `.superpowers/specs/spec-regression-gates.md`

## Global Constraints

- Run everything with `uv run` from the repo root
  (`/home/admin/Documents/AI/applications/lexigram-dev`).
- Every commit: `git commit <paths> -m "<emoji> <type>(<scope>): <summary>"`
  (pathspec commits only — shared tree).
- Gates: `uv run ruff check <files>` and `uv run ruff format --check <files>`
  must pass before each commit.
- Dev-tool scripts follow `dev/check_tier_boundary.py` conventions:
  module docstring with Usage, `argparse` with `--root PATH`, `sys.exit`
  status, plain `print` allowed in these CLIs.
- Library/test code never uses `print`.

---

### Task 1: Stub-shadow MRO scanner (`dev/check_stub_shadows.py`)

**Files:**
- Create: `dev/check_stub_shadows.py`
- Modify: `.github/workflows/ci.yml` (quality job, after the
  `check_dep_pins.py` step near line 95)

**Interfaces:**
- Consumes: nothing (standalone CLI)
- Produces: exit-code contract — `0` no shadows, `1` findings; stdout lines
  `CLASS.attr -> stub in Owner shadows real in RealOwner`. The CI step and
  future callers rely only on the exit code.

- [ ] **Step 1: Write the scanner**

```python
"""Fail when a class attribute resolves to a NotImplementedError stub that
shadows a real implementation later in its MRO.

The auth-controller split (commit 7bfb54c3) introduced typing stubs such as

    def generate_breadcrumbs(self, *crumbs, current=None):
        raise NotImplementedError

inside endpoint mixins. Because the mixins sat earlier in the MRO than
``AdminController`` (which owns the real implementations), every call raised
at runtime. This gate re-detects that shape anywhere in the workspace.

Usage:
    python check_stub_shadows.py [--root PATH]

Exit codes: 0 = clean, 1 = at least one shadow found.
"""

from __future__ import annotations

import argparse
import ast
import importlib
import inspect
import logging
import pkgutil
import sys
from pathlib import Path

ROOT_PACKAGES = ("lexigram",)


def _is_stub(func: object) -> bool:
    """True when the function's body is exactly ``raise NotImplementedError``."""
    try:
        source = inspect.getsource(func)  # type: ignore[arg-type]
        tree = ast.parse(source)
    except (OSError, TypeError, SyntaxError):
        return False
    fn = next(
        (
            node
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ),
        None,
    )
    if fn is None:
        return False
    body = [
        statement
        for statement in fn.body
        if not (isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Constant))
    ]
    return (
        len(body) == 1
        and isinstance(body[0], ast.Raise)
        and "NotImplementedError" in ast.dump(body[0])
    )


def _unwrap(attr: object) -> object:
    """Expose the callable behind properties and staticmethods."""
    return getattr(attr, "fget", getattr(attr, "__func__", attr))


def _import_workspace_packages() -> None:
    logging.disable(logging.CRITICAL)
    for name in ROOT_PACKAGES:
        try:
            package = importlib.import_module(name)
        except ImportError:
            continue
        for module in pkgutil.walk_packages(package.__path__, prefix=name + "."):
            try:
                importlib.import_module(module.name)
            except Exception:  # noqa: BLE001 — unimportable modules are not shadows
                continue


def _workspace_classes() -> set[type]:
    classes: set[type] = set()
    for module in list(sys.modules.values()):
        if getattr(module, "__name__", "").startswith("lexigram"):
            for value in vars(module).values():
                if inspect.isclass(value):
                    classes.add(value)
    return classes


def find_shadows() -> list[str]:
    """Return one report line per stub-shadow finding."""

    _import_workspace_packages()
    findings: list[str] = []
    seen: set[tuple[str, str]] = set()
    for cls in _workspace_classes():
        try:
            mro = cls.__mro__
        except AttributeError:
            continue
        for name in dir(cls):
            if name.startswith("__"):
                continue
            owners = [candidate for candidate in mro if name in vars(candidate)]
            if len(owners) < 2:
                continue
            key = (cls.__qualname__, name)
            if key in seen:
                continue
            seen.add(key)
            first_fn = _unwrap(vars(owners[0])[name])
            if not _is_stub(first_fn):
                continue
            real_owner = next(
                (
                    candidate
                    for candidate in owners[1:]
                    if not _is_stub(_unwrap(vars(candidate)[name]))
                ),
                None,
            )
            if real_owner is not None:
                findings.append(
                    f"{cls.__qualname__}.{name} -> stub in {owners[0].__name__} "
                    f"shadows real in {real_owner.__name__}"
                )
    return sorted(findings)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="repo root (informational)")
    args = parser.parse_args()
    del args  # parity with sibling tools; scanning uses imported packages

    findings = find_shadows()
    for line in findings:
        print(line)
    print(f"{len(findings)} shadow finding(s)")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run it — expect exit 0 (clean after `95e9656`)**

Run: `uv run python dev/check_stub_shadows.py`
Expected: `0 shadow finding(s)`, exit code `0`.

Sanity-check the detector by temporarily adding a stub to any scratch class
and confirming it reports, then revert:

```python
class _Scratch:
    def helper(self) -> None:
        raise NotImplementedError

class _ScratchChild(_Scratch):
    def helper(self) -> None:
        """real"""
```

- [ ] **Step 3: Lint**

Run: `uv run ruff check dev/check_stub_shadows.py && uv run ruff format --check dev/check_stub_shadows.py`
Expected: pass. Fix findings before proceeding.

- [ ] **Step 4: Wire into CI quality job**

In `.github/workflows/ci.yml`, inside the `quality` job immediately after the
step running `check_dep_pins.py --root .` (~line 95), add:

```yaml
      - name: Stub-shadow gate (MRO resolution)
        run: uv run python dev/check_stub_shadows.py --root .
```

- [ ] **Step 5: Commit**

```bash
git commit dev/check_stub_shadows.py .github/workflows/ci.yml \
  -m "🛡️ feat(dev): gate stub-shadowed MRO methods workspace-wide"
```

(If 🛡️ is rejected by tooling, use `🔧 chore(dev): …`.)

---

### Task 2: Duplicate route-path gate (lexigram-web)

**Files:**
- Create: `packages/lexigram-web/tests/unit/routing/test_route_paths.py`

**Interfaces:**
- Consumes: `TestEnvironment` fixture pattern from
  `packages/lexigram-testing/src/lexigram/testing/fixtures/bed.py`;
  `WebProvider` from `lexigram.web.di.provider`.
- Produces: test `test_no_duplicate_route_paths` — fails listing duplicated
  paths if any contributor/core pair ever collides again.

- [ ] **Step 1: Write the failing-probe test**

```python
"""Route registry hygiene: no two registered routes may share a path.

The relay-gateway contributor once registered GET /health before the
canonical web health route (fixed by registering /health pre-contributors);
this test keeps first-match-wins collisions impossible to reintroduce.
"""

from __future__ import annotations

from collections import Counter

import pytest

from lexigram.web.di.provider import WebProvider


@pytest.mark.asyncio
async def test_no_duplicate_route_paths(test_bed) -> None:
    """Every registered Starlette route path must be unique."""

    web = await test_bed.resolve(WebProvider)
    paths = [
        path
        for path in (
            getattr(route, "path", None) for route in web.starlette.routes
        )
        if path
    ]
    duplicates = {path: count for path, count in Counter(paths).items() if count > 1}
    assert not duplicates, f"duplicate route paths registered: {duplicates}"
```

The package-local ``test_bed`` fixture (`packages/lexigram-web/tests/conftest.py:78`)
already registers IdentityProvider, ObservabilityProvider, and WebProvider,
and boots them via ``bed.context()`` — do NOT call ``use_provider``/``setup``
here (that would double-register WebProvider on an already-running bed).
This mirrors sibling usage in ``test_health_routes.py:58``.

- [ ] **Step 2: Run it**

Run: `cd packages/lexigram-web && uv run pytest tests/unit/routing/test_route_paths.py -q --no-cov -p no:cacheprovider`
Expected: PASS (post-`32de8bb` there are zero duplicate paths).

- [ ] **Step 3: Lint**

Run: `uv run ruff check packages/lexigram-web/tests/unit/routing/test_route_paths.py && uv run ruff format --check packages/lexigram-web/tests/unit/routing/test_route_paths.py`

- [ ] **Step 4: Commit**

```bash
git commit packages/lexigram-web/tests/unit/routing/test_route_paths.py \
  -m "✅ test(web): forbid duplicate route paths across contributors"
```

---

### Task 3: Provider contract smoke harness

**Files:**
- Create: `packages/lexigram-testing/src/lexigram/testing/lib/smoke.py`
- Modify: `packages/lexigram-testing/src/lexigram/testing/lib/__init__.py`
  (re-export)
- Test: `packages/lexigram-testing/tests/unit/test_smoke.py`
- Create: `experimental/apps/lexigram-admin/tests/unit/test_provider_smoke.py`

**Interfaces:**
- Consumes: container protocol with
  `async resolve(service_type, bypass_visibility=True)`.
- Produces: `assert_contracts_resolve(container, contracts: list[type]) -> None`
  raising `AssertionError("contract failed to resolve: X")` on first failure.
  Later packages adopt this for their own provider smoke tests.

- [ ] **Step 1: Write the helper**

```python
"""Boot-time composition assertions for provider exports."""

from __future__ import annotations

from typing import Any


async def assert_contracts_resolve(container: Any, contracts: list[type]) -> None:
    """Resolve every contract, failing loudly on the first miss.

    Args:
        container: DI resolver exposing ``resolve(type, bypass_visibility=...)``.
        contracts: Contract types a provider declares in ``exports``.

    Raises:
        AssertionError: naming the first contract that cannot be resolved.
    """
    for contract in contracts:
        try:
            await container.resolve(contract, bypass_visibility=True)
        except Exception as exc:  # noqa: BLE001 — any failure means unresolved
            raise AssertionError(
                f"contract failed to resolve: {contract.__name__}: {exc}"
            ) from exc


__all__ = ["assert_contracts_resolve"]
```

Add to `lib/__init__.py`: `from lexigram.testing.lib.smoke import assert_contracts_resolve` plus its `__all__` entry, mirroring existing export style.

- [ ] **Step 2: Unit-test the helper (failing first)**

```python
"""Tests for lexigram.testing.lib.smoke.assert_contracts_resolve."""

from __future__ import annotations

import pytest

from lexigram.testing.lib.smoke import assert_contracts_resolve


class _Ok:
    """Registered contract."""


class _Missing:
    """Unregistered contract."""


def _container_with(*registered: type) -> object:
    class _C:
        async def resolve(self, service_type: type, bypass_visibility: bool = False) -> object:
            if service_type in registered:
                return object()
            raise LookupError(service_type.__name__)

    return _C()


@pytest.mark.asyncio
async def test_passes_when_all_registered() -> None:
    await assert_contracts_resolve(_container_with(_Ok), [_Ok])


@pytest.mark.asyncio
async def test_names_the_missing_contract() -> None:
    with pytest.raises(AssertionError, match="_Missing"):
        await assert_contracts_resolve(_container_with(), [_Missing])
```

Run: `cd packages/lexigram-testing && uv run pytest tests/unit/test_smoke.py -q --no-cov -p no:cacheprovider`
Expected: PASS (write the test file *before* the helper only if executing
strict TDD; both orders acceptable here since Task steps 1–2 ship together).

- [ ] **Step 3: Admin consumer smoke test**

```python
"""Smoke: AdminProvider's exported contracts resolve after register+boot.

AdminProvider cannot boot in a bare container: freeze-time validation
(LEX_ERR_DI_008) requires DatabaseProviderProtocol and FlagManagerProtocol to
be registered. Both are satisfied with MagicMock stand-ins via
``TestEnvironment.override``, which ``setup()`` applies before the app starts.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from lexigram.admin.config import AdminConfig
from lexigram.admin.di.bundle_provider import AdminProvider
from lexigram.contracts.admin.protocols import (
    AdminContributorRegistryProtocol,
    AdminDashboardProtocol,
)
from lexigram.contracts.data import DatabaseProviderProtocol
from lexigram.contracts.feature_flags.protocols import FlagManagerProtocol
from lexigram.testing.fixtures.bed import TestEnvironment
from lexigram.testing.lib.smoke import assert_contracts_resolve


@pytest.mark.asyncio
async def test_admin_exports_resolve() -> None:
    bed = TestEnvironment()
    bed.override(DatabaseProviderProtocol, MagicMock()).override(
        FlagManagerProtocol, MagicMock()
    )
    bed.use_provider(
        AdminProvider(
            config=AdminConfig.from_dict(
                {"auth": {"security": {"setup_token": "smoke-token"}}}
            )
        )
    )
    await bed.setup()
    try:
        await assert_contracts_resolve(
            bed.container,
            [AdminContributorRegistryProtocol, AdminDashboardProtocol],
        )
    finally:
        await bed.teardown()
```

> **Verified 2026-08-22:** this exact test body passes in this workspace.
> Do NOT register singletons via `bed.container.singleton(...)` before
> `setup()` — `bed.container` is `None` until setup creates it; use
> `bed.override(...)`.

Run: `cd experimental/apps/lexigram-admin && uv run pytest tests/unit/test_provider_smoke.py -q --no-cov -p no:cacheprovider`
Expected: PASS.

- [ ] **Step 4: Lint + full scoped suites**

Run:
```bash
uv run ruff check packages/lexigram-testing/src/lexigram/testing/lib/smoke.py \
  packages/lexigram-testing/src/lexigram/testing/lib/__init__.py \
  packages/lexigram-testing/tests/unit/test_smoke.py \
  experimental/apps/lexigram-admin/tests/unit/test_provider_smoke.py \
&& uv run ruff format --check packages/lexigram-testing/src/lexigram/testing/lib/smoke.py \
  packages/lexigram-testing/tests/unit/test_smoke.py \
  experimental/apps/lexigram-admin/tests/unit/test_provider_smoke.py
```
Then `cd packages/lexigram-testing && uv run pytest tests/unit -q --no-cov -p no:cacheprovider`
and the same for lexigram-admin unit tests. Expected: green.

- [ ] **Step 5: Commit**

```bash
git commit \
  packages/lexigram-testing/src/lexigram/testing/lib/smoke.py \
  packages/lexigram-testing/src/lexigram/testing/lib/__init__.py \
  packages/lexigram-testing/tests/unit/test_smoke.py \
  experimental/apps/lexigram-admin/tests/unit/test_provider_smoke.py \
  -m "✅ test(testing): provider export smoke harness + admin consumer"
```

---

## Self-review notes

- Spec R1→Task 1, R2→Task 2, R3→Task 3 — full coverage.
- Type consistency: `assert_contracts_resolve(container, contracts)` used
  identically in Tasks 3 steps 2–3.
- Known risk: Task 1 imports every workspace package in one process (~40 s,
  same as the aggregate suite); if CI time matters, move it to the `tests`
  job or add `--packages` filtering later — out of scope now.
