# Security Criticals Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the three critical authZ/authN gaps — fail-open CSRF, mass-assignment through default validators, and client-controlled tenant identity with unscoped CRUD.

**Architecture:** (1) the admin CSRF decorator fails closed and delegates token validation to `AdminCsrfService`; (2) controller-default `validate_create/update` route through the existing `Resource.before_validate` coercion/validation plus a model-field allowlist and protected-field denylist applied at the write layer; (3) tenant identity derives from authenticated state validated against the registry, with an injected mandatory `tenant_id` filter in the repository data source gated by `multitenancy.enforce_scoping`.

**Tech Stack:** pytest, starlette TestClient patterns already used by admin tests; no new dependencies.

**Spec:** `.superpowers/specs/spec-security-remediation.md` (findings 1–3)

## Global Constraints

- Repo root: `/home/admin/Documents/AI/applications/lexigram-dev`; run everything via `uv run`.
- Narrow runs: `pytest <files> -q --no-cov -p no:cacheprovider -m "not integration"`.
- Gates before each commit: ruff check + format --check on touched paths; mypy on touched admin src modules.
- Emoji pathspec commits; `git add -f` for brand-new files.
- One commit per task; regression tests ship with the fix.

---

### Task 1: CSRF guard fails closed + timing-safe validation

**Files:**
- Modify: `experimental/apps/lexigram-admin/src/lexigram/admin/auth/guards.py:437-466`
- Test: `experimental/apps/lexigram-admin/tests/unit/auth/test_csrf_decorator.py` (create)

**Interfaces:**
- Consumes: `AdminCsrfServiceProtocol.validate_token(expected: str, submitted: str) -> bool` (exists on session-bound service; locate concrete accessor `request.state.csrf_service` or container fallback as used elsewhere in guards.py).
- Produces: decorator `_require_csrf` behavior contract — missing session/token ⇒ `PermissionDeniedError`; mismatch/expiry ⇒ same; valid ⇒ pass.

- [ ] **Step 1: Write failing tests**

```python
"""CSRF decorator fail-closed contract."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from lexigram.admin.auth.guards import require_csrf
from lexigram.contracts.exceptions.domain import PermissionDeniedError


def _request(csrf_token=None, submitted=None, header=None):
    request = MagicMock()
    request.method = "POST"
    request.state.session = (
        SimpleNamespace(csrf_token=csrf_token) if csrf_token else None
    )
    request.headers = {"X-CSRF-Token": header} if header else {}
    request.scope = {}
    async def _form():
        return {"csrf_token": submitted} if submitted else {}
    request.form = _form
    return request


@pytest.mark.asyncio
async def test_missing_session_token_fails_closed():
    @require_csrf
    async def handler(request):
        return "ok"

    with pytest.raises(PermissionDeniedError, match="CSRF"):
        await handler(_request(csrf_token=None))


@pytest.mark.asyncio
async def test_expired_or_invalid_token_rejected_via_service():
    svc = MagicMock()
    svc.validate_token.return_value = False

    @require_csrf
    async def handler(request):
        return "ok"

    req = _request(csrf_token="expected", submitted="anything")
    req.state.csrf_service = svc
    with pytest.raises(PermissionDeniedError):
        await handler(req)
    svc.validate_token.assert_called_once()


@pytest.mark.asyncio
async def test_valid_token_passes_without_service_compare_digest_fallback():
    @require_csrf
    async def handler(request):
        return "ok"

    assert (
        await handler(_request(csrf_token="tok", submitted="tok")) == "ok"
    )
```

- [ ] **Step 2: Run to verify failure**

Run: `cd experimental/apps/lexigram-admin && uv run pytest tests/unit/auth/test_csrf_decorator.py -q --no-cov -p no:cacheprovider`
Expected: first two FAIL (current code passes through / uses !=), third may pass.

- [ ] **Step 3: Implement**

Replace lines ~436-466 of `guards.py`:

