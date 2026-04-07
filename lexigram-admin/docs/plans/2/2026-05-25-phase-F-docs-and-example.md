# Phase F — Docs & Example: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Source review:** `REVIEW2.md` §8 (Missing Docs, Tests, Contracts), §6 (Strategic answer), Appendix B (Verdict Summary)
> **Parent track:** `docs/plans/2/README.md`
> **Estimate:** 1 week
> **Risk:** LOW — docs and example code only; no production behavior changes
> **Blocks:** none
> **Blocked by:** Phases A, B, C, E (the docs describe the new surface; the example exercises it)

**Goal:** Make the new framework-composition story discoverable. Ship (1) an **Extension Developer Guide** that walks a third-party package author through contributing every supported capability end-to-end, and (2) a working `examples/lexigram-admin-plugin-demo/` package that contributes resources, pages, widgets, settings panels, routes, and a cache integration — all via a single `BaseAdminContributor` subclass.

**Architecture:** The example package lives in `examples/lexigram-admin-plugin-demo/` next to the existing `examples/platform/`. It declares itself as a plugin via `[project.entry-points."lexigram.admin.contributors"]` and uses every contribution surface (Phases A through E). The Extension Developer Guide reads as a top-to-bottom narrative from "create a package" to "publish to PyPI," with the example package as the running illustration.

**Tech Stack:** Python 3.11+, all of `lexigram-admin`'s public surface, Markdown for docs.

---

## File Structure Map

### Create — Documentation

```
lexigram-admin/docs/
├── EXTENSION_DEVELOPER_GUIDE.md       # NEW — top-level narrative guide
├── CONTRIBUTOR_REFERENCE.md           # NEW — exhaustive reference for BaseAdminContributor surface
├── FRAMEWORK_COMPOSITION.md           # NEW — which framework package supplies what to admin
├── MIGRATION_TO_DELEGATED_AUTH.md     # NEW — for apps that overrode AdminAuthGuard pre-Phase-D.1
└── GUIDE.md                           # FILL IN — currently 622B stub; turn into landing page that links the above
```

### Create — Example package

```
examples/lexigram-admin-plugin-demo/
├── pyproject.toml                     # entry-points block + dependency on lexigram-admin[cache]
├── README.md
├── src/lexigram_admin_plugin_demo/
│   ├── __init__.py
│   ├── contributor.py                 # DemoContributor — the single entry point
│   ├── resources/
│   │   ├── __init__.py
│   │   ├── widget.py                  # WidgetResource (CRUD example, cacheable=True)
│   │   └── audit_log.py               # AuditLogResource (searchable=True, read-only)
│   ├── pages/
│   │   └── overview.py                # DemoOverviewPage (full custom page)
│   ├── settings/
│   │   └── panel.py                   # DemoSettingsPanel
│   ├── widgets/
│   │   └── widget_count.py            # Dashboard widget renderer
│   ├── actions/
│   │   └── archive_old.py             # BulkAction with task_runner="tasks"
│   └── routes.py                      # AdminRouteSpec for each widget's render endpoint
└── tests/
    ├── conftest.py
    ├── test_contributor_loads.py
    ├── test_resources_registered.py
    ├── test_page_renders.py
    ├── test_settings_panel_renders.py
    ├── test_widgets_render.py
    ├── test_bulk_action_dispatches.py
    └── test_namespacing.py
```

### Update existing docs

```
lexigram-admin/docs/
├── ARCHITECTURE.md                    # add cross-link to EXTENSION_DEVELOPER_GUIDE.md
├── RESOURCES.md                       # add "resources as a contributor" subsection
├── CONFIGURATION.md                   # fill in the empty stub (currently 541B)
├── HOWTOS.md                          # fill in the empty stub (193B)
├── QUICKSTART.md                      # fill in the empty stub (308B)
└── TROUBLESHOOTING.md                 # fill in the empty stub (277B) with contributor-discovery troubleshooting

lexigram-admin/
└── README.md                          # mention the contributor system and link to the guide
```

---

