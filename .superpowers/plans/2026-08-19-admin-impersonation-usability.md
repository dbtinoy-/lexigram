# Admin Impersonation Usability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire up `ImpersonationService` (currently fully built but deliberately unwired) into a usable, safe feature: close the three latent security gaps (nested sessions, target-role restriction, multi-worker session visibility), register an HTTP route, add an "Impersonate" row action on the Users resource, and show an always-visible banner while impersonating with a one-click "Stop impersonating" control.

**Architecture:** This plan implements two layers in sequence. First, D1-D4 — the inherited backend design from `docs/superpowers/specs/2026-08-16-security-impersonation-design.md` §3.1 Option A — hardens `ImpersonationService` itself (nested-session guard, target-role denial, `request`-session fallback for cross-worker visibility) and adds the missing `ImpersonationController` HTTP route. Second, D5-D8 — from `docs/superpowers/specs/2026-08-19-admin-impersonation-usability-design.md` — build the usability surface on top: a `RowAction` button on the Users table (replacing the orphaned `UserImpersonationView`), a pre-render context-resolution step mirroring the existing `_apply_theme_overrides` pattern, a banner component in `AdminShell`, and DI registration for `ImpersonationService`/`ImpersonationController`.

**Tech Stack:** Python 3.11+, Starlette (`Request`/`Response`/`RedirectResponse`), `lexigram.di` (`@inject`, `container.singleton`), `lexigram.result` (`Result`/`Ok`/`Err`), pytest + pytest-asyncio, httpx `AsyncClient` for integration tests.

---

## File Structure

| File | Responsibility |
|---|---|
| `src/lexigram/admin/services/impersonation.py` | **Modify.** D1 nested-guard, D2 target-role policy check, D3 `request`-fallback for `get_active_session`/`is_impersonating`, D5 docstring update. |
| `src/lexigram/admin/controllers/impersonation.py` | **Create.** New `ImpersonationController` — `POST /admin/impersonate/{user_id}` (D4/D5) and `POST /admin/impersonate/stop` (D4/D7). |
| `src/lexigram/admin/actions/standard.py` | **Modify.** New `ImpersonateAction(RowAction)` (D5). |
| `src/lexigram/admin/actions/__init__.py` | **Modify.** Add `ImpersonateAction` to the `_EXPORTS` lazy-loading whitelist and the `TYPE_CHECKING` import block, so it becomes importable from `lexigram.admin.actions` (D5). |
| `src/lexigram/admin/resources/users.py` | **Modify.** Add `ImpersonateAction()` to `UserResource.actions` (D5). |
| `src/lexigram/admin/views/_views.py` | **Modify.** Delete `UserImpersonationView` and its `__all__` entry (D5). |
| `src/lexigram/admin/controllers/base.py` | **Modify.** New `_apply_impersonation_context` helper, called from `render_admin` (D6). |
| `src/lexigram/admin/engine/renderer.py` | **Modify.** Thread `impersonation_active`/`impersonation_target_id`/`csrf_token` from `extra_context` into `AdminShell` (D7). |
| `src/lexigram/admin/ui/templates/shell.py` | **Modify.** `AdminShell.__init__` gains banner params; `render()` renders the banner above `main-content` (D7). |
| `src/lexigram/admin/di/bundle_provider.py` | **Modify.** Register `ImpersonationService`/`ImpersonationController` singletons; best-effort wiring in `mount_to_app()` (D8). |
| `tests/unit/test_impersonation.py` | **Modify.** New tests for D1/D2/D3. |
| `tests/unit/controllers/test_impersonation_controller.py` | **Create.** Unit tests for `ImpersonationController` (D4/D5). |
| `tests/integration/test_impersonation_controller_routes.py` | **Create.** End-to-end HTTP tests for both routes (D4/D8). |
| `tests/unit/actions/test_impersonate_action.py` | **Create.** Unit tests for `ImpersonateAction` (D5). |
| `tests/unit/controllers/test_base_impersonation_context.py` | **Create.** Unit tests for `_apply_impersonation_context` (D6). |
| `tests/unit/ui/test_shell_impersonation_banner.py` | **Create.** Unit tests for the banner rendering (D7). |

**Note on execution order relative to the Tenancy plan:** `docs/superpowers/plans/2026-08-19-admin-tenancy-visibility.md` also modifies `controllers/base.py` (adds `_apply_tenant_context`, called from `render_admin` right after `_apply_theme_overrides`) and `ui/templates/shell.py` (`main_area` construction). If the Tenancy plan lands first, Task 8 below inserts `_apply_impersonation_context`'s call **after `_apply_tenant_context`** instead of after `_apply_theme_overrides`, and Task 9 below inserts the banner **after** the Tenancy plan's `TenantSwitcher`-related additions to `main_area` rather than directly after `topbar_html`. Each task calls this out again at its insertion point — check the current state of the file before editing rather than assuming line numbers.

---

## Task 1: Nested-session guard (D1)

**Files:**
- Modify: `src/lexigram/admin/services/impersonation.py:145-212` (`start()`)
- Test: `tests/unit/test_impersonation.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/unit/test_impersonation.py`, inside `TestImpersonationServiceStart`:

```python
    @pytest.mark.asyncio
    async def test_nested_impersonation_is_denied(self) -> None:
        service = ImpersonationService()
        actor = _make_actor("admin1", ["superadmin"])
        first = await service.start(actor, "user-123")
        assert first.is_ok()

        second = await service.start(actor, "user-456")

        assert second.is_err()
        assert isinstance(second.unwrap_err(), PermissionDeniedError)
        # The original session must be untouched.
        session = service.get_active_session("admin1")
        assert session is not None
        assert session.target_user_id == "user-123"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_impersonation.py -v -k test_nested_impersonation_is_denied`
Expected: FAIL — `second.is_err()` is `False` (current code silently overwrites the session)

- [ ] **Step 3: Implement the guard**

In `src/lexigram/admin/services/impersonation.py`, in `start()`, insert this check immediately after the existing `can_impersonate` block and before `session = ImpersonationSession(...)` (currently line 179):

```python
        if actor_id in self._sessions:
            logger.warning(
                "impersonation.nested_attempt",
                actor_id=actor_id,
                target_user_id=target_user_id,
            )
            return Err(
                PermissionDeniedError(
                    f"User {actor_id!r} already has an active impersonation session; "
                    "stop it before starting another."
                )
            )

        session = ImpersonationSession(
```

(This replaces just the `session = ImpersonationSession(` line with the guard block followed by that same line — the rest of `start()` is unchanged.)

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_impersonation.py -v -k TestImpersonationServiceStart`
Expected: PASS (6 tests — 5 existing + 1 new)

- [ ] **Step 5: Commit**

```bash
git add src/lexigram/admin/services/impersonation.py tests/unit/test_impersonation.py
git commit -m "feat(admin): deny nested impersonation sessions (D1)"
```

---

## Task 2: Target-role restriction (D2)

**Files:**
- Modify: `src/lexigram/admin/services/impersonation.py` (`ImpersonationPolicy` class, `start()` signature)
- Test: `tests/unit/test_impersonation.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/unit/test_impersonation.py`, inside `TestImpersonationPolicy`:

```python
    def test_cannot_impersonate_target_holding_super_admin_role(self) -> None:
        policy = ImpersonationPolicy()
        assert not policy.can_impersonate_target(["superadmin", "editor"])

    def test_can_impersonate_target_without_super_admin_role(self) -> None:
        policy = ImpersonationPolicy()
        assert policy.can_impersonate_target(["editor", "viewer"])

    def test_can_impersonate_target_with_no_roles(self) -> None:
        policy = ImpersonationPolicy()
        assert policy.can_impersonate_target([])