```python
        # Get expected token from session
        session = getattr(request.state, "session", None)
        expected_token = getattr(session, "csrf_token", None) if session else None

        if not expected_token:
            # Fail closed: a session without CSRF state cannot authorize
            # state-changing requests.
            logger.warning("csrf_rejected_no_session_token")
            raise PermissionDeniedError(
                message="Missing CSRF session state",
                code=ErrorCode.AUTH_INVALID_TOKEN,
            )

        # Get submitted token
        submitted_token = request.headers.get("X-CSRF-Token")

        if not submitted_token:
            # Try form data
            try:
                form = request.scope.get("admin_form_data")
                if form is None:
                    form = await request.form()
                submitted_token = form.get("csrf_token")  # type: ignore[assignment]
            except (
                ConnectionError,
                RuntimeError,
                ValueError,
                TypeError,
                AttributeError,
            ):
                submitted_token = None

        if not submitted_token:
            raise PermissionDeniedError(
                message="Invalid or missing CSRF token",
                code=ErrorCode.AUTH_INVALID_TOKEN,
            )

        # Prefer the HMAC+expiry service when bound; fall back to a
        # timing-safe constant-time compare.
        csrf_service = getattr(request.state, "csrf_service", None)
        if csrf_service is not None:
            if not csrf_service.validate_token(expected_token, submitted_token):
                raise PermissionDeniedError(
                    message="Invalid or expired CSRF token",
                    code=ErrorCode.AUTH_INVALID_TOKEN,
                )
        elif not hmac.compare_digest(expected_token, submitted_token):
            raise PermissionDeniedError(
                message="Invalid or missing CSRF token",
                code=ErrorCode.AUTH_INVALID_TOKEN,
            )

        return await func(request, *args, **kwargs)
```

Add `import hmac` to module imports if absent. Locate how other code reaches the bound `AdminCsrfService` (grep `csrf_service` in `admin/di/sub_providers/auth.py`) and, if sessions always carry it, prefer that accessor over `request.state`.

- [ ] **Step 4: Run suite + sweep for callers relying on old behavior**

Run: `uv run pytest tests/unit -q --no-cov -p no:cacheprovider -m "not integration" --tb=line`
Expected: green. If e2e flows fail for lack of session CSRF binding, wire `request.state.csrf_service` where admin auth middleware binds session state — that is part of this fix, not scope creep.

- [ ] **Step 5: Lint, mypy, commit**

```bash
uv run ruff check experimental/apps/lexigram-admin/src/lexigram/admin/auth/guards.py experimental/apps/lexigram-admin/tests/unit/auth/test_csrf_decorator.py \
&& uv run ruff format --check experimental/apps/lexigram-admin/src/lexigram/admin/auth/guards.py experimental/apps/lexigram-admin/tests/unit/auth/test_csrf_decorator.py \
&& uv run mypy src/lexigram/admin/auth/guards.py
git add -f experimental/apps/lexigram-admin/tests/unit/auth/test_csrf_decorator.py
git commit experimental/apps/lexigram-admin/src/lexigram/admin/auth/guards.py experimental/apps/lexigram-admin/tests/unit/auth/test_csrf_decorator.py \
  -m "🔒 security(admin): CSRF guard fails closed with timing-safe validation"
```

---

### Task 2: Default validators coerce + allowlist model fields; protected-field denylist at write layer

**Files:**
- Modify: `experimental/apps/lexigram-admin/src/lexigram/admin/controllers/resource/mutation.py` (`validate_create`/`validate_update` defaults) and the update-path call sites mirroring create
- Modify: `experimental/apps/lexigram-admin/src/lexigram/admin/data/adapters/memory_adapter.py:118-122` (setattr allowlist)
- Modify: `packages/../experimental/apps/lexigram-admin/src/lexigram/admin/services/import_/service.py:224` (mapped dict filtered before validate)
- Test: `experimental/apps/lexigram-admin/tests/unit/resources/test_mass_assignment_guard.py` (create)