## Bite-Sized Steps

### Task F.1 — Scaffold the example package

**Files:**
- Create: `examples/lexigram-admin-plugin-demo/pyproject.toml`
- Create: `examples/lexigram-admin-plugin-demo/README.md`
- Create: `examples/lexigram-admin-plugin-demo/src/lexigram_admin_plugin_demo/__init__.py`

- [ ] **Step F.1.1: Write `pyproject.toml`** (10 min)

```toml
[project]
name = "lexigram-admin-plugin-demo"
version = "0.1.0"
description = "Demonstration of every contributor capability in lexigram-admin"
requires-python = ">=3.11"
dependencies = [
    "lexigram-admin>=0.2.0",
    "lexigram-contracts>=0.2.0",
]

[project.optional-dependencies]
cache = ["lexigram-cache"]
tasks = ["lexigram-tasks"]
search = ["lexigram-search"]

[project.entry-points."lexigram.admin.contributors"]
demo = "lexigram_admin_plugin_demo.contributor:DemoContributor"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

- [ ] **Step F.1.2: Write the README** (10 min) — orient the reader, list what the demo shows, point at the guide.

- [ ] **Step F.1.3: Install editable + verify discovery** (3 min)

```bash
cd examples/lexigram-admin-plugin-demo
uv pip install -e .
python -c "from importlib.metadata import entry_points; \
    print(list(entry_points(group='lexigram.admin.contributors')))"
```

Expected: the `demo` entry point appears.

- [ ] **Step F.1.4: Commit** (1 min)

---

### Task F.2 — `DemoContributor` skeleton

**Files:**
- Create: `examples/lexigram-admin-plugin-demo/src/lexigram_admin_plugin_demo/contributor.py`
- Test: `examples/lexigram-admin-plugin-demo/tests/test_contributor_loads.py`

- [ ] **Step F.2.1: Write failing test** (5 min)

```python
def test_contributor_class_is_subclass_of_base() -> None:
    from lexigram.contracts.admin import BaseAdminContributor
    from lexigram_admin_plugin_demo.contributor import DemoContributor
    assert issubclass(DemoContributor, BaseAdminContributor)

def test_contributor_required_metadata() -> None:
    from lexigram_admin_plugin_demo.contributor import DemoContributor
    c = DemoContributor()
    assert c.name == "demo"
    assert c.package_source == "lexigram_admin_plugin_demo"
    assert c.version == "0.1.0"
```

- [ ] **Step F.2.2: Implement skeleton** (15 min)

```python
from lexigram.contracts.admin import BaseAdminContributor

class DemoContributor(BaseAdminContributor):
    name = "demo"
    display_name = "Plugin Demo"
    group = "examples"
    icon = "puzzle"
    priority = 500
    version = "0.1.0"
    package_source = "lexigram_admin_plugin_demo"
    required_permissions = frozenset()

    def get_resources(self): ...
    def get_dashboard_widgets(self): ...
    def get_navigation_items(self): ...
    def get_management_pages(self): ...
    def get_settings_panels(self): ...
    def get_actions(self): ...
    def get_routes(self): ...
    def get_health_definitions(self): ...
```

- [ ] **Step F.2.3: Run + commit** (2 min)

---

### Task F.3 — Contribute resources (`WidgetResource`, `AuditLogResource`)

**Files:**
- Create: `examples/lexigram-admin-plugin-demo/src/lexigram_admin_plugin_demo/resources/widget.py`
- Create: `examples/lexigram-admin-plugin-demo/src/lexigram_admin_plugin_demo/resources/audit_log.py`
- Test: `examples/lexigram-admin-plugin-demo/tests/test_resources_registered.py`

- [ ] **Step F.3.1: Define `WidgetResource` with `cacheable=True`** (15 min)

```python
class WidgetResource(Resource):
    model = Widget
    name = "widgets"               # becomes "demo.widgets" after namespacing
    cluster = "examples"
    cacheable = True               # opts into Phase E.1 cache integration
    fields = [
        TextField(name="title", required=True, sortable=True),
        EnumField(name="status", enum=WidgetStatus),
        DateField(name="created_at", sortable=True),
    ]