```

Add to `TestImpersonationServiceStart`:

```python
    @pytest.mark.asyncio
    async def test_start_denies_target_with_super_admin_role(self) -> None:
        service = ImpersonationService()
        actor = _make_actor("admin1", ["superadmin"])
        result = await service.start(
            actor, "user-123", target_roles=["superadmin"]
        )
        assert result.is_err()
        assert isinstance(result.unwrap_err(), PermissionDeniedError)
        assert not service.is_impersonating("admin1")

    @pytest.mark.asyncio
    async def test_start_allows_target_without_super_admin_role(self) -> None:
        service = ImpersonationService()
        actor = _make_actor("admin1", ["superadmin"])
        result = await service.start(actor, "user-123", target_roles=["editor"])
        assert result.is_ok()

    @pytest.mark.asyncio
    async def test_start_allows_when_target_roles_not_provided(self) -> None:
        service = ImpersonationService()
        actor = _make_actor("admin1", ["superadmin"])
        result = await service.start(actor, "user-123")
        assert result.is_ok()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_impersonation.py -v -k "can_impersonate_target or target_with_super_admin_role or target_without_super_admin_role"`
Expected: FAIL — `can_impersonate_target` doesn't exist on `ImpersonationPolicy` (`AttributeError`); `start()` doesn't accept `target_roles` (`TypeError: unexpected keyword argument`)

- [ ] **Step 3: Implement `can_impersonate_target`**

In `src/lexigram/admin/services/impersonation.py`, add this method to `ImpersonationPolicy`, directly after `can_impersonate`:

```python
    def can_impersonate_target(self, target_roles: list[str]) -> bool:
        """Return True unless *target_roles* includes the super-admin role.

        Args:
            target_roles: Role names held by the user being impersonated.

        Returns:
            False if the target holds the configured super-admin role
            (impersonating another super-admin is never allowed); True
            otherwise, including when *target_roles* is empty.
        """
        return self._super_admin_role not in target_roles
```

- [ ] **Step 4: Add `target_roles` param to `start()` and call the check**

In `start()`'s signature, add the new parameter (after `request`):

```python
    async def start(
        self,
        actor: Any,
        target_user_id: str,
        reason: str = "",
        request: Any | None = None,
        target_roles: list[str] | None = None,
    ) -> Result[ImpersonationSession, PermissionDeniedError]:
```

Update the docstring's `Args:` block to add:

```
            target_roles: Optional list of role names held by the target
                user. When provided and it includes the configured
                super-admin role, the attempt is denied.
