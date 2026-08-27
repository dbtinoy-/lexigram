# Admin Tenancy Visibility & Switching Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give superadmins a working tenant switcher in the admin shell, and make tenant switching actually change what they see (dashboard widget preferences), by implementing D0–D4 from `docs/superpowers/specs/2026-08-19-admin-tenancy-visibility-design.md`.

**Architecture:** Tenant context is resolved once per request in `AdminController._apply_tenant_context` (new sibling to the existing `_apply_theme_overrides`) and written into `extra_context`. `AdminRenderer.render_page` reads those keys and threads them through `AdminShell` → `TopBar` → a new `TenantSwitcher` component (a plain auto-submitting `<select>` in a `<form>`, mirroring `LanguageSwitcher`'s proven shape). The switcher posts to a new `POST /admin/set-tenant` route on a new `TenancyController`, which validates superadmin + tenant existence, sets the `admin_tenant` cookie, and logs a `TENANT_SWITCHED` audit event. Six hardcoded `tenant_id = "default"` call sites in `controllers/widgets.py` are fixed to resolve the real tenant, so switching has a visible effect on dashboard widgets.

**Tech Stack:** Python 3.11+, Starlette, `lexigram-admin`'s own DI container (`@inject`), Jinja2 (only for the outer `admin_shell.html` chrome — everything else is the in-house `lexigram.ui` component system, `el()`/`Component`), pytest + pytest-asyncio (`asyncio_mode = "auto"`).

**Key finding not in the spec (discovered during file-structure mapping):** `request.state.csrf_token` — which `AdminRenderer.render_page` already reads for the `<meta name="csrf-token">`/`hx-headers` chrome — is only ever set by `resources/form_renderer.py` and `resources/handler.py` (resource CRUD form rendering). It is `None` on ordinary dashboard/widget pages, which is exactly where `TenantSwitcher` renders. Since `TenantSwitcher` is a plain (non-HTMX) form POST, it can't rely on the shell's `hx-headers` CSRF injection either (that only fires for `hx-*` requests — confirmed by reading `AdminCsrfMiddleware._validate_csrf`, which checks the form body's `csrf_token` field first for form-encoded POSTs, falling back to the `X-CSRF-Token` header only if the form field is absent). So Task 6 below generates a **fresh** CSRF token specifically for the switcher form (`tenant_csrf_token`, via the same `csrf_service.generate_token(session_id)` call `WidgetController._get_csrf_token` already uses), rather than trying to reuse the mostly-unset `request.state.csrf_token`. This is a necessary, surgical addition — not scope creep — because without it the switcher form would 403 on every real submission.

---

## File Structure

| File | Change |
|---|---|
| `src/lexigram/admin/auth/types.py` | Modify — add `TENANT_SWITCHED` to `AdminSecurityEventType` |
| `src/lexigram/admin/ui/organisms/topbar.py` | Modify — new `TenantSwitcher` component; `TopBar.__init__`/`render()` gain tenant params and render the switcher |
| `src/lexigram/admin/ui/templates/shell.py` | Modify — `AdminShell.__init__`/`render()` gain tenant params, thread to `TopBar` |
| `src/lexigram/admin/engine/renderer.py` | Modify — `render_page` reads tenant fields from `extra_context`, passes to `AdminShell` |
| `src/lexigram/admin/controllers/base.py` | Modify — new `_apply_tenant_context` async helper, called from `render_admin` |
| `src/lexigram/admin/controllers/tenancy.py` | Create — new `TenancyController` with `POST /admin/set-tenant` |
| `src/lexigram/admin/di/bundle_provider.py` | Modify — register + best-effort mount `TenancyController` |
| `src/lexigram/admin/controllers/widgets.py` | Modify — fix 6 hardcoded `tenant_id = "default"` sites |
| `tests/unit/auth/test_admin_security_event_types.py` | Create |
| `tests/unit/ui/test_tenant_switcher.py` | Create |
| `tests/unit/ui/test_topbar_tenant_switcher.py` | Create |
| `tests/unit/ui/test_shell_tenant_context.py` | Create |
| `tests/unit/engine/test_renderer_tenant_context.py` | Create |
| `tests/unit/controllers/test_base_tenant_context.py` | Create |
| `tests/unit/controllers/test_tenancy_controller.py` | Create |
| `tests/integration/test_tenancy_controller_routes.py` | Create |
| `tests/unit/controllers/test_widgets.py` | Modify — add 6 regression tests for D4 |

All commands below run from `lexigram-admin/` (where `pyproject.toml`'s `[tool.pytest.ini_options]` lives).

---

### Task 1: `TENANT_SWITCHED` audit event type

**Files:**
- Modify: `src/lexigram/admin/auth/types.py:47`
- Test: `tests/unit/auth/test_admin_security_event_types.py`

- [x] **Step 1: Write the failing test**

```python
"""Tests for new AdminSecurityEventType members."""

from __future__ import annotations

from lexigram.admin.auth.types import AdminSecurityEventType


class TestTenantSwitchedEventType:
    def test_tenant_switched_member_exists(self) -> None:
        assert AdminSecurityEventType.TENANT_SWITCHED == "tenant_switched"
```

- [x] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/auth/test_admin_security_event_types.py -v`
Expected: FAIL with `AttributeError: TENANT_SWITCHED`

- [x] **Step 3: Add the enum member**

In `src/lexigram/admin/auth/types.py`, find the last member of `AdminSecurityEventType` (currently `USER_REGISTERED = "user_registered"` at line 47) and add directly after it:

```python
    USER_REGISTERED = "user_registered"
    TENANT_SWITCHED = "tenant_switched"
```

- [x] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/auth/test_admin_security_event_types.py -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add src/lexigram/admin/auth/types.py tests/unit/auth/test_admin_security_event_types.py
git commit -m "feat(admin): add TENANT_SWITCHED audit event type"
```

---

### Task 2: `TenantSwitcher` component

**Files:**
- Modify: `src/lexigram/admin/ui/organisms/topbar.py` (add class after `LanguageSwitcher`, before `ThemeToggle`, i.e. after line 62)
- Test: `tests/unit/ui/test_tenant_switcher.py`

- [x] **Step 1: Write the failing tests**

```python
"""Tests for TenantSwitcher — superadmin tenant-switching control."""

from __future__ import annotations

from lexigram.admin.ui.organisms.topbar import TenantSwitcher
from lexigram.ui import render_to_string


class TestTenantSwitcher:
    def test_renders_nothing_when_no_tenants(self) -> None:
        html = render_to_string(TenantSwitcher(tenants=[], current_tenant_id=None))
        assert html.strip() == ""

    def test_renders_select_with_options(self) -> None:
        html = render_to_string(
            TenantSwitcher(
                tenants=[("acme", "Acme Corp"), ("globex", "Globex Inc")],
                current_tenant_id="acme",
            )
        )
        assert '<select' in html
        assert 'name="tenant_id"' in html
        assert "Acme Corp" in html
        assert "Globex Inc" in html

    def test_current_tenant_preselected(self) -> None:
        html = render_to_string(
            TenantSwitcher(
                tenants=[("acme", "Acme Corp"), ("globex", "Globex Inc")],
                current_tenant_id="globex",
            )
        )
        globex_idx = html.index('value="globex"')
        acme_idx = html.index('value="acme"')
        # "selected" attribute must appear on the globex <option>, not acme's
        assert "selected" in html[globex_idx : globex_idx + 60]
        assert "selected" not in html[acme_idx : acme_idx + 60]

    def test_posts_to_set_tenant_by_default(self) -> None:
        html = render_to_string(
            TenantSwitcher(tenants=[("acme", "Acme Corp")], current_tenant_id="acme")
        )
        assert 'action="/admin/set-tenant"' in html
        assert 'method="POST"' in html

    def test_includes_csrf_hidden_field_when_token_given(self) -> None:
        html = render_to_string(
            TenantSwitcher(
                tenants=[("acme", "Acme Corp")],
                current_tenant_id="acme",
                csrf_token="tok123",
            )
        )
        assert 'type="hidden"' in html
        assert 'name="csrf_token"' in html
        assert 'value="tok123"' in html

    def test_no_csrf_field_when_token_absent(self) -> None:
        html = render_to_string(
            TenantSwitcher(tenants=[("acme", "Acme Corp")], current_tenant_id="acme")
        )
        assert 'name="csrf_token"' not in html
```

- [x] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/ui/test_tenant_switcher.py -v`
Expected: FAIL with `ImportError: cannot import name 'TenantSwitcher'`

- [x] **Step 3: Implement `TenantSwitcher`**

In `src/lexigram/admin/ui/organisms/topbar.py`, insert this class immediately after `LanguageSwitcher` (after line 62, before `class ThemeToggle`):

```python
class TenantSwitcher(Component):
    """Superadmin-only tenant switcher for the admin topbar.

    Mirrors ``LanguageSwitcher``'s plain ``<select>``-in-``<form>``
    auto-submit shape (there is no dropdown-menu precedent in this file
    to follow instead). Renders nothing when *tenants* is empty — callers
    (``TopBar``) are responsible for only constructing this with data
    when tenancy is enabled and the requesting user is a superadmin; an
    empty list is what makes this a no-op in every other case.

    Unlike ``LanguageSwitcher``, this form carries a CSRF hidden field:
    it is a genuine plain-form POST (not HTMX), so the shell's
    ``hx-headers`` CSRF injection does not apply, and
    ``request.state.csrf_token`` is not reliably populated on the pages
    this switcher appears on (see plan header for details).

    Args:
        tenants: Ordered list of ``(tenant_id, name)`` pairs.
        current_tenant_id: The currently active tenant id, pre-selected.
        csrf_token: CSRF token embedded as a hidden form field, if given.
        action_url: URL that accepts a ``POST`` with ``tenant_id=<id>``.
    """

    def __init__(
        self,
        tenants: list[tuple[str, str]] | None = None,
        current_tenant_id: str | None = None,
        csrf_token: str | None = None,
        action_url: str = "/admin/set-tenant",
        **props: Any,
    ) -> None:
        super().__init__(**props)
        self.tenants = tenants or []
        self.current_tenant_id = current_tenant_id
        self.csrf_token = csrf_token
        self.action_url = action_url

    def render(self) -> Any:
        if not self.tenants:
            return ""
        options = [
            el(
                "option",
                name,
                value=tenant_id,
                selected=(tenant_id == self.current_tenant_id) or None,
            )
            for tenant_id, name in self.tenants
        ]
        select = el(
            "select",
            *options,
            name="tenant_id",
            class_=(
                "text-sm bg-transparent border border-border "
                "rounded px-2 py-1 text-foreground "
                "focus:outline-none focus:ring-2 focus:ring-ring cursor-pointer"
            ),
            **{"x-on:change": "$el.form.submit()"},
        )
        children: list[Any] = [select]
        if self.csrf_token:
            children.append(
                el(
                    "input",
                    type_="hidden",
                    name="csrf_token",
                    value=self.csrf_token,
                )
            )
        return el(
            "form",
            *children,
            method="POST",
            action=self.action_url,
            class_="inline-block",
        )
```

- [x] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/ui/test_tenant_switcher.py -v`
Expected: PASS (6 tests)

- [x] **Step 5: Commit**

```bash
git add src/lexigram/admin/ui/organisms/topbar.py tests/unit/ui/test_tenant_switcher.py
git commit -m "feat(admin): add TenantSwitcher component"
```

---

### Task 3: Wire `TenantSwitcher` into `TopBar`

**Files:**
- Modify: `src/lexigram/admin/ui/organisms/topbar.py:90-165` (`TopBar.__init__` and `render()`)
- Test: `tests/unit/ui/test_topbar_tenant_switcher.py`

- [x] **Step 1: Write the failing tests**

```python
"""Tests for TopBar's tenant-switcher threading."""

from __future__ import annotations

from lexigram.admin.ui.organisms.topbar import TopBar
from lexigram.ui import render_to_string


class TestTopBarTenantSwitcher:
    def test_no_switcher_when_current_tenant_id_absent(self) -> None:
        html = render_to_string(TopBar(title="Admin"))
        assert 'name="tenant_id"' not in html

    def test_switcher_rendered_when_tenant_context_present(self) -> None:
        html = render_to_string(
            TopBar(
                title="Admin",
                current_tenant_id="acme",
                current_tenant_name="Acme Corp",
                tenant_list=[("acme", "Acme Corp"), ("globex", "Globex Inc")],
                tenant_csrf_token="tok123",
            )
        )
        assert 'name="tenant_id"' in html
        assert "Acme Corp" in html
        assert "Globex Inc" in html
        assert 'value="tok123"' in html

    def test_switcher_appears_before_notification_bell(self) -> None:
        html = render_to_string(
            TopBar(
                title="Admin",
                current_tenant_id="acme",
                current_tenant_name="Acme Corp",
                tenant_list=[("acme", "Acme Corp")],
            )
        )
        switcher_idx = html.index('name="tenant_id"')
        bell_idx = html.index("notifications")
        assert switcher_idx < bell_idx
```

- [x] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/ui/test_topbar_tenant_switcher.py -v`
Expected: FAIL — `test_switcher_rendered_when_tenant_context_present` and `test_switcher_appears_before_notification_bell` fail (no switcher markup); `test_no_switcher_when_current_tenant_id_absent` passes trivially (accept this — it's asserting today's already-correct default behavior, kept as a regression guard).

- [x] **Step 3: Thread tenant params through `TopBar`**

In `src/lexigram/admin/ui/organisms/topbar.py`, modify `TopBar.__init__` (currently lines 90-108):

```python
    def __init__(
        self,
        title: str = "Admin",
        user: Any | None = None,
        user_menu_items: list[dict[str, Any]] | None = None,
        left: Any | None = None,
        center: Any | None = None,
        right: Any | None = None,
        site_name: str = "",
        current_tenant_id: str | None = None,
        current_tenant_name: str = "",
        tenant_list: list[tuple[str, str]] | None = None,
        tenant_csrf_token: str | None = None,
        **props: Any,
    ) -> None:
        super().__init__(**props)
        self.title_val = title
        self.site_name = site_name
        self.left = left
        self.center = center
        self.right = right
        self.user = user
        self.user_menu_items = user_menu_items
        self.current_tenant_id = current_tenant_id
        self.current_tenant_name = current_tenant_name
        self.tenant_list = tenant_list or []
        self.tenant_csrf_token = tenant_csrf_token
```

Then modify the default `right_node` block inside `render()` (currently lines 151-165):

```python
        # Default Right: TenantSwitcher (superadmin only) + NotificationBell + ThemeToggle
        right_node = self.right
        if right_node is None:
            from lexigram.ui import NotificationBell

            right_elements = []
            if self.current_tenant_id is not None:
                right_elements.append(
                    TenantSwitcher(
                        tenants=self.tenant_list,
                        current_tenant_id=self.current_tenant_id,
                        csrf_token=self.tenant_csrf_token,
                    )
                )
            right_elements.append(
                NotificationBell(inbox_url="/admin/notifications").render()
            )
            right_elements.append(ThemeToggle())
            right_node = el(
                "div",
                *right_elements,
                class_="flex items-center space-x-3",
            )
```

- [x] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/ui/test_topbar_tenant_switcher.py -v`
Expected: PASS (3 tests)

- [x] **Step 5: Run the full topbar/tenant-switcher suite together**

Run: `uv run pytest tests/unit/ui/test_tenant_switcher.py tests/unit/ui/test_topbar_tenant_switcher.py -v`
Expected: PASS (9 tests)

- [x] **Step 6: Commit**

```bash
git add src/lexigram/admin/ui/organisms/topbar.py tests/unit/ui/test_topbar_tenant_switcher.py
git commit -m "feat(admin): render TenantSwitcher in TopBar when tenant context present"
```

---

### Task 4: Thread tenant context through `AdminShell`

**Files:**
- Modify: `src/lexigram/admin/ui/templates/shell.py:17-71` (`__init__`), `:169-177` (`render()`'s `TopBar` construction)
- Test: `tests/unit/ui/test_shell_tenant_context.py`

- [x] **Step 1: Write the failing test**

```python
"""Tests for AdminShell threading tenant context into TopBar."""

from __future__ import annotations

from lexigram.admin.ui.templates.shell import AdminShell
from lexigram.ui import render_to_string


class TestAdminShellTenantContext:
    def test_tenant_switcher_absent_by_default(self) -> None:
        html = render_to_string(AdminShell(content="hello"))
        assert 'name="tenant_id"' not in html

    def test_tenant_context_reaches_topbar(self) -> None:
        html = render_to_string(
            AdminShell(
                content="hello",
                current_tenant_id="acme",
                current_tenant_name="Acme Corp",
                tenant_list=[("acme", "Acme Corp"), ("globex", "Globex Inc")],
                tenant_csrf_token="tok123",
            )
        )
        assert 'name="tenant_id"' in html
        assert "Acme Corp" in html
        assert "Globex Inc" in html
        assert 'value="tok123"' in html
```

- [x] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/ui/test_shell_tenant_context.py -v`
Expected: FAIL — `test_tenant_context_reaches_topbar` fails with `TypeError: AdminShell.__init__() got an unexpected keyword argument 'current_tenant_id'`

- [x] **Step 3: Thread tenant params through `AdminShell`**

In `src/lexigram/admin/ui/templates/shell.py`, modify `__init__` (currently lines 17-46) — add four new params after `dark_mode: str = ""` and assign them:

```python
    def __init__(
        self,
        content: Any,
        title: str = "Admin",
        user: Any | None = None,
        nav_items: list | None = None,
        user_menu_items: list | None = None,
        system_menu_items: list | None = None,
        sidebar: Sidebar | None = None,
        topbar: TopBar | None = None,
        flash_messages: list[dict[str, str]] | None = None,
        breadcrumbs: list[dict[str, Any]] | None = None,
        commands: list[dict[str, str]] | None = None,
        features: dict[str, bool] | None = None,
        theme_css: str = "",
        site_name: str = "",
        logo_url: str = "",
        dark_mode: str = "",
        current_tenant_id: str | None = None,
        current_tenant_name: str = "",
        tenant_list: list[tuple[str, str]] | None = None,
        tenant_csrf_token: str | None = None,
        **props: Any,
    ) -> None:
        super().__init__(**props)
        self.content = content
        self.title = title
        self.user = user or {}
        self.commands = commands or []
        self.features = features or {}
        self.theme_css = theme_css
        self.site_name = site_name
        self.logo_url = logo_url
        self.dark_mode = dark_mode
        self.current_tenant_id = current_tenant_id
        self.current_tenant_name = current_tenant_name
        self.tenant_list = tenant_list or []
        self.tenant_csrf_token = tenant_csrf_token
```

(Everything else in `__init__` after the old `self.dark_mode = dark_mode` line stays unchanged.)

Then modify the `TopBar` construction inside `render()` (currently lines 169-177):

```python
        # 2. Prepare TopBar
        topbar = self.topbar_instance
        if topbar is None:
            topbar = TopBar(
                title=self.title,
                site_name=self.site_name,
                user=self.user,
                user_menu_items=self.user_menu_items,
                current_tenant_id=self.current_tenant_id,
                current_tenant_name=self.current_tenant_name,
                tenant_list=self.tenant_list,
                tenant_csrf_token=self.tenant_csrf_token,
            )
```

- [x] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/ui/test_shell_tenant_context.py -v`
Expected: PASS (2 tests)

- [x] **Step 5: Run the existing shell test suite to check for regressions**

Run: `uv run pytest tests/unit/ui/test_shell_secondary_nav.py tests/unit/test_shell_system_menu_presence.py tests/unit/ui/test_shell_tenant_context.py -v`
Expected: PASS, no regressions

- [x] **Step 6: Commit**

```bash
git add src/lexigram/admin/ui/templates/shell.py tests/unit/ui/test_shell_tenant_context.py
git commit -m "feat(admin): thread tenant context from AdminShell into TopBar"
```

---

### Task 5: Thread tenant context through `AdminRenderer.render_page`

**Files:**
- Modify: `src/lexigram/admin/engine/renderer.py:159-181`
- Test: `tests/unit/engine/test_renderer_tenant_context.py`

- [x] **Step 1: Write the failing test**

```python
"""Tests for AdminRenderer threading tenant extra_context into AdminShell."""

from __future__ import annotations

from lexigram.admin.engine.renderer import AdminRenderer


class TestRendererTenantContext:
    def test_tenant_fields_reach_rendered_html(self) -> None:
        renderer = AdminRenderer()
        response = renderer.render_page(
            "hello",
            request=None,
            title="Dashboard",
            current_tenant_id="acme",
            current_tenant_name="Acme Corp",
            tenant_list=[("acme", "Acme Corp"), ("globex", "Globex Inc")],
            tenant_csrf_token="tok123",
        )
        body = response.body.decode()
        assert 'name="tenant_id"' in body
        assert "Acme Corp" in body
        assert "Globex Inc" in body
        assert 'value="tok123"' in body

    def test_no_tenant_fields_means_no_switcher(self) -> None:
        renderer = AdminRenderer()
        response = renderer.render_page("hello", request=None, title="Dashboard")
        body = response.body.decode()
        assert 'name="tenant_id"' not in body
```

- [x] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/engine/test_renderer_tenant_context.py -v`
Expected: FAIL — `test_tenant_fields_reach_rendered_html` fails (no switcher markup in output)

- [x] **Step 3: Read tenant fields from `extra_context` and pass to `AdminShell`**

In `src/lexigram/admin/engine/renderer.py`, modify `render_page` — after the existing block that reads `site_name`/`logo_url`/`favicon_url`/`dark_mode` (currently lines 163-166), add:

```python
        site_name = extra_context.get("site_name") or self.config.site_name
        logo_url = extra_context.get("logo_url") or ""
        favicon_url = extra_context.get("favicon_url") or ""
        dark_mode = extra_context.get("dark_mode") or ""
        current_tenant_id = extra_context.get("current_tenant_id")
        current_tenant_name = extra_context.get("current_tenant_name") or ""
        tenant_list = extra_context.get("tenant_list") or []
        tenant_csrf_token = extra_context.get("tenant_csrf_token")

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
            current_tenant_id=current_tenant_id,
            current_tenant_name=current_tenant_name,
            tenant_list=tenant_list,
            tenant_csrf_token=tenant_csrf_token,
        )
```

(This replaces the old `shell = AdminShell(...)` block at lines 168-181 — same fields, four new ones added.)

- [x] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/engine/test_renderer_tenant_context.py -v`
Expected: PASS (2 tests)

- [x] **Step 5: Run the existing renderer test suite to check for regressions**

Run: `uv run pytest tests/unit/engine/test_renderer_shell_escape.py tests/unit/engine/test_renderer_tenant_context.py -v`
Expected: PASS, no regressions

- [x] **Step 6: Commit**

```bash
git add src/lexigram/admin/engine/renderer.py tests/unit/engine/test_renderer_tenant_context.py
git commit -m "feat(admin): thread tenant extra_context into AdminShell in render_page"
```

---

### Task 6: `_apply_tenant_context` — resolve tenant context before rendering (D0)

**Files:**
- Modify: `src/lexigram/admin/controllers/base.py` (new method after `_apply_theme_overrides`, i.e. after line 166; call site in `render_admin` at line 189)
- Test: `tests/unit/controllers/test_base_tenant_context.py`

This is the task that actually makes the switcher appear: it populates the `extra_context` keys Tasks 3-5 already know how to render.

- [x] **Step 1: Write the failing tests**

```python
"""Tests for AdminController._apply_tenant_context."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.admin.controllers.base import AdminController


def _make_controller() -> AdminController:
    return AdminController(renderer=MagicMock())


def _make_request(
    *,
    container: MagicMock,
    user: SimpleNamespace | None,
    tenant_id: str | None = None,
) -> MagicMock:
    request = MagicMock()
    request.state = SimpleNamespace(
        container=container, user=user, tenant_id=tenant_id
    )
    request.session = {"admin_user_id": "u1"}
    request.headers = {}
    request.cookies = {}
    return request


class TestApplyTenantContext:
    @pytest.mark.asyncio
    async def test_noop_when_tenancy_disabled(self) -> None:
        from lexigram.admin.config import AdminConfig

        config = AdminConfig()
        config.tenancy.enabled = False
        container = MagicMock()
        container.resolve = AsyncMock(return_value=config)

        controller = _make_controller()
        request = _make_request(
            container=container, user=SimpleNamespace(roles=["superadmin"])
        )
        extra_context: dict = {}
        await controller._apply_tenant_context(request, extra_context)

        assert extra_context == {}

    @pytest.mark.asyncio
    async def test_noop_when_user_not_superadmin(self) -> None:
        from lexigram.admin.config import AdminConfig

        config = AdminConfig()
        config.tenancy.enabled = True
        container = MagicMock()
        container.resolve = AsyncMock(return_value=config)

        controller = _make_controller()
        request = _make_request(
            container=container, user=SimpleNamespace(roles=["editor"])
        )
        extra_context: dict = {}
        await controller._apply_tenant_context(request, extra_context)

        assert extra_context == {}

    @pytest.mark.asyncio
    async def test_populates_context_for_superadmin(self) -> None:
        from lexigram.admin.config import AdminConfig
        from lexigram.admin.multitenancy.adapter import TenantProviderRegistry
        from lexigram.admin.multitenancy.models import TenantConfig

        config = AdminConfig()
        config.tenancy.enabled = True

        registry = TenantProviderRegistry()
        await registry.add(TenantConfig(tenant_id="acme", name="Acme Corp"))
        await registry.add(TenantConfig(tenant_id="globex", name="Globex Inc"))

        csrf_service = MagicMock()
        csrf_service.generate_token.return_value = "tok123"

        from lexigram.admin.auth.protocols import AdminCsrfServiceProtocol

        async def resolve(cls: type) -> object:
            if cls is AdminConfig:
                return config
            if cls is TenantProviderRegistry:
                return registry
            if cls is AdminCsrfServiceProtocol:
                return csrf_service
            raise AssertionError(f"unexpected resolve({cls})")

        container = MagicMock()
        container.resolve = AsyncMock(side_effect=resolve)

        controller = _make_controller()
        request = _make_request(
            container=container,
            user=SimpleNamespace(roles=["superadmin"]),
            tenant_id="acme",
        )
        extra_context: dict = {}
        await controller._apply_tenant_context(request, extra_context)

        assert extra_context["current_tenant_id"] == "acme"
        assert extra_context["current_tenant_name"] == "Acme Corp"
        assert set(extra_context["tenant_list"]) == {
            ("acme", "Acme Corp"),
            ("globex", "Globex Inc"),
        }
        assert extra_context["tenant_csrf_token"] == "tok123"

    @pytest.mark.asyncio
    async def test_falls_back_to_raw_id_when_registry_has_no_match(self) -> None:
        from lexigram.admin.config import AdminConfig
        from lexigram.admin.multitenancy.adapter import TenantProviderRegistry

        config = AdminConfig()
        config.tenancy.enabled = True
        registry = TenantProviderRegistry()  # empty — no matching tenant

        from lexigram.admin.auth.protocols import AdminCsrfServiceProtocol

        async def resolve(cls: type) -> object:
            if cls is AdminConfig:
                return config
            if cls is TenantProviderRegistry:
                return registry
            if cls is AdminCsrfServiceProtocol:
                raise RuntimeError("no csrf service in this test")
            raise AssertionError(f"unexpected resolve({cls})")

        container = MagicMock()
        container.resolve = AsyncMock(side_effect=resolve)

        controller = _make_controller()
        request = _make_request(
            container=container,
            user=SimpleNamespace(roles=["superadmin"]),
            tenant_id="deleted-tenant",
        )
        extra_context: dict = {}
        await controller._apply_tenant_context(request, extra_context)

        assert extra_context["current_tenant_id"] == "deleted-tenant"
        assert extra_context["current_tenant_name"] == "deleted-tenant"
        assert extra_context["tenant_list"] == []
        assert "tenant_csrf_token" not in extra_context
```

- [x] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/controllers/test_base_tenant_context.py -v`
Expected: FAIL with `AttributeError: 'AdminController' object has no attribute '_apply_tenant_context'`

- [x] **Step 3: Implement `_apply_tenant_context`**

In `src/lexigram/admin/controllers/base.py`, insert this method immediately after `_apply_theme_overrides` (after line 166, before `async def render_admin`):

```python
    async def _apply_tenant_context(
        self,
        request: Request,
        extra_context: dict[str, Any],
    ) -> None:
        """Resolve current tenant + switchable list into extra_context.

        Populates ``current_tenant_id``/``current_tenant_name``/
        ``tenant_list``/``tenant_csrf_token`` only when tenancy is enabled
        and the requesting user is a superadmin — presence of
        ``current_tenant_id`` doubles as the render gate for
        ``TenantSwitcher`` (absent means "don't show the switcher"), so no
        separate flag is threaded through.

        ``tenant_csrf_token`` is generated fresh via the CSRF service
        rather than reusing ``request.state.csrf_token``, because that
        value is only populated by resource CRUD form rendering
        (``resources/form_renderer.py``, ``resources/handler.py``), not on
        the dashboard/widget pages this switcher actually appears on.
        """
        try:
            from lexigram.admin.config import AdminConfig

            container = getattr(request.state, "container", None) or getattr(
                request.app.state, "container", None
            )
            if container is None:
                return
            config = await container.resolve(AdminConfig)
            if not config.tenancy.enabled:
                return

            user = getattr(request.state, "user", None)
            if not user:
                return

            from lexigram.admin.rbac.super_admin import is_super_admin

            if not is_super_admin(user, config.rbac.super_admin_role):
                return

            from lexigram.admin.multitenancy.adapter import (
                TenantProviderRegistry,
                resolve_tenant_id,
            )

            registry = await container.resolve(TenantProviderRegistry)
            current_tenant_id = await resolve_tenant_id(request, default="default")
            current_tenant = await registry.get(current_tenant_id)
            extra_context.setdefault("current_tenant_id", current_tenant_id)
            extra_context.setdefault(
                "current_tenant_name",
                current_tenant.name if current_tenant else current_tenant_id,
            )
            extra_context.setdefault(
                "tenant_list",
                [(t.tenant_id, t.name) for t in await registry.all(active_only=True)],
            )

            try:
                from lexigram.admin.auth.protocols import AdminCsrfServiceProtocol

                csrf_service = await container.resolve(AdminCsrfServiceProtocol)
                session = getattr(request, "session", {})
                session_id = session.get("admin_user_id", "")
                extra_context.setdefault(
                    "tenant_csrf_token", csrf_service.generate_token(session_id)
                )
            except Exception:  # noqa: BLE001, S110 — token generation is non-fatal
                pass
        except Exception:  # noqa: BLE001, S110 — matches _apply_theme_overrides
            pass
```

Then, in `render_admin` (currently lines 168-209), add the new call right after the existing `_apply_theme_overrides` call:

```python
        # Inject runtime theme overrides (primary_color, site_name)
        await self._apply_theme_overrides(request, extra_context)

        # Inject tenant context (current tenant, switchable list, CSRF token)
        await self._apply_tenant_context(request, extra_context)
```

- [x] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/controllers/test_base_tenant_context.py -v`
Expected: PASS (4 tests)

- [x] **Step 5: Commit**

```bash
git add src/lexigram/admin/controllers/base.py tests/unit/controllers/test_base_tenant_context.py
git commit -m "feat(admin): resolve tenant context before rendering (D0)"
```

---

### Task 7: `POST /admin/set-tenant` route on a new `TenancyController` (D2)

**Files:**
- Create: `src/lexigram/admin/controllers/tenancy.py`
- Test: `tests/unit/controllers/test_tenancy_controller.py`

- [x] **Step 1: Write the failing tests**

```python
"""Unit tests for TenancyController.set_tenant."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.admin.config import AdminConfig
from lexigram.admin.controllers.tenancy import TenancyController
from lexigram.admin.multitenancy.adapter import TenantProviderRegistry
from lexigram.admin.multitenancy.models import TenantConfig


def _make_request(
    *, form: dict, user: SimpleNamespace | None, tenant_id: str | None = None
) -> MagicMock:
    request = MagicMock()
    request.state = SimpleNamespace(user=user, tenant_id=tenant_id)
    request.scope = {"admin_form_data": form}
    request.headers = {"referer": "/admin/dashboard"}
    request.client = SimpleNamespace(host="127.0.0.1")
    return request


class TestSetTenant:
    @pytest.mark.asyncio
    async def test_returns_404_when_tenancy_disabled(self) -> None:
        config = AdminConfig()
        config.tenancy.enabled = False
        controller = TenancyController(config=config, registry=None)
        request = _make_request(
            form={"tenant_id": "acme"}, user=SimpleNamespace(roles=["superadmin"])
        )

        response = await controller.set_tenant(request)

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_returns_403_for_non_superadmin(self) -> None:
        config = AdminConfig()
        config.tenancy.enabled = True
        registry = TenantProviderRegistry()
        controller = TenancyController(config=config, registry=registry)
        request = _make_request(
            form={"tenant_id": "acme"}, user=SimpleNamespace(roles=["editor"])
        )

        response = await controller.set_tenant(request)

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_returns_400_for_unknown_tenant(self) -> None:
        config = AdminConfig()
        config.tenancy.enabled = True
        registry = TenantProviderRegistry()
        controller = TenancyController(config=config, registry=registry)
        request = _make_request(
            form={"tenant_id": "nonexistent"},
            user=SimpleNamespace(roles=["superadmin"]),
        )

        response = await controller.set_tenant(request)

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_returns_400_for_missing_tenant_id(self) -> None:
        config = AdminConfig()
        config.tenancy.enabled = True
        registry = TenantProviderRegistry()
        controller = TenancyController(config=config, registry=registry)
        request = _make_request(
            form={}, user=SimpleNamespace(roles=["superadmin"])
        )

        response = await controller.set_tenant(request)

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_success_sets_cookie_and_redirects(self) -> None:
        config = AdminConfig()
        config.tenancy.enabled = True
        registry = TenantProviderRegistry()
        await registry.add(TenantConfig(tenant_id="acme", name="Acme Corp"))
        controller = TenancyController(config=config, registry=registry)
        request = _make_request(
            form={"tenant_id": "acme"},
            user=SimpleNamespace(roles=["superadmin"]),
            tenant_id="default",
        )

        response = await controller.set_tenant(request)

        assert response.status_code == 303
        assert response.headers["location"] == "/admin/dashboard"
        set_cookie = response.headers.get("set-cookie", "")
        assert config.tenancy.cookie_name in set_cookie
        assert "acme" in set_cookie

    @pytest.mark.asyncio
    async def test_success_logs_audit_event(self) -> None:
        config = AdminConfig()
        config.tenancy.enabled = True
        registry = TenantProviderRegistry()
        await registry.add(TenantConfig(tenant_id="acme", name="Acme Corp"))
        audit_service = MagicMock()
        audit_service.log_event = AsyncMock()
        controller = TenancyController(
            config=config, registry=registry, audit_service=audit_service
        )
        request = _make_request(
            form={"tenant_id": "acme"},
            user=SimpleNamespace(roles=["superadmin"]),
            tenant_id="default",
        )

        await controller.set_tenant(request)

        audit_service.log_event.assert_awaited_once()
        _, kwargs = audit_service.log_event.await_args
        from lexigram.admin.auth.types import AdminSecurityEventType

        assert kwargs["event_type"] == AdminSecurityEventType.TENANT_SWITCHED
        assert kwargs["success"] is True
        assert kwargs["metadata"] == {"from_tenant": "default", "to_tenant": "acme"}
```

- [x] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/controllers/test_tenancy_controller.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'lexigram.admin.controllers.tenancy'`

- [x] **Step 3: Implement `TenancyController`**

Create `src/lexigram/admin/controllers/tenancy.py`:

```python
"""Tenant-switching controller for the admin panel."""

from __future__ import annotations

from typing import Any

from starlette.requests import Request
from starlette.responses import RedirectResponse, Response

from lexigram.admin.auth.protocols import AdminAuditLogServiceProtocol
from lexigram.admin.auth.types import AdminSecurityEventType
from lexigram.admin.config import AdminConfig
from lexigram.admin.multitenancy.adapter import TenantProviderRegistry
from lexigram.admin.rbac.super_admin import is_super_admin
from lexigram.contracts.web import post
from lexigram.di.decorators import inject
from lexigram.logging import get_logger

logger = get_logger(__name__)


@inject
class TenancyController:
    """Handles superadmin tenant-switching.

    CSRF is validated by the global ``AdminCsrfMiddleware`` already applied
    to every admin POST route — this controller does not duplicate that
    check.
    """

    prefix = ""

    def __init__(
        self,
        config: AdminConfig,
        registry: TenantProviderRegistry | None = None,
        audit_service: AdminAuditLogServiceProtocol | None = None,
    ) -> None:
        self._config = config
        self._registry = registry
        self._audit_service = audit_service

    @post("/set-tenant")
    async def set_tenant(self, request: Request) -> Response:
        """Switch the active tenant for a superadmin session."""
        if not self._config.tenancy.enabled or self._registry is None:
            return Response(status_code=404)

        user = getattr(request.state, "user", None)
        if not user or not is_super_admin(user, self._config.rbac.super_admin_role):
            return Response(content="Forbidden", status_code=403)

        data = request.scope.get("admin_form_data")
        if data is None:
            data = await request.form()
        tenant_id = str(data.get("tenant_id", "")).strip()

        tenant = await self._registry.get(tenant_id) if tenant_id else None
        if tenant is None:
            return Response(content="Unknown tenant", status_code=400)

        previous_tenant_id = getattr(request.state, "tenant_id", None) or "default"

        redirect_to = request.headers.get("referer") or "/admin/"
        response = RedirectResponse(url=redirect_to, status_code=303)
        response.set_cookie(
            self._config.tenancy.cookie_name,
            tenant.tenant_id,
            httponly=True,
            samesite="lax",
        )

        await self._audit(
            request,
            from_tenant=previous_tenant_id,
            to_tenant=tenant.tenant_id,
        )

        return response

    async def _audit(self, request: Request, **metadata: Any) -> None:
        """Log a TENANT_SWITCHED event, best-effort."""
        if not self._audit_service:
            return
        try:
            client = getattr(request, "client", None)
            await self._audit_service.log_event(
                event_type=AdminSecurityEventType.TENANT_SWITCHED,
                ip_address=getattr(client, "host", "unknown"),
                user_agent=request.headers.get("user-agent", "") or "",
                success=True,
                metadata=metadata,
            )
        except Exception:  # noqa: BLE001 — audit failures must not break the switch
            logger.warning("tenancy.audit_failed", **metadata)
```

- [x] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/controllers/test_tenancy_controller.py -v`
Expected: PASS (6 tests)

- [x] **Step 5: Commit**

```bash
git add src/lexigram/admin/controllers/tenancy.py tests/unit/controllers/test_tenancy_controller.py
git commit -m "feat(admin): add POST /admin/set-tenant route (D2)"
```

---

### Task 8: Register and mount `TenancyController` in DI

**Files:**
- Modify: `src/lexigram/admin/di/bundle_provider.py` (register() around line 162; mount_to_app() best-effort block modeled on WidgetController's, currently lines 314-352)
- Test: `tests/integration/test_tenancy_controller_routes.py`

- [x] **Step 1: Write the failing integration test**

Model this on `tests/integration/test_widget_controller_routes.py`'s `create_widget_app()` helper — build a minimal Starlette app with the route wired directly to the controller method (bypassing full DI/mount machinery), so this test exercises the actual `TenancyController.set_tenant` route end-to-end without needing the whole `AdminProvider` boot sequence.

```python
"""Integration tests for POST /admin/set-tenant."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from starlette.applications import Starlette
from starlette.routing import Route

from lexigram.admin.config import AdminConfig
from lexigram.admin.controllers.tenancy import TenancyController
from lexigram.admin.multitenancy.adapter import TenantProviderRegistry
from lexigram.admin.multitenancy.models import TenantConfig


async def _create_tenancy_app(
    *, roles: list[str], tenants: list[TenantConfig] | None = None
) -> Starlette:
    config = AdminConfig()
    config.tenancy.enabled = True
    registry = TenantProviderRegistry()
    for tenant in tenants or []:
        await registry.add(tenant)
    controller = TenancyController(config=config, registry=registry)

    async def set_tenant_endpoint(request):
        request.state.user = MagicMock(roles=roles)
        request.state.tenant_id = "default"
        return await controller.set_tenant(request)

    app = Starlette(
        routes=[Route("/admin/set-tenant", set_tenant_endpoint, methods=["POST"])]
    )
    return app


class TestSetTenantRoute:
    @pytest.mark.asyncio
    async def test_superadmin_switch_returns_303_and_sets_cookie(self) -> None:
        app = await _create_tenancy_app(
            roles=["superadmin"],
            tenants=[TenantConfig(tenant_id="acme", name="Acme Corp")],
        )
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            response = await client.post(
                "/admin/set-tenant",
                data={"tenant_id": "acme"},
                headers={"referer": "/admin/dashboard"},
                follow_redirects=False,
            )
        assert response.status_code == 303
        assert "admin_tenant" in response.headers.get("set-cookie", "")

    @pytest.mark.asyncio
    async def test_non_superadmin_returns_403(self) -> None:
        app = await _create_tenancy_app(
            roles=["editor"],
            tenants=[TenantConfig(tenant_id="acme", name="Acme Corp")],
        )
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            response = await client.post(
                "/admin/set-tenant",
                data={"tenant_id": "acme"},
                follow_redirects=False,
            )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_unknown_tenant_returns_400(self) -> None:
        app = await _create_tenancy_app(roles=["superadmin"], tenants=[])
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            response = await client.post(
                "/admin/set-tenant",
                data={"tenant_id": "nonexistent"},
                follow_redirects=False,
            )
        assert response.status_code == 400
```

- [x] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/integration/test_tenancy_controller_routes.py -v`
Expected: FAIL with `ModuleNotFoundError` (same missing module as Task 7 — this confirms Task 7's implementation, if not yet committed in a real run, must land first; when run after Task 7 is done, this instead validates the route works over real HTTP)

Since Task 7 already created `controllers/tenancy.py`, this test should actually **pass immediately** once written — that's expected and fine (it's an end-to-end regression check on top of Task 7's unit tests, not new production code). If it fails for any reason other than the controller already existing, treat that as a real bug to fix before proceeding.

- [x] **Step 3: Run test to verify it passes**

Run: `uv run pytest tests/integration/test_tenancy_controller_routes.py -v`
Expected: PASS (3 tests)

- [x] **Step 4: Wire `TenancyController` into DI registration**

In `src/lexigram/admin/di/bundle_provider.py`, `register()` method — add the import and singleton registration next to `WidgetController`'s (currently line 104 and line 162):

```python
        from lexigram.admin.controllers.dashboard import DashboardController
        from lexigram.admin.controllers.tenancy import TenancyController
        from lexigram.admin.controllers.widgets import WidgetController
```

```python
        # Register built-in controllers
        container.singleton(WidgetController, WidgetController)
        container.singleton(TenancyController, TenancyController)
        container.singleton(DashboardController, DashboardController)
```

- [x] **Step 5: Wire `TenancyController` into `mount_to_app`**

In the same file, `mount_to_app()` — add a new best-effort resolution block immediately after the existing "Resolve built-in WidgetController" block (after line 352, before "Resolve built-in DashboardController"):

```python
        # Resolve built-in TenancyController (best-effort)
        try:
            from lexigram.admin.auth.protocols import (
                AdminAuditLogServiceProtocol,
            )
            from lexigram.admin.controllers.tenancy import TenancyController
            from lexigram.admin.multitenancy.adapter import TenantProviderRegistry

            tenancy_controller = await admin_resolver.resolve(
                TenancyController,
                bypass_visibility=True,
            )
            controller_instances.append(tenancy_controller)
            if self._config.tenancy.enabled:
                try:
                    tenancy_controller._registry = await admin_resolver.resolve(
                        TenantProviderRegistry,
                        bypass_visibility=True,
                    )
                except Exception:
                    tenancy_controller._registry = None
            try:
                audit_service = await admin_resolver.resolve(
                    AdminAuditLogServiceProtocol,
                    bypass_visibility=True,
                )
            except Exception:
                audit_service = None
            if audit_service is not None:
                tenancy_controller._audit_service = audit_service
        except Exception as exc:
            _log.error(
                "admin.tenancy_controller_resolution_failed",
                error=str(exc),
                strict=self._config.strict_resource_resolution,
            )
            self._mount_failures["controller:TenancyController"] = str(exc)
            if self._config.strict_resource_resolution:
                raise
```

Note: `TenancyController` is resolved via DI with `registry: TenantProviderRegistry | None = None` as a constructor default, so resolution succeeds even when tenancy is disabled and `TenantProviderRegistry` was never registered (per `AdminTenancySubProvider.register`, which returns early when `config.tenancy.enabled` is `False`). The explicit re-resolution above only runs when tenancy is enabled, matching that sub-provider's own gate.

- [x] **Step 6: Run the full test suite for this task**

Run: `uv run pytest tests/integration/test_tenancy_controller_routes.py tests/unit/controllers/test_tenancy_controller.py -v`
Expected: PASS (9 tests)

- [x] **Step 7: Commit**

```bash
git add src/lexigram/admin/di/bundle_provider.py tests/integration/test_tenancy_controller_routes.py
git commit -m "feat(admin): register and mount TenancyController"
```

---

### Task 9: Fix hardcoded tenant scoping in `controllers/widgets.py` (D4)

**Files:**
- Modify: `src/lexigram/admin/controllers/widgets.py:219, 362, 419, 476, 507, 637`
- Test: `tests/unit/controllers/test_widgets.py` (extend existing file)

- [x] **Step 1: Write the failing tests**

Add this class to the end of `tests/unit/controllers/test_widgets.py`:

```python
class TestWidgetControllerTenantScoping:
    """D4: dashboard widget prefs must resolve the real tenant, not hardcode 'default'."""

    @pytest.mark.asyncio
    async def test_render_widget_uses_resolved_tenant(self) -> None:
        mock_registry = MagicMock()
        mock_contributor = MagicMock()
        mock_registry.get.return_value = mock_contributor
        mock_contributor.render_widget = AsyncMock(
            return_value=Ok(WidgetViewModel(content=MessageContent(text="ok")))
        )
        settings_service = MagicMock()
        settings_service.get_widget_prefs = AsyncMock(return_value={"configs": {}})
        controller = WidgetController(registry=mock_registry)
        controller._settings_service = settings_service

        mock_request = MagicMock()
        mock_request.query_params = {}
        mock_request.state = SimpleNamespace(tenant_id="acme")

        await controller.render_widget(
            request=mock_request, contributor_id="c1", widget_name="w1"
        )

        settings_service.get_widget_prefs.assert_awaited_once_with("acme", "default")

    @pytest.mark.asyncio
    async def test_widget_config_popup_uses_resolved_tenant(self) -> None:
        controller = WidgetController(registry=MagicMock())
        controller._registry.get_all.return_value = []
        mock_request = MagicMock()
        mock_request.state = SimpleNamespace(tenant_id="acme")

        import lexigram.admin.controllers.widgets as widgets_module
        from lexigram.admin.multitenancy.adapter import resolve_tenant_id as original

        captured: dict[str, str] = {}

        async def spy(request, *, default):
            resolved = await original(request, default=default)
            captured["tenant_id"] = resolved
            return resolved

        widgets_module.resolve_tenant_id = spy
        try:
            await controller.widget_config_popup(request=mock_request, name="w1")
        finally:
            widgets_module.resolve_tenant_id = original

        assert captured["tenant_id"] == "acme"
```

Note: the second test spies on `resolve_tenant_id` **as bound into `controllers/widgets.py`'s own namespace** (`widgets_module.resolve_tenant_id`), not on the `multitenancy.adapter` module where it's defined. Since Step 3 below adds a direct-name import (`from lexigram.admin.multitenancy.adapter import resolve_tenant_id`), `widgets.py` binds its own local reference at import time — patching the attribute on `adapter` afterward would not affect that already-bound name, so the spy would never be called. Patching the name where it's *used* is required. Add `from types import SimpleNamespace` to the imports at the top of the test file if not already present.

- [x] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/controllers/test_widgets.py -v -k TenantScoping`
Expected: FAIL — `test_render_widget_uses_resolved_tenant` fails (`get_widget_prefs` called with `("default", "default")`, not `("acme", "default")`); `test_widget_config_popup_uses_resolved_tenant` fails (`captured` stays empty, `resolve_tenant_id` never called)

- [x] **Step 3: Add the import**

In `src/lexigram/admin/controllers/widgets.py`, add this import anywhere in the existing top-of-file import block (e.g. directly before line 20, `from lexigram.admin.rbac.super_admin import is_super_admin`):

```python
from lexigram.admin.multitenancy.adapter import resolve_tenant_id
```

Exact placement doesn't matter — `uv run ruff check . --fix` (Task 10) will sort imports alphabetically regardless.

- [x] **Step 4: Fix the 6 call sites**

Site 1 — `render_widget` (line 219), replace:
```python
            prefs = await self._settings_service.get_widget_prefs("default", "default")
```
with:
```python
            tenant_id = await resolve_tenant_id(request, default="default")
            prefs = await self._settings_service.get_widget_prefs(tenant_id, "default")
```

Site 2 — `widget_config_popup` (line 362), replace:
```python
        tenant_id = "default"
        user_id = "default"
```
with:
```python
        tenant_id = await resolve_tenant_id(request, default="default")
        user_id = "default"
```

Site 3 — `save_widget_config` (line 419), same replacement as Site 2.

Site 4 — `reorder_widgets` (line 476), same replacement as Site 2.

Site 5 — `customize_all_widgets` (line 507), same replacement as Site 2.

Site 6 — `save_all_widget_configs` (line 637), same replacement as Site 2.

(All five of sites 2-6 share the identical two-line `tenant_id = "default"` / `user_id = "default"` pattern — same fix applies verbatim at each location. `user_id` stays untouched at every site per D4's explicit scope boundary.)

- [x] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/unit/controllers/test_widgets.py -v`
Expected: PASS, including all pre-existing tests in this file (no regressions) plus the 2 new ones

- [x] **Step 6: Run the full widgets-related test suite**

Run: `uv run pytest tests/unit/controllers/test_widgets.py tests/unit/controllers/test_widgets_superadmin_configurable.py -v`
Expected: PASS, no regressions

- [x] **Step 7: Commit**

```bash
git add src/lexigram/admin/controllers/widgets.py tests/unit/controllers/test_widgets.py
git commit -m "fix(admin): resolve real tenant in widget prefs instead of hardcoding default (D4)"
```

---

### Task 10: Full-suite regression check

- [x] **Step 1: Run the entire lexigram-admin test suite**

Run: `uv run pytest --tb=short`
Expected: PASS, no regressions anywhere in the package (this also re-confirms coverage stays at or above the configured `--cov-fail-under=60` threshold, since 4 new source files/methods now have dedicated tests)

- [x] **Step 2: Run ruff and mypy per the workspace's CI commands**

Run (from `framework/`): `cd .. && uv run ruff check lexigram-admin/ --fix && uv run ruff format lexigram-admin/ && uv run mypy lexigram-admin/src/`
Expected: No errors. Fix any lint/type issues surfaced before considering this plan complete.

- [x] **Step 3: Manually smoke-test the switcher (optional but recommended)**

If a local dev instance with `tenancy.enabled=True` and at least 2 registered tenants is available, log in as a superadmin, confirm the switcher appears in the topbar, switch tenants, and confirm the dashboard widget preferences change and an audit log entry appears. This is out of reach for an automated step but worth doing before considering the feature done end-to-end.