```

- [ ] **Step F.3.2: Define `AuditLogResource` with `searchable=True`, read-only** (15 min)

```python
class AuditLogResource(Resource):
    model = AuditLog
    name = "audit_logs"
    cluster = "examples"
    searchable = True
    permissions = ResourcePermissions(
        can_list={"*"}, can_view={"*"},
        can_create=set(), can_edit=set(), can_delete=set(),
    )
    fields = [...]
```

- [ ] **Step F.3.3: Wire into `DemoContributor.get_resources()`** (3 min)

```python
def get_resources(self):
    from .resources.widget import WidgetResource
    from .resources.audit_log import AuditLogResource
    return [WidgetResource, AuditLogResource]
```

- [ ] **Step F.3.4: Write test** (10 min)

```python
@pytest.mark.asyncio
async def test_demo_resources_registered_with_namespace() -> None:
    # boot admin with DemoContributor
    # introspect resource registry
    # assert "demo.widgets" and "demo.audit_logs" are present
```

- [ ] **Step F.3.5: Run + commit** (2 min)

---

### Task F.4 — Contribute a management page

**Files:**
- Create: `examples/lexigram-admin-plugin-demo/src/lexigram_admin_plugin_demo/pages/overview.py`
- Test: `examples/lexigram-admin-plugin-demo/tests/test_page_renders.py`

- [ ] **Step F.4.1: Implement `DemoOverviewPage`** (20 min)

```python
class DemoOverviewPage:  # AdminPageHandlerProtocol-compatible
    async def handle(self, request) -> Response:
        # render a custom HTML page using lexigram.ui primitives
        ...
```

- [ ] **Step F.4.2: Wire into `DemoContributor.get_management_pages()`** (5 min)

```python
def get_management_pages(self):
    return [ManagementPageDefinition(
        name="overview",                          # becomes "demo.overview"
        title="Demo Overview",
        route_path="/admin/demo/overview",
        handler=DemoOverviewPage(),               # typed handler — not a string!
        category=PageCategory.OVERVIEW,
        required_permissions=frozenset(),
    )]
```

- [ ] **Step F.4.3: Write test** (15 min)

```python
@pytest.mark.asyncio
async def test_demo_overview_page_is_reachable() -> None:
    # GET /admin/demo/overview → 200 with expected fragment in body
    ...
```

- [ ] **Step F.4.4: Run + commit** (2 min)

---

### Task F.5 — Contribute a settings panel

**Files:**
- Create: `examples/lexigram-admin-plugin-demo/src/lexigram_admin_plugin_demo/settings/panel.py`
- Test: `examples/lexigram-admin-plugin-demo/tests/test_settings_panel_renders.py`

- [ ] **Step F.5.1: Implement `DemoSettingsPanel`** (15 min)
- [ ] **Step F.5.2: Wire into `DemoContributor.get_settings_panels()`** (5 min)
- [ ] **Step F.5.3: Write test** (15 min)
- [ ] **Step F.5.4: Run + commit** (2 min)

---

### Task F.6 — Contribute a dashboard widget + its route

**Files:**
- Create: `examples/lexigram-admin-plugin-demo/src/lexigram_admin_plugin_demo/widgets/widget_count.py`
- Create: `examples/lexigram-admin-plugin-demo/src/lexigram_admin_plugin_demo/routes.py`
- Test: `examples/lexigram-admin-plugin-demo/tests/test_widgets_render.py`

- [ ] **Step F.6.1: Implement the widget renderer** (15 min)
- [ ] **Step F.6.2: Implement the `AdminRouteSpec` list** (10 min)

```python
# routes.py
from lexigram.contracts.admin import AdminRouteSpec

def make_routes(contributor) -> list[AdminRouteSpec]:
    return [
        AdminRouteSpec(
            path="/admin/demo/widgets/widget_count",
            method="GET",
            handler=contributor.render_widget_count,
            name="widgets.widget_count",
            permissions=frozenset(),
        ),
    ]