```

Insert this check immediately after the nested-session guard added in Task 1 (still before `session = ImpersonationSession(...)`):

```python
        if target_roles and not self._policy.can_impersonate_target(target_roles):
            logger.warning(
                "impersonation.target_denied",
                actor_id=actor_id,
                target_user_id=target_user_id,
            )
            return Err(
                PermissionDeniedError(
                    f"Target user {target_user_id!r} holds the super-admin role "
                    "and cannot be impersonated."
                )
            )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_impersonation.py -v`
Expected: PASS (all tests, including the 6 new ones from this task)

- [ ] **Step 6: Commit**

```bash
git add src/lexigram/admin/services/impersonation.py tests/unit/test_impersonation.py
git commit -m "feat(admin): deny impersonating super-admin targets (D2)"
```

---

## Task 3: Multi-worker session fallback (D3)

**Files:**
- Modify: `src/lexigram/admin/services/impersonation.py:271-291` (`get_active_session`, `is_impersonating`)
- Test: `tests/unit/test_impersonation.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/unit/test_impersonation.py`, inside `TestImpersonationServiceQuery`:

```python
    @pytest.mark.asyncio
    async def test_get_active_session_falls_back_to_request_session(self) -> None:
        # Simulate a different worker process: a fresh service with no
        # in-memory session, but a request carrying the session cookie
        # written by the worker that handled `start()`.
        writer_service = ImpersonationService()
        actor = _make_actor("admin1", ["superadmin"])
        mock_request = MagicMock()
        mock_request.session = {}
        await writer_service.start(actor, "user-123", request=mock_request)

        reader_service = ImpersonationService()
        session = reader_service.get_active_session("admin1", request=mock_request)

        assert session is not None
        assert session.target_user_id == "user-123"

    @pytest.mark.asyncio
    async def test_get_active_session_ignores_mismatched_actor_in_request(
        self,
    ) -> None:
        writer_service = ImpersonationService()
        actor = _make_actor("admin1", ["superadmin"])
        mock_request = MagicMock()
        mock_request.session = {}
        await writer_service.start(actor, "user-123", request=mock_request)

        reader_service = ImpersonationService()
        session = reader_service.get_active_session("someone-else", request=mock_request)

        assert session is None

    @pytest.mark.asyncio
    async def test_is_impersonating_falls_back_to_request_session(self) -> None:
        writer_service = ImpersonationService()
        actor = _make_actor("admin1", ["superadmin"])
        mock_request = MagicMock()
        mock_request.session = {}
        await writer_service.start(actor, "user-123", request=mock_request)

        reader_service = ImpersonationService()
        assert reader_service.is_impersonating("admin1", request=mock_request)
        assert not reader_service.is_impersonating("admin1")

    def test_get_active_session_without_request_still_works(self) -> None:
        service = ImpersonationService()
        assert service.get_active_session("nobody") is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_impersonation.py -v -k "falls_back or mismatched_actor or without_request_still_works"`
Expected: FAIL — `get_active_session()`/`is_impersonating()` don't accept a `request` keyword argument (`TypeError: unexpected keyword argument 'request'`)

- [ ] **Step 3: Implement the fallback**

In `src/lexigram/admin/services/impersonation.py`, replace `get_active_session` and `is_impersonating` (current lines 271-291) with:

```python
    def get_active_session(
        self, actor_id: str, request: Any | None = None
    ) -> ImpersonationSession | None:
        """Return the active ``ImpersonationSession`` for *actor_id*, or ``None``.

        Args:
            actor_id: Admin user ID to look up.
            request: Optional Starlette request — when the in-process
                session store has no entry (e.g. a different worker
                handled the original ``start()`` call), the session is
                reconstructed from ``request.session`` if present.

        Returns:
            Active session, or ``None`` if the user is not impersonating.
        """
        session = self._sessions.get(actor_id)
        if session is not None:
            return session
        if request is not None:
            req_session = getattr(request, "session", None)
            raw = req_session.get(_SESSION_KEY) if req_session else None
            if isinstance(raw, dict) and raw.get("actor_id") == actor_id:
                return ImpersonationSession(
                    id=raw.get("id", ""),
                    actor_id=actor_id,
                    target_user_id=raw.get("target_user_id", ""),
                    reason=raw.get("reason", ""),
                )
        return None

    def is_impersonating(self, actor_id: str, request: Any | None = None) -> bool:
        """Return ``True`` if *actor_id* currently has an active impersonation.

        Args:
            actor_id: Admin user ID to check.
            request: Optional Starlette request, passed through to
                ``get_active_session`` for cross-worker fallback.

        Returns:
            True if an active session exists for this actor.
        """
        return self.get_active_session(actor_id, request) is not None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_impersonation.py -v`
Expected: PASS (all tests, including the 4 new ones)

- [ ] **Step 5: Commit**

```bash
git add src/lexigram/admin/services/impersonation.py tests/unit/test_impersonation.py
git commit -m "feat(admin): fall back to request.session for cross-worker impersonation lookups (D3)"
```

---

## Task 4: `ImpersonationController` — routes (D4)

**Files:**
- Create: `src/lexigram/admin/controllers/impersonation.py`
- Test: `tests/unit/controllers/test_impersonation_controller.py`

**Design notes before writing code:**
- CSRF is validated globally by `AdminCsrfMiddleware`, already applied to every admin POST route — this controller does not duplicate that check (same reasoning as `TenancyController` in the Tenancy plan).
- The `POST /admin/impersonate/{user_id}` handler is invoked via `hx-post` with `hx-swap="none"` (set by `ImpersonateAction` in Task 7), so a normal redirect response would be silently discarded by htmx. On success it must set the `HX-Redirect` response header instead — confirmed precedent at `middleware/auth_guard.py:119` and `controllers/resource.py:370,447,646` (`response.headers["HX-Redirect"] = url`). On failure (403/409) it returns a plain error response with an `HX-Trigger` header carrying a `show-toast` event — confirmed precedent at `controllers/resource.py:680-710` and `middleware/error.py:191` (`response.headers["HX-Trigger"] = '{"show-toast":{"message":"...","type":"error"}}'`).
- The `POST /admin/impersonate/stop` handler is submitted by a plain (non-htmx) `<form>` (built in Task 9's banner), so it uses an ordinary `RedirectResponse` (302) — no `HX-Redirect` needed. This matches the plain-redirect idiom already used elsewhere (e.g. `controllers/auth.py`, `controllers/settings.py`).
- Per the spec's error table (§5), a stop request with no active session must surface as a "redirect-with-flash-message," not a silent no-op. The flash mechanism in `state/context.py` is session-backed (`AdminContextManager.__aenter__`/`__aexit__` read/write `session["_flash"]`), so a flash added just before a 302 genuinely survives to the next page load — this is the exact same pattern already used at `controllers/auth.py:325-328` (`async with AdminContextManager(request) as ctx: ctx.add_flash(...)` immediately before `RedirectResponse(...)`). The module-level `flash()` helper only works when a context is active (`AdminContextManager.get_context()` is non-`None`), so it can't be called bare here — it must go through `async with AdminContextManager(request) as ctx: ctx.add_flash(...)` like `auth.py` does, not the bare `flash()` call.
- `target_roles` for D2's check is resolved via `AdminUserStoreProtocol.get_user_by_id(user_id)` (confirmed method exists at `auth/store/protocols.py:116`), reading `.roles` off the returned entity. If the target user can't be found, `target_roles` is left `None` (D2's check only fires when target roles are known — an unknown target is caught downstream by `start()` itself failing to make sense of a nonexistent user id, which is out of scope here per the spec's error table).
- `AdminRouter._build_routes()` (`core/routing.py:182-184`) mounts a controller's routes only by calling `controller.get_routes()` directly — there is no base class requirement, it just needs `hasattr(controller, "get_routes")`. This controller defines `get_routes()` explicitly (mirroring `WidgetController.get_routes()` at `controllers/widgets.py:126`) rather than relying on `@get`/`@post` decorators plus `AdminController`'s reflection-based `get_routes()`, because that reflection walks `inspect.getmembers()`, which returns members **sorted alphabetically by name** — `start_impersonation` would sort before `stop_impersonation`, registering `/impersonate/{user_id}` before the literal `/impersonate/stop`. Starlette matches routes in list order and returns on the first match, so a request to `POST /impersonate/stop` would be swallowed by the parameterised route first (matching `user_id="stop"`) and never reach the real stop handler. `core/routing.py:258-259` documents this exact class of bug for resource routes (`# Fixed-path routes must come before {prefix}/{id} ...`); the same rule applies here. The explicit `get_routes()` below hardcodes `/impersonate/stop` first, sidestepping alphabetical ordering entirely.
- Because routes are now hand-built rather than decorator-driven, `start_impersonation`/`stop_impersonation` are plain `async def` methods (no `@post` decorator, no `lexigram.contracts.web` import, no `prefix` class attribute — the paths are written directly in `get_routes()`).
- Both handlers guard `if actor is None` / `if user is None` before proceeding. This is a real, reachable state, not dead code: `AdminAuthGuardMiddleware` (`middleware/auth_guard.py:61-125`) only checks that `session["admin_user_id"]` is truthy before letting a request through to the controller — it never re-validates against the database. `AdminAuthMiddleware._load_user()` (`middleware/auth.py:134-215`), which actually populates `request.state.user`, performs the real validation (session TTL expiry, revocation, deactivated/deleted user) and returns `GUEST_USER` (i.e. `None`, defined at `auth/models.py:16`) in those cases — even for a request that already passed the guard. So a session that expires, is revoked, or belongs to a since-deactivated admin between the guard check and the controller running a query is a real production race, not a hypothetical one, and `request.state.user` is `None` on those requests. The guard is required.

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/controllers/test_impersonation_controller.py`:

```python
"""Unit tests for ImpersonationController."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.admin.controllers.impersonation import ImpersonationController
from lexigram.admin.exceptions import NotFoundError, PermissionDeniedError
from lexigram.admin.services.impersonation import ImpersonationSession
from lexigram.result import Err, Ok


def _make_request(
    *, user: SimpleNamespace | None, path_params: dict | None = None
) -> MagicMock:
    request = MagicMock()
    request.state = SimpleNamespace(user=user)
    request.path_params = path_params or {}
    request.session = {}
    request.headers = {}
    request.client = SimpleNamespace(host="127.0.0.1")
    return request


class TestStartImpersonation:
    @pytest.mark.asyncio
    async def test_success_sets_hx_redirect(self) -> None:
        service = MagicMock()
        service.start = AsyncMock(
            return_value=Ok(
                ImpersonationSession(actor_id="admin1", target_user_id="user-123")
            )
        )
        user_store = MagicMock()
        user_store.get_user_by_id = AsyncMock(
            return_value=SimpleNamespace(id="user-123", roles=["editor"])
        )
        controller = ImpersonationController(service=service, user_store=user_store)
        request = _make_request(
            user=SimpleNamespace(id="admin1", roles=["superadmin"]),
            path_params={"user_id": "user-123"},
        )

        response = await controller.start_impersonation(request)

        assert response.headers["HX-Redirect"] == "/admin/users"
        service.start.assert_awaited_once()
        _, kwargs = service.start.await_args
        assert kwargs["target_roles"] == ["editor"]

    @pytest.mark.asyncio
    async def test_denied_returns_error_with_toast_trigger(self) -> None:
        service = MagicMock()
        service.start = AsyncMock(
            return_value=Err(PermissionDeniedError("not authorised"))
        )
        user_store = MagicMock()
        user_store.get_user_by_id = AsyncMock(return_value=None)
        controller = ImpersonationController(service=service, user_store=user_store)
        request = _make_request(
            user=SimpleNamespace(id="admin1", roles=["editor"]),
            path_params={"user_id": "user-123"},
        )

        response = await controller.start_impersonation(request)

        assert response.status_code == 403
        assert "show-toast" in response.headers["HX-Trigger"]

    @pytest.mark.asyncio
    async def test_no_authenticated_user_returns_403(self) -> None:
        service = MagicMock()
        user_store = MagicMock()
        controller = ImpersonationController(service=service, user_store=user_store)
        request = _make_request(user=None, path_params={"user_id": "user-123"})

        response = await controller.start_impersonation(request)

        assert response.status_code == 403
        service.start.assert_not_called()

    @pytest.mark.asyncio
    async def test_unknown_target_user_passes_none_target_roles(self) -> None:
        service = MagicMock()
        service.start = AsyncMock(
            return_value=Ok(
                ImpersonationSession(actor_id="admin1", target_user_id="ghost")
            )
        )
        user_store = MagicMock()
        user_store.get_user_by_id = AsyncMock(return_value=None)
        controller = ImpersonationController(service=service, user_store=user_store)
        request = _make_request(
            user=SimpleNamespace(id="admin1", roles=["superadmin"]),
            path_params={"user_id": "ghost"},
        )

        await controller.start_impersonation(request)

        _, kwargs = service.start.await_args
        assert kwargs["target_roles"] is None


class TestStopImpersonation:
    @pytest.mark.asyncio
    async def test_success_redirects(self) -> None:
        service = MagicMock()
        service.stop = AsyncMock(return_value=Ok("admin1"))
        controller = ImpersonationController(service=service, user_store=MagicMock())
        request = _make_request(user=SimpleNamespace(id="admin1", roles=["superadmin"]))

        response = await controller.stop_impersonation(request)

        assert response.status_code == 302
        service.stop.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_no_active_session_still_redirects(self) -> None:
        service = MagicMock()
        service.stop = AsyncMock(return_value=Err(NotFoundError("none")))
        controller = ImpersonationController(service=service, user_store=MagicMock())
        request = _make_request(user=SimpleNamespace(id="admin1", roles=["superadmin"]))

        response = await controller.stop_impersonation(request)

        assert response.status_code == 302

    @pytest.mark.asyncio
    async def test_no_active_session_flashes_warning(self) -> None:
        """Per the spec's error table: no active session, stop posted anyway
        -> redirect-with-flash-message. Flash is session-backed (see
        AdminContextManager._write_flash_to_session), so it must survive the
        redirect for the next page load to display it — asserting directly
        on request.session["_flash"] here is what proves that."""
        service = MagicMock()
        service.stop = AsyncMock(return_value=Err(NotFoundError("none")))
        controller = ImpersonationController(service=service, user_store=MagicMock())
        request = _make_request(user=SimpleNamespace(id="admin1", roles=["superadmin"]))

        await controller.stop_impersonation(request)

        assert request.session["_flash"] == [
            {"message": "No active impersonation session to stop.", "category": "warning"}
        ]


class TestGetRoutes:
    def test_stop_route_precedes_parameterised_start_route(self) -> None:
        controller = ImpersonationController(service=MagicMock(), user_store=MagicMock())

        routes = controller.get_routes()

        assert [r.path for r in routes] == [
            "/impersonate/stop",
            "/impersonate/{user_id}",
        ]

    def test_routes_bind_to_correct_handlers(self) -> None:
        controller = ImpersonationController(service=MagicMock(), user_store=MagicMock())

        routes = controller.get_routes()

        assert routes[0].endpoint == controller.stop_impersonation
        assert routes[1].endpoint == controller.start_impersonation
        assert routes[0].methods == {"POST"}
        assert routes[1].methods == {"POST"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/controllers/test_impersonation_controller.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'lexigram.admin.controllers.impersonation'`

- [ ] **Step 3: Implement `ImpersonationController`**

Create `src/lexigram/admin/controllers/impersonation.py`:

```python
"""Impersonation controller for the admin panel."""

from __future__ import annotations

import json
from typing import Any

from starlette.requests import Request
from starlette.responses import RedirectResponse, Response
from starlette.routing import Route

from lexigram.admin.auth.store import AdminUserStoreProtocol
from lexigram.admin.services.impersonation import ImpersonationService
from lexigram.di.decorators import inject
from lexigram.logging import get_logger

logger = get_logger(__name__)


@inject
class ImpersonationController:
    """Handles starting and stopping superadmin impersonation sessions.

    CSRF is validated by the global ``AdminCsrfMiddleware`` already applied
    to every admin POST route — this controller does not duplicate that
    check.
    """

    def __init__(
        self,
        service: ImpersonationService,
        user_store: AdminUserStoreProtocol,
    ) -> None:
        self._service = service
        self._user_store = user_store

    def get_routes(self) -> list[Any]:
        """Build routes explicitly, with the literal ``/impersonate/stop``
        path ordered before the parameterised ``/impersonate/{user_id}``
        path — Starlette matches routes in list order, and a
        dispatched-first ``{user_id}`` route would otherwise swallow
        ``/impersonate/stop`` (``user_id="stop"``).
        """
        return [
            Route(
                "/impersonate/stop",
                endpoint=self.stop_impersonation,
                methods=["POST"],
                name="admin_impersonation_stop",
            ),
            Route(
                "/impersonate/{user_id}",
                endpoint=self.start_impersonation,
                methods=["POST"],
                name="admin_impersonation_start",
            ),
        ]

    async def start_impersonation(self, request: Request) -> Response:
        """Start impersonating the target user (D4/D5)."""
        actor = getattr(request.state, "user", None)
        if actor is None:
            return self._toast_error("You must be signed in.", status_code=403)

        target_user_id = str(request.path_params.get("user_id", ""))

        target_roles: list[str] | None = None
        try:
            target = await self._user_store.get_user_by_id(target_user_id)
        except Exception:  # noqa: BLE001 — best-effort role lookup
            target = None
        if target is not None:
            target_roles = list(getattr(target, "roles", []) or [])

        result = await self._service.start(
            actor,
            target_user_id,
            request=request,
            target_roles=target_roles,
        )

        if result.is_err():
            error = result.unwrap_err()
            return self._toast_error(str(error), status_code=403)

        response = Response(status_code=200)
        response.headers["HX-Redirect"] = "/admin/users"
        return response

    async def stop_impersonation(self, request: Request) -> Response:
        """Stop the active impersonation session for the current actor (D4/D7)."""
        actor = getattr(request.state, "user", None)
        if actor is not None:
            result = await self._service.stop(actor, request)
            if result.is_err():
                from lexigram.admin.state.context import AdminContextManager

                async with AdminContextManager(request) as ctx:
                    ctx.add_flash("No active impersonation session to stop.", "warning")
        return RedirectResponse(url="/admin/", status_code=302)

    @staticmethod
    def _toast_error(message: str, *, status_code: int) -> Response:
        """Build an error response carrying an HX-Trigger toast event."""
        response = Response(content=message, status_code=status_code)
        response.headers["HX-Trigger"] = json.dumps(
            {"show-toast": {"message": message, "type": "error"}}
        )
        return response
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/controllers/test_impersonation_controller.py -v`
Expected: PASS (9 tests)

- [ ] **Step 5: Commit**

```bash
git add src/lexigram/admin/controllers/impersonation.py tests/unit/controllers/test_impersonation_controller.py
git commit -m "feat(admin): add impersonation start/stop routes (D4)"
```

---

## Task 5: DI registration for `ImpersonationService` and `ImpersonationController` (D8)

**Files:**
- Modify: `src/lexigram/admin/di/bundle_provider.py` (`register()` around lines 104/162; `mount_to_app()` best-effort block after the WidgetController block, currently lines 314-352)
- Test: `tests/integration/test_impersonation_controller_routes.py`

**Design notes:** `ImpersonationService.__init__`'s params (`audit_logger`, `policy`, `active_sessions`, `rbac_config`) all default to `None`/falsy, so `container.singleton(ImpersonationService, ImpersonationService)` constructs safely via `@inject` even for the one param (`audit_logger: AuditLoggerProtocol | None`) that has no direct DI registration — it just resolves to `None`. `AdminRbacConfig` **is** already registered as a pre-built instance (`container.singleton(AdminRbacConfig, self._config.rbac)`, confirmed at `bundle_provider.py` inside `register()`), so `rbac_config` resolves correctly with no extra wiring needed. Only `audit_logger` needs best-effort post-construction wiring, following the same pattern used to wire `WidgetController._audit_service` and (per the Tenancy plan) `TenancyController._audit_service` — setting the resolved service onto the instance attribute after construction (here, `impersonation_service._audit`, `ImpersonationService`'s actual attribute name for its audit logger, confirmed at `services/impersonation.py:132`) — because `AuditLoggerProtocol` itself has zero DI registrations, but `AdminAuditLogServiceProtocol` (which structurally extends it) is registered and can satisfy it via duck typing.

- [ ] **Step 1: Write the failing integration test**

Model this on `tests/integration/test_widget_controller_routes.py`'s pattern (also used by the Tenancy plan's Task 8) — a minimal Starlette app built from the controller's own `get_routes()` output, exercising the real route handlers *and* the real route registration/ordering over HTTP without booting the full `AdminProvider`. Building the app from `get_routes()` (rather than hand-wiring `Route(...)` entries pointing at the controller methods) is deliberate: it's what actually catches a route-ordering regression like `/impersonate/stop` being shadowed by `/impersonate/{user_id}` — a hand-wired app can't reproduce that bug class even if `get_routes()` regresses.

Create `tests/integration/test_impersonation_controller_routes.py`:

```python
"""Integration tests for POST /admin/impersonate/{user_id} and /stop."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from starlette.applications import Starlette