**Interfaces:**
- Consumes: `Resource.before_validate(data)` → `Ok(dict) | Err(AdminValidationError-details)`; `Resource.model` annotations for the field allowlist; form-coercion helper.
- Produces: `ResourceController._filter_model_fields(data) -> dict` used by both defaults and import service.

- [ ] **Step 1: Write failing tests**

```python
"""Mass-assignment guard: unknown/protected keys never reach the data source."""

from __future__ import annotations

from dataclasses import dataclass, field
from unittest.mock import AsyncMock

import pytest

from lexigram.admin.controllers.resource import ResourceController


@dataclass
class Model:
    name: str = ""
    is_active: bool = True


class _DS:
    def __init__(self):
        self.created = None
    async def create(self, data):
        self.created = dict(data)
        return {"id": "1", **data}


def _controller(ds) -> ResourceController:
    ctrl = ResourceController.__new__(ResourceController)
    ctrl.model = Model
    ctrl._data_source = ds
    ctrl.resource_name = "pets"
    ctrl.meta = type("M", (), {"name": "pets", "prefix": "/admin"})
    return ctrl


@pytest.mark.asyncio
async def test_unknown_and_protected_keys_stripped_on_create():
    ds = _DS()
    ctrl = _controller(ds)
    data = {
        "name": "Rex",
        "role": "superadmin",
        "tenant_id": "other",
        "id": "999",
        "is_active": "on",
    }
    validated = ctrl.validate_create(data)
    created = await ds.create(validated)
    assert set(ds.created) <= {"name", "is_active"}


@pytest.mark.asyncio
async def test_coercion_applies_bool_from_form_string():
    ds = _DS()
    ctrl = _controller(ds)
    validated = ctrl.validate_create({"name": "Rex", "is_active": "on"})
    assert validated["is_active"] is True
```

- [ ] **Step 2: Verify failure**

Run scoped command from Task 1 Step 2 pattern against this file.
Expected: FAIL — current default returns raw dict including `role`/`tenant_id`/`id`, and `is_active` stays `"on"`.

- [ ] **Step 3: Implement**

In `mutation.py` replace both defaults:

```python
    def validate_create(self: ResourceController, data: dict[str, Any]) -> dict[str, Any]:
        """Coerce, validate against the resource model, and strip unknown keys."""
        return self._validated_model_fields(data)

    def validate_update(self: ResourceController, data: dict[str, Any]) -> dict[str, Any]:
        """Same contract as create for updates."""
        return self._validated_model_fields(data)
```

Add one shared helper (place near other controller helpers; reuse `before_validate` from the bound resource instance `self.resource` if present — otherwise inline the same calls):

```python
    def _allowed_model_fields(self) -> set[str]:
        model = getattr(self, "model", None)
        if model is None:
            return set()
        fields = getattr(model, "model_fields", None) or getattr(
            model, "__annotations__", {}
        )
        return {k for k in fields if not k.startswith("_")}

    _PROTECTED_FIELDS = {"id", "tenant_id", "created_at", "updated_at"}

    def _validated_model_fields(self, data: dict[str, Any]) -> dict[str, Any]:
        from lexigram.admin.exceptions import AdminValidationError

        allowed = self._allowed_model_fields()
        cleaned = {k: v for k, v in data.items() if k in allowed}
        cleaned = {
            k: v for k, v in cleaned.items() if k not in self._PROTECTED_FIELDS
        }
        result = self.before_validate(cleaned)
        if hasattr(result, "is_err") and result.is_err():
            raise result.unwrap_err()
        out = result.unwrap() if hasattr(result, "unwrap") else result
        if isinstance(out, dict) and allowed:
            out = {k: v for k, v in out.items() if k in allowed}
            out = {k: v for k, v in out.items() if k not in self._PROTECTED_FIELDS}
        return out
```