```

- [ ] **Step F.6.3: Wire into `DemoContributor.get_dashboard_widgets()` and `get_routes()`** (5 min)
- [ ] **Step F.6.4: Write test** (15 min)
- [ ] **Step F.6.5: Run + commit** (2 min)

---

### Task F.7 — Contribute a bulk action with `task_runner`

**Files:**
- Create: `examples/lexigram-admin-plugin-demo/src/lexigram_admin_plugin_demo/actions/archive_old.py`
- Test: `examples/lexigram-admin-plugin-demo/tests/test_bulk_action_dispatches.py`

- [ ] **Step F.7.1: Implement `ArchiveOldWidgetsAction`** (15 min)

```python
class ArchiveOldWidgetsAction(BulkAction):
    name = "archive_old"
    label = "Archive selected"
    task_runner = "tasks"  # opts into Phase E.2 task integration
    async def execute(self, records, ctx):
        ...
```

- [ ] **Step F.7.2: Test in both states (tasks installed vs not)** (15 min)
- [ ] **Step F.7.3: Run + commit** (2 min)

---

### Task F.8 — Namespacing assertion test

**Files:**
- Test: `examples/lexigram-admin-plugin-demo/tests/test_namespacing.py`

- [ ] **Step F.8.1: Write tests asserting every contributed name is prefixed with `demo.`** (10 min)

```python
@pytest.mark.asyncio
async def test_all_contributions_are_namespaced() -> None:
    # boot admin with DemoContributor
    # for each of widgets/nav/pages/settings/routes:
    #   assert every item's name begins with "demo."