from lexigram.admin.controllers.impersonation import ImpersonationController
from lexigram.admin.services.impersonation import ImpersonationService


async def _create_impersonation_app(*, actor_roles: list[str]) -> Starlette:
    service = ImpersonationService()
    user_store = MagicMock()
    user_store.get_user_by_id = AsyncMock(
        return_value=MagicMock(id="user-123", roles=["editor"])
    )
    controller = ImpersonationController(service=service, user_store=user_store)

    async def _inject_actor(request, call_next):
        request.state.user = MagicMock(id="admin1", roles=actor_roles)
        # Request.session is a read-only property backed by scope["session"]
        # (no setter) — set the scope key directly, not request.session.
        request.scope["session"] = {}
        return await call_next(request)

    app = Starlette(routes=controller.get_routes())
    app.middleware("http")(_inject_actor)
    return app


class TestImpersonationRoutes:
    @pytest.mark.asyncio
    async def test_superadmin_start_returns_hx_redirect(self) -> None:
        app = await _create_impersonation_app(actor_roles=["superadmin"])
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/impersonate/user-123")
        assert response.status_code == 200
        assert response.headers["HX-Redirect"] == "/admin/users"

    @pytest.mark.asyncio
    async def test_non_superadmin_start_returns_403(self) -> None:
        app = await _create_impersonation_app(actor_roles=["editor"])
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/impersonate/user-123")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_stop_redirects(self) -> None:
        app = await _create_impersonation_app(actor_roles=["superadmin"])
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/impersonate/stop", follow_redirects=False)
        assert response.status_code == 302
        assert response.headers["location"] == "/admin/"

    @pytest.mark.asyncio
    async def test_stop_route_not_shadowed_by_parameterised_start_route(self) -> None:
        """Regression guard for the alphabetical route-ordering bug class:
        if get_routes() ever put the parameterised route first, this POST
        would be matched as user_id="stop" and return an HX-Redirect (200)
        instead of the real stop handler's 302."""
        app = await _create_impersonation_app(actor_roles=["superadmin"])
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/impersonate/stop", follow_redirects=False)
        assert response.status_code == 302
        assert "HX-Redirect" not in response.headers
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/integration/test_impersonation_controller_routes.py -v`
Expected: FAIL with `ModuleNotFoundError` if Task 4 hasn't landed yet; if Task 4 is already committed, this passes immediately (it's an end-to-end regression check on top of Task 4's unit tests, not new production code) — proceed either way.

- [ ] **Step 3: Run test to verify it passes**

Run: `uv run pytest tests/integration/test_impersonation_controller_routes.py -v`
Expected: PASS (4 tests)

- [ ] **Step 4: Wire DI registration**

In `src/lexigram/admin/di/bundle_provider.py`, `register()` method — add imports next to `WidgetController`'s (currently line 104):

```python
        from lexigram.admin.controllers.dashboard import DashboardController
        from lexigram.admin.controllers.impersonation import ImpersonationController
        from lexigram.admin.controllers.widgets import WidgetController