Mirror the filter in `services/import_/service.py` at the mapped-dict step (call the resource's `validate_create` instead of `dict(item)` when a resource/model is bound). In `memory_adapter.py`, restrict `setattr` targets to the bound model's declared fields.

- [ ] **Step 4: Suite + sweep**

Run full admin unit suite; expect existing resource/import suites green (some may need their fixtures to include previously-pass-through keys — fix fixtures only when the key is legitimately part of the form).

- [ ] **Step 5: Commit**

```bash
git add -f experimental/apps/lexigram-admin/tests/unit/resources/test_mass_assignment_guard.py
git commit <touched-paths> -m "🔒 security(admin): block mass-assignment via model-field allowlist"
```

---

### Task 3: Tenant scoping enforced server-side

**Files:**
- Modify: `experimental/apps/lexigram-admin/src/lexigram/admin/multitenancy/adapter.py:181-194`
- Modify: `experimental/apps/lexigram-admin/src/lexigram/admin/data/adapters/repository/data_source.py`
- Modify: `experimental/apps/lexigram-admin/src/lexigram/admin/config.py` (add `enforce_scoping: bool = True` under multitenancy section)
- Test: `experimental/apps/lexigram-admin/tests/unit/multitenancy/test_tenant_scoping.py` (create)

**Interfaces:**
- Consumes: existing tenant registry lookup used by adapter; repository filters mechanism (`to_repository_filters()` on QuerySpec / filter kwargs).
- Produces: `resolve_tenant_id(request|state) -> str | None` validating against registry; `RepositoryDataSource.tenant_scope: str | None` attribute — when set (and scoping enabled), every read/write method adds `{"tenant_id": value}` equality.

- [ ] **Step 1: Failing tests**

```python
"""Server-side tenant scoping contract."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_header_tenant_rejected_unless_in_registry(monkeypatch):
    from lexigram.admin.multitenancy.adapter import resolve_tenant_id

    class Registry:
        def exists(self, tenant_id): return tenant_id == "acme"

    monkeypatch.setattr(
        "lexigram.admin.multitenancy.adapter._registry_lookup",
        lambda: Registry(),
    )
    assert resolve_tenant_id("acme", header_value="acme") == "acme"
    assert resolve_tenant_id("acme", header_value="evil") == "acme"


@pytest.mark.asyncio
async def test_data_source_scopes_all_operations():
    from lexigram.admin.data.adapters.repository.data_source import (
        RepositoryDataSource,
    )

    seen = {}

    class FakeRepo:
        async def find_many(self, spec):
            seen["filters"] = getattr(spec, "_extra_filters", None)
            class R: items=[]; total=0
            return R()

    ds = RepositoryDataSource(repo=FakeRepo())
    ds.tenant_scope = "acme"
    await ds.find_many(object())
    assert seen["filters"] == {"tenant_id": "acme"}
```

Adapt constructor/filters plumbing to real signatures while keeping the asserted contract.

- [ ] **Step 2: Red-run**, then implement:

- Adapter: replace verbatim header trust with `resolve_tenant_id(identity_claim_tenant, header_value)`; header wins only when it matches the authenticated claim/registry entry.
- Data source: add `tenant_scope: str | None = None`; in `find_one/find_many/create/update/delete/count`, merge `tenant_id` into filters when set and scoping enabled (config flag read at construction).
- Middleware keeps setting `request.state.tenant_id` but the data source consumes only the *validated* value propagated via container-scoped context.

- [ ] **Step 3: Full admin suite green** (single-tenant deployments unaffected because flag/scoping inactive without multitenancy).

- [ ] **Step 4: Commit**

```bash
git add -f experimental/apps/lexigram-admin/tests/unit/multitenancy/test_tenant_scoping.py
git commit <paths> -m "🔒 security(admin): enforce server-side tenant scoping on resource data"
```

---

## Self-review notes

- Spec findings 1→T1, 2→T2, 3→T3; decisions table honored (fail-closed; scoping flag).
- Biggest implementation risk: T1 wiring of `csrf_service` onto `request.state` — investigate during Step 3 via existing middleware binding; if sessions never carry the service, use container fallback resolved in middleware at login time.