```

- [ ] **Step F.8.2: Run + commit** (2 min)

---

### Task F.9 — Write the Extension Developer Guide

**Files:**
- Create: `lexigram-admin/docs/EXTENSION_DEVELOPER_GUIDE.md`

Outline (each section is one Step):

- [ ] **Step F.9.1: "Who this is for"** (10 min) — third-party package authors who want to ship admin functionality.
- [ ] **Step F.9.2: "Create the package skeleton"** (15 min) — minimal `pyproject.toml`, entry-points block, package layout. Use the demo as the reference.
- [ ] **Step F.9.3: "Your first contributor"** (15 min) — the minimal `BaseAdminContributor` subclass; required metadata fields and what each does.
- [ ] **Step F.9.4: "Contribute a resource"** (20 min) — walk through `WidgetResource` from the demo; explain `cacheable`, `searchable`, `cluster`, `permissions`. Mention the namespacing convention.
- [ ] **Step F.9.5: "Contribute a page"** (15 min) — `ManagementPageDefinition`, typed `AdminPageHandlerProtocol` vs legacy string handler.
- [ ] **Step F.9.6: "Contribute a settings panel"** (10 min) — same pattern as pages.
- [ ] **Step F.9.7: "Contribute a widget + its route"** (15 min) — widgets are decoupled from their render endpoints; use `get_routes()` so admin auto-registers them.
- [ ] **Step F.9.8: "Contribute an action"** (10 min) — row, bulk, header; `task_runner` for background execution.
- [ ] **Step F.9.9: "Permissions and RBAC"** (15 min) — `required_permissions` on contributor metadata; per-resource `permissions`; per-action authorization.
- [ ] **Step F.9.10: "Optional framework integrations"** (10 min) — opt into cache, tasks, search, resilience, storage via declarative knobs.
- [ ] **Step F.9.11: "Naming and collisions"** (10 min) — explain the namespacing prefix, the `contributor_collision_mode` config, when to use `warn` vs `error`.
- [ ] **Step F.9.12: "Test your contributor"** (10 min) — fixtures for booting admin with just your contributor; how to assert registration; how to test rendering.
- [ ] **Step F.9.13: "Publish to PyPI"** (5 min) — version your contributor, document your `required_permissions`, link to the demo.
- [ ] **Step F.9.14: "Troubleshooting"** (10 min) — common errors: contributor not discovered, name collision, missing optional integration.
- [ ] **Step F.9.15: Commit** (1 min)

---

### Task F.10 — Write the Contributor Reference

**Files:**
- Create: `lexigram-admin/docs/CONTRIBUTOR_REFERENCE.md`

Goal: exhaustive reference, not a tutorial. One section per method on `BaseAdminContributor`, with signature, return type, default behavior, collision policy, permission semantics, and a short example.

- [ ] **Step F.10.1: Section for each of: `get_dashboard_widgets`, `get_navigation_items`, `get_health_definitions`, `get_management_pages`, `get_settings_panels`, `get_actions`, `get_routes`, `get_resources`, `on_admin_boot`, `on_admin_shutdown`, `render_widget`, `render_health_check`, `execute_action`** (15 min × ~13 sections)
- [ ] **Step F.10.2: Add a "Definition types reference" appendix listing every contributed dataclass shape** (15 min)
- [ ] **Step F.10.3: Commit** (1 min)

---

### Task F.11 — Write the Framework Composition Map

**Files:**
- Create: `lexigram-admin/docs/FRAMEWORK_COMPOSITION.md`

- [ ] **Step F.11.1: Reproduce the three-ring diagram from `REVIEW2.md` §5** (10 min)
- [ ] **Step F.11.2: Write the "Required dependencies" section** (10 min) — what admin always needs.
- [ ] **Step F.11.3: Write the "Optional integrations" section** (10 min) — table from `REVIEW2.md` §5 with what each optional package gives you, when to install it, what the declarative knob is.
- [ ] **Step F.11.4: Write the "What admin does NOT do for you" section** (10 min) — identity is `lexigram-auth`, tenancy is `lexigram-tenancy`, metrics are `lexigram-monitor`.
- [ ] **Step F.11.5: Commit** (1 min)

---

### Task F.12 — Write `MIGRATION_TO_DELEGATED_AUTH.md`

**Files:**
- Create: `lexigram-admin/docs/MIGRATION_TO_DELEGATED_AUTH.md`

This doc is the bridge for any app that overrode `AdminAuthGuard`, `AdminSessionManager`, `AdminJWTBackend`, or `AdminOAuthIntegration` before Phase D.1 landed.

- [ ] **Step F.12.1: "What changed"** (10 min) — link to Phase D.1 plan.
- [ ] **Step F.12.2: "How to migrate"** (15 min) — concrete diff examples.
- [ ] **Step F.12.3: "What stays the same"** (5 min) — `admin/rbac/` is unchanged; field/action/record permissions still admin-owned.
- [ ] **Step F.12.4: Commit** (1 min)

---

### Task F.13 — Fill in the stub docs

**Files:**
- Modify: `lexigram-admin/docs/GUIDE.md`
- Modify: `lexigram-admin/docs/QUICKSTART.md`
- Modify: `lexigram-admin/docs/HOWTOS.md`
- Modify: `lexigram-admin/docs/CONFIGURATION.md`
- Modify: `lexigram-admin/docs/TROUBLESHOOTING.md`

- [ ] **Step F.13.1: `GUIDE.md` becomes a landing page that links to ARCHITECTURE, RESOURCES, EXTENSION_DEVELOPER_GUIDE, CONTRIBUTOR_REFERENCE, FRAMEWORK_COMPOSITION** (10 min)
- [ ] **Step F.13.2: `QUICKSTART.md` — minimal 5-minute "boot admin with one resource" recipe** (20 min)
- [ ] **Step F.13.3: `HOWTOS.md` — collection of short recipes** (30 min)
- [ ] **Step F.13.4: `CONFIGURATION.md` — full `AdminConfig` reference including `contributor_collision_mode`** (20 min)
- [ ] **Step F.13.5: `TROUBLESHOOTING.md` — common errors and resolutions, especially contributor discovery** (15 min)
- [ ] **Step F.13.6: Commit** (1 min)

---

### Task F.14 — Update the top-level README

**Files:**
- Modify: `lexigram-admin/README.md`

- [ ] **Step F.14.1: Add "Contributor System" section with one-paragraph pitch and link to EXTENSION_DEVELOPER_GUIDE.md** (10 min)
- [ ] **Step F.14.2: Add the demo plugin to the "Examples" list** (3 min)
- [ ] **Step F.14.3: Commit** (1 min)

---

### Task F.15 — Cross-link existing docs

**Files:**
- Modify: `lexigram-admin/docs/ARCHITECTURE.md` (Contribution System section)
- Modify: `lexigram-admin/docs/RESOURCES.md`

- [ ] **Step F.15.1: ARCHITECTURE.md — add "For plugin authors, see [Extension Developer Guide]" callout in the Contribution section** (5 min)
- [ ] **Step F.15.2: RESOURCES.md — add a "Resources from plugins" subsection that shows how to declare a `Resource` inside a contributor** (15 min)
- [ ] **Step F.15.3: Commit** (1 min)

---

## Validation Gate

- [ ] All demo tests pass:
  ```bash
  cd /home/admin/Documents/AI/applications/framework/lexigram/examples/lexigram-admin-plugin-demo
  uv run pytest -v
  ```
- [ ] Demo discovered when installed editable:
  ```bash
  uv pip install -e examples/lexigram-admin-plugin-demo
  python -c "from importlib.metadata import entry_points; \
    assert any(e.name == 'demo' for e in entry_points(group='lexigram.admin.contributors'))"
  ```
- [ ] Boot a dev admin with the demo installed and visit:
  - `/admin/demo/widgets` → list page renders
  - `/admin/demo/audit_logs` → list page renders (read-only)
  - `/admin/demo/overview` → custom page renders
  - `/admin/demo/widgets/widget_count` → widget endpoint serves HTML fragment
  - Dashboard → demo widget appears
  - Sidebar → demo nav group appears
- [ ] All new docs render without dead links:
  ```bash
  # if mkdocs is in use, build it
  uv run mkdocs build --strict
  # otherwise lint markdown
  uv run markdownlint lexigram-admin/docs/*.md
  ```
- [ ] The Extension Developer Guide reads end-to-end without referring to source code — a reader who only reads the guide should be able to write a working contributor.
- [ ] Coverage on the demo package ≥ 80%.

## What Phase F Does NOT Do

- Does not introduce any new contributor capability. It only exercises and documents what Phases A–E built.
- Does not move the demo into `lexigram-admin/examples/`. It lives at the workspace `examples/` root next to `examples/platform/`.
- Does not publish the demo to PyPI. It remains an internal reference.

## Cross-Package Coordination Notes

| Coordination point | Action |
|---|---|
| `examples/platform/` (existing demo) | Add a note in its README that the new `examples/lexigram-admin-plugin-demo/` is the canonical multi-capability example. Keep `platform/` as the simpler one-capability example. |
| `lexigram-cache`, `lexigram-tasks`, `lexigram-search` | None — demo consumes them via optional extras |
| `lexigram-contracts` | None — only consumes `BaseAdminContributor`, `AdminRouteSpec`, `AdminPageHandlerProtocol` |

## Dependencies and Sequencing

- **Phase A** must land first so the demo can import from `lexigram.contracts.admin` cleanly.
- **Phase B** must land first so `get_management_pages()`, `get_settings_panels()`, and `get_routes()` actually work.
- **Phase C** must land first so `get_resources()` actually registers resources.
- **Phase E.1 / E.2 / E.3** should land first so `cacheable=True`, `task_runner="tasks"`, `searchable=True` in the demo are not dead code.
- **Phase D** does not block Phase F, but the migration doc (F.12) only needs to exist after D.1 is merged.

## Long-Term Maintenance

The demo package becomes the **regression fixture** for the entire contributor system. Whenever a new contributor capability lands, the demo gains a small example of it and the Extension Developer Guide grows a section. CI should run the demo's tests on every PR that touches `lexigram-admin`, `lexigram-contracts/admin/`, or any of the optional integration packages.