```

Add singleton registrations next to `WidgetController`'s (currently line 162):

```python
        # Register built-in controllers
        container.singleton(WidgetController, WidgetController)
        container.singleton(DashboardController, DashboardController)
        from lexigram.admin.services.impersonation import ImpersonationService

        container.singleton(ImpersonationService, ImpersonationService)
        container.singleton(ImpersonationController, ImpersonationController)
```

- [ ] **Step 5: Wire best-effort resolution into `mount_to_app`**

In the same file, `mount_to_app()` — add a new best-effort resolution block immediately after the existing "Resolve built-in WidgetController" block (after line 352, before "Resolve built-in DashboardController"):

```python
        # Resolve built-in ImpersonationController (best-effort)
        try:
            from lexigram.admin.auth.protocols import (
                AdminAuditLogServiceProtocol,
            )
            from lexigram.admin.controllers.impersonation import (
                ImpersonationController,
            )
            from lexigram.admin.services.impersonation import ImpersonationService

            impersonation_service = await admin_resolver.resolve(
                ImpersonationService,
                bypass_visibility=True,
            )
            if getattr(impersonation_service, "_audit", None) is None:
                try:
                    audit_service = await admin_resolver.resolve(
                        AdminAuditLogServiceProtocol,
                        bypass_visibility=True,
                    )
                except Exception:
                    audit_service = None
                if audit_service is not None:
                    impersonation_service._audit = audit_service

            impersonation_controller = await admin_resolver.resolve(
                ImpersonationController,
                bypass_visibility=True,
            )
            controller_instances.append(impersonation_controller)
        except Exception as exc:
            _log.error(
                "admin.impersonation_controller_resolution_failed",
                error=str(exc),
                strict=self._config.strict_resource_resolution,
            )
            self._mount_failures["controller:ImpersonationController"] = str(exc)
            if self._config.strict_resource_resolution:
                raise
```

- [ ] **Step 6: Run the full test suite for this task**

Run: `uv run pytest tests/integration/test_impersonation_controller_routes.py tests/unit/controllers/test_impersonation_controller.py tests/unit/test_impersonation.py -v`
Expected: PASS (all tests, no regressions)

- [ ] **Step 7: Commit**

```bash
git add src/lexigram/admin/di/bundle_provider.py tests/integration/test_impersonation_controller_routes.py
git commit -m "feat(admin): register ImpersonationService/ImpersonationController in DI (D8)"
```

---

## Task 6: `ImpersonateAction` row action; retire `UserImpersonationView` (D5)

**Files:**
- Modify: `src/lexigram/admin/actions/standard.py` (new class, after `PermissionsAction` at line 161)
- Modify: `src/lexigram/admin/actions/__init__.py` (add `ImpersonateAction` to the `_EXPORTS` whitelist and `TYPE_CHECKING` import block)
- Modify: `src/lexigram/admin/resources/users.py:130-134` (`UserResource.actions`)
- Modify: `src/lexigram/admin/views/_views.py:454-578` (delete `UserImpersonationView` + `__all__` entry)
- Modify: `src/lexigram/admin/services/impersonation.py:28-40` (docstring update)
- Test: `tests/unit/actions/test_impersonate_action.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/actions/test_impersonate_action.py`:

```python
"""Unit tests for ImpersonateAction."""

from __future__ import annotations

from types import SimpleNamespace

from lexigram.admin.actions.standard import ImpersonateAction
from lexigram.admin.actions.types import ActionContext


class TestImpersonateActionVisibility:
    def test_hidden_for_own_record(self) -> None:
        action = ImpersonateAction()
        record = {"id": "admin1", "name": "Admin One"}
        user = SimpleNamespace(id="admin1")
        assert action.visible_for(record, user) is False

    def test_visible_for_other_records(self) -> None:
        action = ImpersonateAction()
        record = {"id": "user-123", "name": "Other User"}
        user = SimpleNamespace(id="admin1")
        assert action.visible_for(record, user) is True

    def test_visible_when_user_is_none(self) -> None:
        action = ImpersonateAction()
        record = {"id": "user-123", "name": "Other User"}
        assert action.visible_for(record, None) is True


class TestImpersonateActionUrl:
    def test_get_url_shape(self) -> None:
        action = ImpersonateAction()
        record = {"id": "user-123", "name": "Other User"}
        ctx = ActionContext(resource_name="users", resource_prefix="/admin/users")
        assert action._get_url(record, ctx) == "/admin/impersonate/user-123"

    def test_get_url_none_when_no_record_id(self) -> None:
        action = ImpersonateAction()
        ctx = ActionContext(resource_name="users", resource_prefix="/admin/users")
        assert action._get_url({}, ctx) is None


class TestImpersonateActionHtmxAttrs:
    def test_htmx_attrs_use_post_and_confirm(self) -> None:
        action = ImpersonateAction()
        record = {"id": "user-123", "name": "Other User"}
        ctx = ActionContext(resource_name="users", resource_prefix="/admin/users")
        url = action._get_url(record, ctx)
        attrs = action._get_htmx_attrs(url, record, ctx)
        assert attrs["hx-post"] == "/admin/impersonate/user-123"
        assert attrs["hx-target"] == "body"
        assert attrs["hx-swap"] == "none"
        assert "hx-confirm" in attrs
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/actions/test_impersonate_action.py -v`
Expected: FAIL with `ImportError: cannot import name 'ImpersonateAction'`

- [ ] **Step 3: Implement `ImpersonateAction`**

In `src/lexigram/admin/actions/standard.py`, add this class directly after `PermissionsAction` (after line 161, before `class CreateAction`):

```python
class ImpersonateAction(RowAction):
    """Impersonate a user's session (users resource only).

    Target-role restriction (denying impersonation of another
    super-admin) is enforced server-side only — this action has no
    access to DI/config at render time (``Action`` is a frozen,
    import-time-constructed dataclass), and the row's rendered fields
    don't expose RBAC role membership. See
    ``docs/superpowers/specs/2026-08-19-admin-impersonation-usability-design.md``
    D5 for the full reasoning.
    """

    def __init__(
        self,
        name: str = "impersonate",
        label: str | None = None,
    ) -> None:
        super().__init__(
            name=name,
            label=label or "Impersonate",
            icon="user-check",
            color=ActionColor.GRAY,
        )

    def visible_for(self, record: Any, user: Any | None = None) -> bool:
        if user is None:
            return True
        record_id = self._get_record_id(record)
        actor_id = str(getattr(user, "id", ""))
        return record_id != actor_id

    def _get_url(self, record: Any, ctx: ActionContext) -> str | None:
        record_id = self._get_record_id(record)
        if not record_id:
            return None
        return f"/admin/impersonate/{record_id}"

    def _get_htmx_attrs(
        self, url: str, record: Any, ctx: ActionContext
    ) -> dict[str, str]:
        name = record.get("name", "this user") if isinstance(record, dict) else "this user"
        return {
            "hx-post": url,
            "hx-target": "body",
            "hx-swap": "none",
            "hx-confirm": f"Impersonate {name}?",
        }

    async def execute(self, record: Any, ctx: ActionContext) -> Result[Any, Any]:
        return Ok({"message": f"Impersonating {record}"})
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/actions/test_impersonate_action.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Register `ImpersonateAction` in the `actions` package's lazy-export whitelist**

`resources/users.py` imports action classes from the **package** `lexigram.admin.actions` (`from lexigram.admin.actions import (CreateAction, DeleteAction, EditAction, PermissionsAction)`), not directly from `lexigram.admin.actions.standard`. That package uses PEP 562 lazy loading (`src/lexigram/admin/actions/__init__.py`): a `_EXPORTS` dict maps each importable name to the submodule that defines it, and `__getattr__` resolves names against that whitelist. A name not in `_EXPORTS` raises `ImportError` even though the class exists in `standard.py` — so `ImpersonateAction` must be added to `_EXPORTS` before it can be imported from the package.

In `src/lexigram/admin/actions/__init__.py`, add `ImpersonateAction` to the `TYPE_CHECKING` import block (next to `PermissionsAction`, currently around line 50):

```python
    from lexigram.admin.actions.standard import (
        CloneAction,
        CreateAction,
        DeleteAction,
        DeleteBulkAction,
        EditAction,
        ExportAction,
        ExportBulkAction,
        ImpersonateAction,
        ImportAction,
        ImportBulkAction,
        PermissionsAction,
        PurgeAction,
        PurgeBulkAction,
        RestoreAction,
        RestoreBulkAction,
        ViewAction,
    )
```

And add it to `_EXPORTS` (next to `PermissionsAction`, currently around line 74):

```python
    "PermissionsAction": "lexigram.admin.actions.standard",
    "ImpersonateAction": "lexigram.admin.actions.standard",
```

- [ ] **Step 6: Run the affected test suite to verify the export works**

Run: `uv run pytest tests/unit/actions/test_impersonate_action.py -v`
Expected: PASS (7 tests) — confirms `ImpersonateAction` is still importable directly from `lexigram.admin.actions.standard` (Step 3's tests already cover this) — the new coverage is exercised next in Step 7 via the `resources/users.py` import.

- [ ] **Step 7: Add `ImpersonateAction` to `UserResource.actions`**

In `src/lexigram/admin/resources/users.py`, add `ImpersonateAction` to the existing package-level import (`from lexigram.admin.actions import (...)`), then update lines 130-134:

```python
from lexigram.admin.actions import (
    CreateAction,
    DeleteAction,
    EditAction,
    ImpersonateAction,
    PermissionsAction,
)
```

```python
    actions: list[Any] = [
        EditAction(),
        DeleteAction(),
        PermissionsAction(),
        ImpersonateAction(),
    ]
```

Run: `uv run python -c "from lexigram.admin.resources.users import UserResource"`
Expected: no `ImportError` (confirms the `_EXPORTS` fix from Step 5 actually resolves this import)

- [ ] **Step 8: Delete `UserImpersonationView`**

In `src/lexigram/admin/views/_views.py`, delete the entire `UserImpersonationView` class (lines 454-568, from `@dataclass` / `class UserImpersonationView:` through the closing of its `render()` method, ending just before the `__all__` list). Then remove `"UserImpersonationView"` from the `__all__` list (currently line 577):

```python
__all__ = [
    "AuditLogView",
    "CalendarView",
    "KanbanView",
    "ResourceView",
    "TreeView",
]
```

`el`/`render_to_string` are also used by other classes in this file (e.g. `AuditLogView.render()`), so they will very likely remain in use — but check anyway with `uv run ruff check src/lexigram/admin/views/_views.py` rather than assuming either way, and only remove an import if ruff actually flags it as unused.

- [ ] **Step 9: Update the "Intentionally unwired" docstring note in `services/impersonation.py`**

In `src/lexigram/admin/services/impersonation.py`, replace the `.. note::` block (currently lines 28-40) with:

```python
.. note::
    Wired via ``ImpersonateAction`` (``lexigram.admin.actions.standard``)
    and ``ImpersonationController`` (``lexigram.admin.controllers.
    impersonation``), which register ``POST /admin/impersonate/{user_id}``
    and ``POST /admin/impersonate/stop``. See
    ``docs/superpowers/specs/2026-08-16-security-impersonation-design.md``
    for the security gaps that were closed before wiring (nested
    sessions, target-role restriction, multi-worker session visibility).
```

- [ ] **Step 10: Run the full affected test suite**

Run: `uv run pytest tests/unit/actions/test_impersonate_action.py tests/unit/actions/ tests/unit/test_impersonation.py -v`
Expected: PASS, no regressions (confirms no other test referenced `UserImpersonationView`)

Run: `grep -rn "UserImpersonationView" src/ tests/` to confirm zero remaining references before committing.

- [ ] **Step 11: Commit**

```bash
git add src/lexigram/admin/actions/standard.py src/lexigram/admin/actions/__init__.py src/lexigram/admin/resources/users.py src/lexigram/admin/views/_views.py src/lexigram/admin/services/impersonation.py tests/unit/actions/test_impersonate_action.py
git commit -m "feat(admin): add Impersonate row action, retire orphaned UserImpersonationView (D5)"
```

---

## Task 7: Resolve impersonation context before rendering (D6)

**Files:**
- Modify: `src/lexigram/admin/controllers/base.py` (new `_apply_impersonation_context` method; new call in `render_admin`)
- Test: `tests/unit/controllers/test_base_impersonation_context.py`

**Design notes:** This mirrors `_apply_theme_overrides` (`controllers/base.py:121-166`) exactly: lazily resolve services from the request-scoped container, best-effort try/except, write into `extra_context` via `setdefault`. Unlike `_apply_theme_overrides`, this step's core lookup (`service.get_active_session(...)`) is **synchronous** — `ImpersonationService.get_active_session` is a plain method, not a coroutine — only the container resolution itself is `await`ed.

**Insertion-point caveat:** if the Tenancy plan (`docs/superpowers/plans/2026-08-19-admin-tenancy-visibility.md`) has already landed, `render_admin` will already call `await self._apply_tenant_context(request, extra_context)` after `_apply_theme_overrides`. In that case, add the new call **after** `_apply_tenant_context` instead of directly after `_apply_theme_overrides`. Check the current contents of `render_admin` before editing rather than assuming.

**On the `if user is None: return` guard below:** this is a real, reachable state on every admin page render, not dead code — see the identical reasoning in Task 4's design notes (`AdminAuthGuardMiddleware` only checks session truthiness, not DB validity; `_load_user()` can still return `GUEST_USER`/`None` for an expired, revoked, or deactivated session that already passed the guard).

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/controllers/test_base_impersonation_context.py`:

```python
"""Unit tests for AdminController._apply_impersonation_context."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.admin.controllers.base import AdminController
from lexigram.admin.services.impersonation import ImpersonationSession


def _make_controller_with_container(resolved: dict) -> AdminController:
    controller = AdminController.__new__(AdminController)
    controller._settings_service = None

    async def fake_resolve(cls):
        return resolved.get(cls)

    container = MagicMock()
    container.resolve = fake_resolve
    return controller, container


class TestApplyImpersonationContext:
    @pytest.mark.asyncio
    async def test_populates_context_when_session_active(self) -> None:
        from lexigram.admin.services.impersonation import ImpersonationService

        service = MagicMock()
        service.get_active_session = MagicMock(
            return_value=ImpersonationSession(
                actor_id="admin1", target_user_id="user-123"
            )
        )
        controller, container = _make_controller_with_container(
            {ImpersonationService: service}
        )
        request = MagicMock()
        request.state = SimpleNamespace(user=SimpleNamespace(id="admin1"), container=container)
        extra_context: dict = {}

        await controller._apply_impersonation_context(request, extra_context)

        assert extra_context["impersonation_active"] is True
        assert extra_context["impersonation_target_id"] == "user-123"

    @pytest.mark.asyncio
    async def test_no_op_when_no_active_session(self) -> None:
        from lexigram.admin.services.impersonation import ImpersonationService

        service = MagicMock()
        service.get_active_session = MagicMock(return_value=None)
        controller, container = _make_controller_with_container(
            {ImpersonationService: service}
        )
        request = MagicMock()
        request.state = SimpleNamespace(user=SimpleNamespace(id="admin1"), container=container)
        extra_context: dict = {}

        await controller._apply_impersonation_context(request, extra_context)

        assert "impersonation_active" not in extra_context

    @pytest.mark.asyncio
    async def test_no_op_when_service_not_registered(self) -> None:
        controller, container = _make_controller_with_container({})
        request = MagicMock()
        request.state = SimpleNamespace(user=SimpleNamespace(id="admin1"), container=container)
        extra_context: dict = {}

        await controller._apply_impersonation_context(request, extra_context)

        assert "impersonation_active" not in extra_context

    @pytest.mark.asyncio
    async def test_no_op_when_no_user(self) -> None:
        from lexigram.admin.services.impersonation import ImpersonationService

        service = MagicMock()
        service.get_active_session = MagicMock(
            return_value=ImpersonationSession(
                actor_id="admin1", target_user_id="user-123"
            )
        )
        controller, container = _make_controller_with_container(
            {ImpersonationService: service}
        )
        request = MagicMock()
        request.state = SimpleNamespace(user=None, container=container)
        extra_context: dict = {}

        await controller._apply_impersonation_context(request, extra_context)

        assert "impersonation_active" not in extra_context
        service.get_active_session.assert_not_called()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/controllers/test_base_impersonation_context.py -v`
Expected: FAIL with `AttributeError: 'AdminController' object has no attribute '_apply_impersonation_context'`

- [ ] **Step 3: Implement `_apply_impersonation_context`**

In `src/lexigram/admin/controllers/base.py`, add this method directly after `_apply_theme_overrides` (currently ending at line 166):

```python
    async def _apply_impersonation_context(
        self,
        request: Request,
        extra_context: dict[str, Any],
    ) -> None:
        """Populate impersonation banner state into extra_context, if active.

        Resolves ``ImpersonationService`` from the request-scoped container
        and checks whether the current actor has an active session. Display
        name resolution is out of scope (no user-store dependency here) —
        the banner shows the raw target user ID.
        """
        user = getattr(request.state, "user", None)
        if user is None:
            return

        try:
            from lexigram.admin.services.impersonation import ImpersonationService

            container = getattr(request.state, "container", None) or getattr(
                request.app.state, "container", None
            )
            if container is None:
                return
            service = await container.resolve(ImpersonationService)
            if service is None:
                return

            actor_id = str(getattr(user, "id", ""))
            session = service.get_active_session(actor_id, request)
            if session is not None:
                extra_context.setdefault("impersonation_active", True)
                extra_context.setdefault(
                    "impersonation_target_id", session.target_user_id
                )
        except Exception:  # noqa: BLE001, S110 — non-fatal
            pass
```

- [ ] **Step 4: Wire the call into `render_admin`**

In `render_admin` (currently line 189), add the new call directly after `await self._apply_theme_overrides(request, extra_context)` (or after `_apply_tenant_context` if the Tenancy plan already landed — see the design note above):

```python
        # Inject runtime theme overrides (primary_color, site_name)
        await self._apply_theme_overrides(request, extra_context)
        # Inject impersonation banner state, if an active session exists
        await self._apply_impersonation_context(request, extra_context)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/unit/controllers/test_base_impersonation_context.py -v`
Expected: PASS (4 tests)

- [ ] **Step 6: Run the broader controller test suite for regressions**

Run: `uv run pytest tests/unit/controllers/ -v`
Expected: PASS, no regressions

- [ ] **Step 7: Commit**

```bash
git add src/lexigram/admin/controllers/base.py tests/unit/controllers/test_base_impersonation_context.py
git commit -m "feat(admin): resolve impersonation context before rendering (D6)"
```

---

## Task 8: Impersonation banner in `AdminShell` (D7)

**Files:**
- Modify: `src/lexigram/admin/engine/renderer.py` (thread `impersonation_active`/`impersonation_target_id`/`csrf_token` into `AdminShell(...)`)
- Modify: `src/lexigram/admin/ui/templates/shell.py` (`AdminShell.__init__` new params; `render()` banner insertion)
- Test: `tests/unit/ui/test_shell_impersonation_banner.py`

**Design notes:** The banner renders as a new child of `main_area`, inserted immediately after `topbar_html` and before the breadcrumbs block (`ui/templates/shell.py`, currently lines 387-425) — not inside `TopBar`, since a banner needs different visual prominence than a passive indicator (this is an active safety warning, not routine chrome). It needs a CSRF token for its "Stop impersonating" form's hidden field; `renderer.py`'s `render_page` already resolves `csrf_token = getattr(request.state, "csrf_token", None)` for the outer Jinja2 template — this task threads that same value into `AdminShell` too, rather than introducing a second CSRF-resolution mechanism.

**Insertion-point caveat:** if the Tenancy plan has already landed, `main_area`'s first children may include Tenancy's additions. In that case, insert the banner after `topbar_html` and after any Tenancy-plan additions that sit between `topbar_html` and the breadcrumbs block, so it still renders directly above the main content area. Check the current contents of `render()` before editing.

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/ui/test_shell_impersonation_banner.py`:

```python
"""Unit tests for AdminShell's impersonation banner."""

from __future__ import annotations

from lexigram.admin.ui.templates.shell import AdminShell
from lexigram.ui.core.base import render_to_string


class TestImpersonationBanner:
    def test_banner_absent_by_default(self) -> None:
        shell = AdminShell(content="<p>hi</p>", title="Test")
        html = render_to_string(shell)
        assert "Impersonating" not in html

    def test_banner_renders_when_active(self) -> None:
        shell = AdminShell(
            content="<p>hi</p>",
            title="Test",
            impersonation_active=True,
            impersonation_target_id="user-123",
        )
        html = render_to_string(shell)
        assert "Impersonating" in html
        assert "user-123" in html

    def test_banner_includes_stop_form_with_csrf(self) -> None:
        shell = AdminShell(
            content="<p>hi</p>",
            title="Test",
            impersonation_active=True,
            impersonation_target_id="user-123",
            csrf_token="tok-abc",
        )
        html = render_to_string(shell)
        assert 'action="/admin/impersonate/stop"' in html
        assert "tok-abc" in html

    def test_banner_absent_when_target_id_present_but_not_active(self) -> None:
        shell = AdminShell(
            content="<p>hi</p>",
            title="Test",
            impersonation_active=False,
            impersonation_target_id="user-123",
        )
        html = render_to_string(shell)
        assert "Impersonating" not in html
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/ui/test_shell_impersonation_banner.py -v`
Expected: FAIL — `AdminShell.__init__` raises `TypeError: unexpected keyword argument 'impersonation_active'`

- [ ] **Step 3: Add banner params to `AdminShell.__init__`**

In `src/lexigram/admin/ui/templates/shell.py`, add three new constructor params (after `dark_mode: str = ""`, before `**props: Any`):

```python
        dark_mode: str = "",
        impersonation_active: bool = False,
        impersonation_target_id: str = "",
        csrf_token: str = "",
        **props: Any,
```

And store them (after `self.dark_mode = dark_mode`):

```python
        self.dark_mode = dark_mode
        self.impersonation_active = impersonation_active
        self.impersonation_target_id = impersonation_target_id
        self.csrf_token = csrf_token
```

- [ ] **Step 4: Build the banner and insert it into `main_area`**

In `render()`, directly before the `main_area = el(...)` block (currently starting at line 387), add:

```python
        impersonation_banner = (
            el(
                "div",
                el(
                    "span",
                    f"Impersonating {self.impersonation_target_id}",
                    class_="font-medium",
                ),
                el(
                    "form",
                    el(
                        "input",
                        type_="hidden",
                        name="csrf_token",
                        value=self.csrf_token or "",
                    ),
                    el(
                        "button",
                        "Stop impersonating",
                        type="submit",
                        class_=(
                            "ml-4 px-3 py-1 text-xs font-medium rounded-md "
                            "bg-white/20 hover:bg-white/30 transition-colors"
                        ),
                    ),
                    method="post",
                    action="/admin/impersonate/stop",
                    class_="inline-flex items-center",
                ),
                class_=(
                    "flex items-center justify-between px-4 py-2 text-sm text-white "
                    "bg-amber-600 dark:bg-amber-700"
                ),
            )
            if self.impersonation_active
            else ""
        )
```

Then update `main_area`'s children to insert `impersonation_banner` right after `topbar_html`:

```python
        main_area = el(
            "div",
            topbar_html,
            impersonation_banner,
            # Breadcrumbs
```

(This changes the two-argument opening `topbar_html,` / `# Breadcrumbs` pair into a three-argument `topbar_html,` / `impersonation_banner,` / `# Breadcrumbs` sequence — the rest of `main_area`'s construction is unchanged.)

- [ ] **Step 5: Thread the new values from `render_page` into `AdminShell`**

In `src/lexigram/admin/engine/renderer.py`, in `render_page` (find the `shell = AdminShell(...)` call, currently lines ~166-179), read the two impersonation keys from `extra_context` right before constructing `shell` (near where `dark_mode` is read):

```python
        dark_mode = extra_context.get("dark_mode") or ""
        impersonation_active = bool(extra_context.get("impersonation_active"))
        impersonation_target_id = str(extra_context.get("impersonation_target_id") or "")
```

Then pass them into the `AdminShell(...)` call, alongside the existing `csrf_token` value already resolved just below (move that resolution above the `shell = AdminShell(...)` call if it currently sits after it):

```python
        csrf_token = getattr(request.state, "csrf_token", None) if request else None

        shell = AdminShell(
            content=content,
            title=title,
            user=user,
            nav_items=nav_items,
            user_menu_items=user_menu_items,
            system_menu_items=system_menu_items,
            breadcrumbs=breadcrumbs,
            flash_messages=flash_messages,
            theme_css=theme_css,
            site_name=site_name,
            logo_url=logo_url,
            dark_mode=dark_mode,
            impersonation_active=impersonation_active,
            impersonation_target_id=impersonation_target_id,
            csrf_token=csrf_token or "",
        )
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest tests/unit/ui/test_shell_impersonation_banner.py -v`
Expected: PASS (4 tests)

- [ ] **Step 7: Run the broader renderer/shell test suite for regressions**

Run: `uv run pytest tests/unit/ui/ tests/unit/engine/ -v`
Expected: PASS, no regressions

- [ ] **Step 8: Commit**

```bash
git add src/lexigram/admin/engine/renderer.py src/lexigram/admin/ui/templates/shell.py tests/unit/ui/test_shell_impersonation_banner.py
git commit -m "feat(admin): render impersonation banner with stop control (D7)"
```

---

## Task 9: Full-suite regression check

**Files:** None (verification only)

- [ ] **Step 1: Run the full lexigram-admin test suite**

Run: `cd lexigram-admin && uv run pytest --tb=short -q`
Expected: PASS, no regressions anywhere in the package

- [ ] **Step 2: Run lint and type checks**

Run: `cd lexigram-admin && uv run ruff check . --fix && uv run ruff format . && uv run mypy src/`
Expected: No errors (ruff may reformat/reorder imports touched by this plan — review the diff before committing)

- [ ] **Step 3: Confirm zero remaining references to the retired view**

Run: `grep -rn "UserImpersonationView" .`
Expected: No matches

- [ ] **Step 4: Commit any lint/format fixes**

```bash
git add -A
git commit -m "chore(admin): lint/format fixes after impersonation usability work"
```

(Skip this step if Step 2 made no changes.)
