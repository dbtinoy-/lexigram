# lexigram-admin Foundation Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Get `lexigram-admin` to a trustworthy baseline by closing every Critical and High finding from REVIEW.md. Stop deep-path imports into `lexigram-ui`, document the Result/Exception doctrine, fail fast on resource resolution, and audit each stub-heavy subsystem to a binary ship-or-delete decision. **No new abstractions** in this plan — that's deferred to a follow-up Filament-evolution plan once the foundation is solid.

**Architecture:** Two phases, each independently revertible. Phase 1 is "stop the bleeding": fix the phantom imports, the deep-path import sprawl, the dependency drift, the silent resource-resolution failures, and codify the Result vs. Exception rule. Phase 2 is "prune the halo": audit the seven subsystems flagged as stub-heavy or contested (`models/`, `layout/`, `relations/`, `monitoring/`, `realtime/`, `validation/`, `views/`, `middleware/`, `cli/`) — read each in full, decide ship-or-delete with documented rationale, then act.

**Tech Stack:** Python 3.11+, htpy ≥0.9, HTMX 2.x, Alpine.js, pytest, ruff, mypy, uv for package management.

**Spec:** `lexigram-admin/REVIEW.md` (Phases 1–2 in §9 First Refactor Steps).

**Working directory:** `/home/admin/Documents/AI/applications/framework/lexigram/lexigram-admin` (run all commands from here unless noted).

**CI command (run after every phase):**
```bash
cd /home/admin/Documents/AI/applications/framework/lexigram && \
  uv run ruff check lexigram-admin --fix && \
  uv run ruff format lexigram-admin && \
  uv run mypy lexigram-admin/src/ && \
  uv run pytest lexigram-admin/ --tb=short
```

---

## Hard Prerequisite: Coordinate with lexigram-ui Phase 1

**This plan assumes `lexigram-ui` Phase 1 (Public API Hardening) is merged before starting.** That phase adds `SubmitButton`, `MarkdownEditor`, `RichEditor`, every input class, every molecule, every organism, `DebounceConfig`, every performance helper, observability symbols to `lexigram.ui`'s `_LAZY_IMPORTS`. Without it, **Task 1.2 below cannot complete** — admin would still need deep-path imports because the symbols are not on ui's public surface.

If ui's plan has not been started, pause this plan and start with `lexigram-ui/docs/plans/2026-05-25-foundation-hardening.md` Phase 1 first.

---

## File Structure Map

Files this plan creates, modifies, or deletes.

### Create
- `tests/integration/test_phantom_imports.py` — guard against deep-path imports into `lexigram.ui` internals
- `tests/integration/test_admin_provider_fail_fast.py` — verify resource-resolution failures surface in non-permissive mode
- `docs/CONVENTIONS.md` — Result-vs-Exception rule, logging, async, frozen dataclass policy
- `docs/HALO_AUDIT.md` — record of ship-or-delete decisions for each contested subsystem

### Modify
- `pyproject.toml:42` — `htpy>=0.2.0` → `htpy>=0.9` (match ui constraint)
- `src/lexigram/admin/ui/__init__.py` — rewrite import block to use `from lexigram.ui import X` exclusively (no deep paths)
- `src/lexigram/admin/di/bundle_provider.py:168-194` — add a `strict` mode that re-raises instead of swallowing
- `src/lexigram/admin/config.py` — add `AdminConfig.strict_resource_resolution: bool` field (default `True` in production, `False` in dev)
- `src/lexigram/admin/models/__init__.py` — depending on Phase 2 decision (see Task 2.1)

### Conditionally delete / move (Phase 2 outcomes; each gated on per-subsystem audit)
- `src/lexigram/admin/cli/` — move out of runtime package if no runtime importer exists
- Stub portions of `src/lexigram/admin/monitoring/`, `src/lexigram/admin/realtime/`, `src/lexigram/admin/validation/`, `src/lexigram/admin/views/`, `src/lexigram/admin/middleware/` — per audit decisions

### Will NOT modify in this plan (despite REVIEW recommendations)
- `src/lexigram/admin/models/` — contains real `Command`, `AdminProviderState`, `SystemSetting` dataclasses + `AdminUser` re-export. **The REVIEW.md "delete this" recommendation was based on incomplete information.** Audit in Phase 2 will document this and keep it.
- `src/lexigram/admin/layout/` — contains real `LayoutType` enum (LIST, GRID, CALENDAR, KANBAN, TIMELINE, MAP, TREE, CUSTOM) and `LayoutConfig` dataclass. Substantive. Keep.
- `src/lexigram/admin/relations/` — contains substantive `AbstractRelationManager` ABC with `table()`, `get_query()`, `count()`, `get_items()`. **This is already the RelationManager scaffolding** the REVIEW recommended building under Phase 5; keep it and grow from here in the follow-up Filament plan.

---

## Phase 1 — Stop the Bleeding

Five tasks. Each closes a Critical or High finding without introducing new abstractions.

### Task 1.1: Pin htpy consistently with lexigram-ui

**Files:**
- Modify: `pyproject.toml:42`

`lexigram-ui` requires `htpy>=0.9`. Admin currently allows `htpy>=0.2.0`, which means an `uv pip install` of admin could resolve a pre-0.9 htpy that ui rejects at runtime.

- [ ] **Step 1: Update the constraint**

In `pyproject.toml`, change line 42:
```toml
    "htpy>=0.2.0",
```
to:
```toml
    "htpy>=0.9",
```

- [ ] **Step 2: Re-resolve the lock and run tests**

```bash
cd /home/admin/Documents/AI/applications/framework/lexigram && \
  uv sync && \
  uv run pytest lexigram-admin/ --tb=short
```

Expected: all tests pass with the tightened constraint.

- [ ] **Step 3: Commit**

```bash
git add lexigram-admin/pyproject.toml
git commit -m "fix(lexigram-admin): pin htpy>=0.9 to match lexigram-ui

Admin's looser >=0.2.0 constraint could resolve a pre-0.9 htpy that
ui rejects at runtime. Match ui's constraint.

Closes REVIEW High #8."
```

### Task 1.2: Rewrite `admin/ui/__init__.py` to import only from `lexigram.ui`

**Files:**
- Modify: `src/lexigram/admin/ui/__init__.py`

**Prerequisite:** `lexigram-ui` Phase 1 merged. Verify by running:
```bash
uv run python -c "from lexigram.ui import SubmitButton, MarkdownEditor, RichEditor, DebounceConfig, TextInput, Select, Form, Repeater, SlideOver; print('OK')"
```
This must print `OK`. If it fails, ui's Phase 1 is incomplete — stop and finish that first.

- [ ] **Step 1: Replace the file's imports wholesale**

Open `src/lexigram/admin/ui/__init__.py`. The current top of the file (lines 38–147) deep-imports from `lexigram.ui.atoms.*`, `lexigram.ui.molecules.*`, `lexigram.ui.organisms.*`, `lexigram.ui.config`, `lexigram.ui.monitoring.*`. Replace those import statements with a single block that imports through the public API.

Rewrite the imports section (everything from the first `from lexigram.ui.accessibility import` through the last `from lexigram.ui.organisms.slide_over import SlideOver`) with this block:

```python
# Public-API imports — never reach into lexigram.ui internals.
# If a symbol is missing from `lexigram.ui`, fix `lexigram-ui/src/lexigram/ui/__init__.py`
# rather than deep-path-importing here.
from lexigram.ui import (
    # Accessibility
    AriaAttrs, AriaLive, AriaRole, SkipLink,
    announce, announce_table_update, button_aria, dialog_aria, header_aria,
    keyboard_navigation_script, row_aria, search_aria, table_aria,
    # Atoms — primitives
    Badge, Button, SubmitButton,
    Divider, Fieldset, FileUpload, Icon, Label, Link,
    MarkdownEditor, RichEditor,
    ProgressBar, Skeleton, Spinner, Switch, Tooltip,
    # Atoms — layout
    Aside, Col, Container, Grid, Row, Stack,
    # Atoms — inputs
    BelongsTo, Checkbox, CheckboxList, ColorPicker, DateInput, Hidden,
    MultiSelect, NumberInput, PasswordInput, Radio, Rating,
    Select, Slider, TagsInput, TextArea, TextInput, TimePicker, Toggle,
    # Config
    DebounceConfig,
    # Core
    Component, el, render_to_string,
    # Errors
    ErrorCategory, ErrorResponse, FieldError,
    htmx_error_response, not_found_error, permission_error,
    server_error, timeout_error, validation_error,
    # Molecules
    Alert, Breadcrumbs, Card, Dropdown, EmptyState, ErrorState,
    FormActions, InputGroup, LoadingOverlay, MetricCard, Modal,
    Popover, RichSelect, Section, SimpleAlert, StatCard, TabPanel, Tabs, Toast,
    # Organisms
    ActivityFeed, Chart, Form, Repeater, SlideOver,
    # Observability
    MetricProtocol, MetricsCollector, MetricType,
    # Performance
    RenderCache, ResponseOptimizer,
    add_htmx_timing_header, debounced_search_attrs,
    infinite_scroll_trigger, lazy_load_placeholder, measure_render_time,
    # Zones
    SwapMode, Zone, Zones,
)

# Admin-specific UI components stay imported from inside admin
from lexigram.admin.ui.htmx_attrs import HTMXAttrs, HTMXAttrsBuilder
from lexigram.admin.ui.molecules.date_range_filter import DateRangeFilter
from lexigram.admin.ui.molecules.filter_bar import FilterBar
from lexigram.admin.ui.molecules.filter_dropdown import FilterDropdown
from lexigram.admin.ui.molecules.jump_to_page import JumpToPage
from lexigram.admin.ui.molecules.page_size_selector import PageSizeSelector
from lexigram.admin.ui.molecules.pagination_links import PaginationLinks
from lexigram.admin.ui.observability import (
    get_health_status, log_htmx_request, log_htmx_response, observe_htmx,
    render_debug_panel, track_error, track_htmx_request, track_render_time,
)
from lexigram.admin.ui.organisms.command_palette import CommandPalette
from lexigram.admin.ui.organisms.data_table import DataTable
from lexigram.admin.ui.organisms.dynamic_form import DynamicForm
from lexigram.admin.ui.organisms.pagination import Pagination
from lexigram.admin.ui.organisms.sidebar import Sidebar, SidebarItem, SidebarSection
from lexigram.admin.ui.organisms.task_progress import TaskProgress
from lexigram.admin.ui.organisms.topbar import ThemeToggle, TopBar
from lexigram.admin.ui.organisms.userbox import UserBox
from lexigram.admin.ui.state import TableState
from lexigram.admin.ui.templates.shell import AdminShell
```

Keep the existing `__all__` list at the bottom of the file unchanged — it already names every symbol; only the import lines change.

- [ ] **Step 2: Verify every name in `__all__` resolves**

Run this one-liner to catch missing imports faster than the full test suite would:
```bash
uv run python -c "import lexigram.admin.ui as m; missing = [s for s in m.__all__ if not hasattr(m, s)]; print('MISSING:', missing) if missing else print('OK', len(m.__all__), 'symbols')"
```

Expected: `OK <N> symbols`. If any name shows under `MISSING:`, either the imports block omitted it (add to the public-API import block in Step 1) or it's no longer needed (remove from `__all__`).

- [ ] **Step 3: Run the full test suite**

```bash
cd /home/admin/Documents/AI/applications/framework/lexigram && \
  uv run pytest lexigram-admin/ --tb=short
```

Expected: all pass. If any test fails with `ImportError` or `AttributeError`, that symbol is missing from `lexigram.ui` — add it to ui's `_LAZY_IMPORTS` (see ui plan Task 1.2) before continuing.

- [ ] **Step 4: Commit**

```bash
git add lexigram-admin/src/lexigram/admin/ui/__init__.py
git commit -m "refactor(lexigram-admin): import UI symbols through lexigram.ui public API only

Replaces 47+ deep-path imports (e.g., from lexigram.ui.atoms.button import Button)
with a single from lexigram.ui import (...) block. Phantom imports
(SubmitButton, MarkdownEditor, RichEditor) now resolve through the
public API.

Closes REVIEW Critical #2 and #3."
```

### Task 1.3: Add a phantom-import guard test

**Files:**
- Create: `tests/integration/test_phantom_imports.py`

This test enforces — at CI time — that admin source files never deep-path-import from `lexigram.ui.atoms.*`, `lexigram.ui.molecules.*`, `lexigram.ui.organisms.*`, `lexigram.ui.layouts.*`, `lexigram.ui.config`, `lexigram.ui.htmx.*`, `lexigram.ui.monitoring.*`, `lexigram.ui.performance.*` (where the public API has equivalents).

- [ ] **Step 1: Write the test**

```python
# tests/integration/test_phantom_imports.py
"""Phantom-import guard.

Admin source files must import UI symbols through `from lexigram.ui import X`
only — never `from lexigram.ui.atoms.button import Button` or similar deep
paths. This test scans every .py file under src/ and rejects forbidden patterns.
"""
from __future__ import annotations

import re
from pathlib import Path

# Patterns that signal a deep-path import bypassing the public API.
# Every symbol these submodules expose has a public-API equivalent in `lexigram.ui`.
FORBIDDEN_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^from lexigram\.ui\.atoms[\.\s]", re.MULTILINE),
    re.compile(r"^from lexigram\.ui\.molecules[\.\s]", re.MULTILINE),
    re.compile(r"^from lexigram\.ui\.organisms[\.\s]", re.MULTILINE),
    re.compile(r"^from lexigram\.ui\.layouts[\.\s]", re.MULTILINE),
    re.compile(r"^from lexigram\.ui\.htmx[\.\s]", re.MULTILINE),
    re.compile(r"^from lexigram\.ui\.monitoring[\.\s]", re.MULTILINE),
    re.compile(r"^from lexigram\.ui\.performance[\.\s]", re.MULTILINE),
    re.compile(r"^from lexigram\.ui\.config\s+import", re.MULTILINE),
    re.compile(r"^from lexigram\.ui\.core[\.\s]", re.MULTILINE),
    re.compile(r"^from lexigram\.ui\.exceptions\s+import", re.MULTILINE),
    re.compile(r"^from lexigram\.ui\.accessibility[\.\s]", re.MULTILINE),
]

# Explicit exceptions where deep imports are intentional and documented.
# Keep this list small and justified — each entry should have a one-line
# comment explaining why the deep import is irreplaceable.
ALLOWLIST: set[str] = {
    # Add paths relative to admin's src/ root, e.g.:
    # "lexigram/admin/some_module.py",  # reason: needs internal type only exposed via deep path
}


def _python_files(root: Path) -> list[Path]:
    return [p for p in root.rglob("*.py") if "__pycache__" not in p.parts]


def test_no_deep_path_ui_imports_in_admin_source() -> None:
    admin_src = Path(__file__).resolve().parents[2] / "src"
    assert admin_src.exists(), f"Expected src/ at {admin_src}"

    offenders: list[tuple[Path, str]] = []
    for path in _python_files(admin_src):
        if str(path.relative_to(admin_src)) in ALLOWLIST:
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_PATTERNS:
            for match in pattern.finditer(text):
                offenders.append((path.relative_to(admin_src), match.group(0).strip()))

    if offenders:
        lines = [f"  {p}: {imp}" for p, imp in offenders]
        msg = (
            "Deep-path imports into lexigram.ui internals are forbidden.\n"
            "Use `from lexigram.ui import X` instead. If a symbol is missing\n"
            "from `lexigram.ui`, add it to lexigram-ui's `_LAZY_IMPORTS`.\n"
            "\nOffending imports:\n" + "\n".join(lines)
        )
        raise AssertionError(msg)


def test_no_phantom_symbols_in_admin_tests() -> None:
    admin_tests = Path(__file__).resolve().parents[1]
    offenders: list[tuple[Path, str]] = []
    for path in _python_files(admin_tests):
        text = path.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_PATTERNS:
            for match in pattern.finditer(text):
                offenders.append((path.relative_to(admin_tests), match.group(0).strip()))

    if offenders:
        lines = [f"  {p}: {imp}" for p, imp in offenders]
        # Tests are a soft warning — assert if any appear so they're surfaced,
        # but allow `render_to_string` integration tests if explicitly allowlisted.
        msg = (
            "Test files contain deep-path imports into lexigram.ui internals.\n"
            "Use `from lexigram.ui import X` unless you're specifically testing\n"
            "the internal module path.\n"
            "\nOffending imports:\n" + "\n".join(lines)
        )
        raise AssertionError(msg)
```

- [ ] **Step 2: Pre-populate ALLOWLIST with any legitimate existing deep imports**

Before running the test, enumerate the test files that currently use deep paths into `lexigram.ui` internals:
```bash
grep -rEln "^from lexigram\.ui\.(atoms|molecules|organisms|layouts|htmx|monitoring|performance|config|core|exceptions|accessibility)" lexigram-admin/tests/ 2>/dev/null
```

For each match, decide:
- **Update to public API** — preferred, e.g., `from lexigram.ui import render_to_string` instead of `from lexigram.ui.core.base import render_to_string`.
- **Add to ALLOWLIST** — only if the test explicitly verifies the internal module path itself (e.g., a test that imports `lexigram.ui.core.base` to assert that `render_to_string` lives at that exact path).

Apply the chosen action to each file. Then proceed to Step 3.

- [ ] **Step 3: Run the test**

```bash
uv run pytest tests/integration/test_phantom_imports.py -v
```

Expected: both `test_no_deep_path_ui_imports_in_admin_source` and `test_no_phantom_symbols_in_admin_tests` pass. If they still fail, return to Step 2 and either fix the remaining files or expand ALLOWLIST with a documented reason per entry.

- [ ] **Step 4: Commit**

```bash
git add lexigram-admin/tests/integration/test_phantom_imports.py
git commit -m "test(lexigram-admin): guard against deep-path imports into lexigram.ui

CI-time check that no admin source file reaches into lexigram.ui.atoms,
lexigram.ui.molecules, lexigram.ui.organisms, etc. All UI symbols must
flow through the public API.

Closes REVIEW Critical #2, #3 (enforcement)."
```

### Task 1.4: Fail fast on resource-resolution errors

**Files:**
- Modify: `src/lexigram/admin/config.py`
- Modify: `src/lexigram/admin/di/bundle_provider.py` (around lines 168–194)
- Create: `tests/integration/test_admin_provider_fail_fast.py`

Today `bundle_provider.py:168-194` silently swallows resource resolution failures (logs and continues). This hides misconfiguration. Replace with a `strict_resource_resolution` flag in `AdminConfig` that defaults `True` in production, `False` in dev.

- [ ] **Step 1: Write the failing test**

```python
# tests/integration/test_admin_provider_fail_fast.py
"""Verify resource-resolution failures fail fast in strict mode."""
from __future__ import annotations

import pytest


class _BrokenResource:
    """Resource class that will raise on resolution."""
    name = "broken"

    def __init__(self) -> None:
        raise RuntimeError("intentional breakage for test")


@pytest.mark.asyncio
async def test_strict_mode_raises_on_resource_resolution_failure():
    """When strict_resource_resolution=True, a failure must propagate."""
    from lexigram.admin.config import AdminConfig
    from lexigram.admin.di.bundle_provider import AdminBundleProvider
    from lexigram.container import Container

    config = AdminConfig(strict_resource_resolution=True)
    provider = AdminBundleProvider(
        config=config,
        resources=[_BrokenResource],
    )
    container = Container()
    await provider.register(container)
    with pytest.raises(RuntimeError, match="intentional breakage"):
        await provider.boot(container)


@pytest.mark.asyncio
async def test_permissive_mode_swallows_resource_resolution_failure():
    """When strict_resource_resolution=False, a failure must be logged but not raised."""
    from lexigram.admin.config import AdminConfig
    from lexigram.admin.di.bundle_provider import AdminBundleProvider
    from lexigram.container import Container

    config = AdminConfig(strict_resource_resolution=False)
    provider = AdminBundleProvider(
        config=config,
        resources=[_BrokenResource],
    )
    container = Container()
    await provider.register(container)
    # Should not raise
    await provider.boot(container)
```

Run:
```bash
uv run pytest tests/integration/test_admin_provider_fail_fast.py -v
```

Expected: both tests fail — the config field doesn't exist yet, and the bundle provider still swallows.

- [ ] **Step 2: Precheck — read AdminConfig's structure**

Before editing, read the surrounding context to determine whether `AdminConfig` is a frozen dataclass, a pydantic `BaseModel`, or a custom typed config:
```bash
grep -n "class AdminConfig" src/lexigram/admin/config.py
```
Then read 30 lines starting from that line, plus any base-class definitions imported at the top of the file.

The new `strict_resource_resolution` field must follow the existing pattern exactly — same decorator (`@dataclass`, `BaseModel` subclass, etc.), same field-declaration style (`field(default=...)`, `Field(default=...)`, plain `= True`), same metadata convention (the `metadata=` dict for dataclass fields, `Field(description=...)` for pydantic).

- [ ] **Step 3: Add `strict_resource_resolution` to `AdminConfig`**

In `src/lexigram/admin/config.py`, locate the `AdminConfig` class (around line 284–373). Add a field — adapt the syntax to match what you discovered in Step 2:

```python
    # Example A — if AdminConfig is a dataclass:
    strict_resource_resolution: bool = field(
        default=True,
        metadata={
            "env": "LEX_ADMIN__STRICT_RESOURCE_RESOLUTION",
            "description": (
                "When True (production default), resource/controller resolution "
                "failures during AdminBundleProvider.boot() raise immediately. "
                "When False, failures are logged and resolution continues with "
                "the remaining resources/controllers. Set to False in dev only."
            ),
        },
    )

    # Example B — if AdminConfig is a pydantic BaseModel:
    strict_resource_resolution: bool = Field(
        default=True,
        description=(
            "When True (production default), resource/controller resolution "
            "failures during AdminBundleProvider.boot() raise immediately. "
            "When False, failures are logged and resolution continues with "
            "the remaining resources/controllers. Set to False in dev only."
        ),
        json_schema_extra={"env": "LEX_ADMIN__STRICT_RESOURCE_RESOLUTION"},
    )
```

Pick the variant that matches Step 2's findings.

In `AdminConfig.validate_for_environment()` (around `config.py:202-222`), add a check that warns if `strict_resource_resolution=False` in production.

- [ ] **Step 4: Update three blocks in `bundle_provider.py` to honor strict mode**

`bundle_provider.py` has three best-effort resolution blocks that all swallow failures the same way. **All three must be updated identically.** They are at approximately:
- Lines 168–178: the resource resolution loop
- Lines 180–194: the controller resolution loop
- Lines 197+: the built-in `WidgetController` resolution

Read the file first to confirm exact line numbers (they may have shifted slightly). Look for each `except Exception as exc:  # noqa: BLE001 — best-effort` comment.

**For the resource block (block 1):**
```python
# BEFORE:
            try:
                resources_dict[name] = await admin_resolver.resolve(
                    resource_cls,
                    bypass_visibility=True,
                )
            except Exception as exc:  # noqa: BLE001 — best-effort; continue with other resources
                _log.warning(
                    "admin.resource_resolution_failed",
                    resource=resource_cls.__name__,
                    error=str(exc),
                )

# AFTER:
            try:
                resources_dict[name] = await admin_resolver.resolve(
                    resource_cls,
                    bypass_visibility=True,
                )
            except Exception as exc:
                _log.error(
                    "admin.resource_resolution_failed",
                    resource=resource_cls.__name__,
                    error=str(exc),
                    strict=self._config.strict_resource_resolution,
                )
                if self._config.strict_resource_resolution:
                    raise
```

**For the controller block (block 2):**
```python
# BEFORE:
            try:
                instance = await admin_resolver.resolve(
                    controller_cls,
                    bypass_visibility=True,
                )
                controller_instances.append(instance)
            except Exception as exc:  # noqa: BLE001 — best-effort; continue with other controllers
                _log.warning(
                    "admin.controller_resolution_failed",
                    controller=controller_cls.__name__,
                    error=str(exc),
                )

# AFTER:
            try:
                instance = await admin_resolver.resolve(
                    controller_cls,
                    bypass_visibility=True,
                )
                controller_instances.append(instance)
            except Exception as exc:
                _log.error(
                    "admin.controller_resolution_failed",
                    controller=controller_cls.__name__,
                    error=str(exc),
                    strict=self._config.strict_resource_resolution,
                )
                if self._config.strict_resource_resolution:
                    raise
```

**For the WidgetController block (block 3):** read the current code around line 197+ (the exact structure may differ). The pattern is the same — change `warning(...)` to `error(...)` with `strict=`, and add `if self._config.strict_resource_resolution: raise` inside the except.

Pass the config into `AdminBundleProvider.__init__` if it isn't already (read `bundle_provider.py:25-50` to confirm — it likely already accepts `config`).

- [ ] **Step 5: Run the tests**

```bash
uv run pytest tests/integration/test_admin_provider_fail_fast.py -v
```

Expected: both pass.

- [ ] **Step 6: Run the full CI**

```bash
cd /home/admin/Documents/AI/applications/framework/lexigram && \
  uv run ruff check lexigram-admin --fix && \
  uv run mypy lexigram-admin/src/ && \
  uv run pytest lexigram-admin/ --tb=short
```

Expected: clean. The existing test suite may need updates if any test depended on silent failure — surface those and fix them in this commit.

- [ ] **Step 7: Commit**

```bash
git add lexigram-admin/src/lexigram/admin/config.py \
        lexigram-admin/src/lexigram/admin/di/bundle_provider.py \
        lexigram-admin/tests/integration/test_admin_provider_fail_fast.py
git commit -m "feat(lexigram-admin): fail fast on resource resolution in strict mode

AdminConfig.strict_resource_resolution (default True) controls whether
AdminBundleProvider raises immediately when a resource or controller
fails to resolve, vs. logging and continuing. Production environments
fail fast; dev can opt into permissive mode.

Closes REVIEW High #7."
```

### Task 1.5: Document the Result/Exception doctrine

**Files:**
- Create: `docs/CONVENTIONS.md`

Admin uses a hybrid pattern: domain failures raise typed exceptions (`NotFoundError`, `PermissionDeniedError`, `ConflictError`, `DataError`); field-level validation returns `Result[Ok, Err]`. This is undocumented today. Codify the rule.

- [ ] **Step 1: Write `docs/CONVENTIONS.md`**

Create the file with content covering:

```markdown
# lexigram-admin Conventions

This document records the standing conventions for admin code. These are
specific to admin; for the framework-wide Lexigram rules see the root
`AGENTS.md` and `CLAUDE.md`.

## Result vs. Exception

**Rule:**
- **Field-level validation** returns `Result[Ok, FieldError]`. Examples:
  `IsValidAdminEmail`, `StrongPassword`, `IsValidUsername`. See
  `src/lexigram/admin/validation/rules.py`.
- **Domain operations on aggregates and services** raise typed exceptions
  inheriting from `DomainError`. Examples: `NotFoundError`,
  `PermissionDeniedError`, `ConflictError`, `DataError`. See
  `src/lexigram/admin/exceptions.py:29-73`.
- **Infrastructure failures** (database connection, cache, queue) raise
  exceptions from the source package (`lexigram-sql`, `lexigram-cache`).
  Admin catches these only at the controller boundary and translates to
  `ErrorResponse` via `htmx_error_response()`.

**Why hybrid?** UI is HTML-rendered and benefits from exceptions surfacing
through HTMX response middleware automatically. Field validation runs in
bulk (whole-form-at-once) and needs to aggregate multiple errors per request,
which is awkward with exceptions.

**Examples — correct:**
```python
# Field validation: Result
class IsValidAdminEmail(AbstractRule):
    def __call__(self, value: Any, field_name: str) -> Result[Any, FieldError]:
        if "@" not in value:
            return Err(FieldError(field=field_name, message="invalid email"))
        return Ok(value)


# Domain: typed exception
async def get_user(self, user_id: UserId) -> AdminUser:
    user = await self._repo.find(user_id)
    if user is None:
        raise NotFoundError(f"user not found: {user_id}")
    return user
```

**Examples — wrong:**
```python
# WRONG: don't return Result for domain ops
async def get_user(self, user_id: UserId) -> Result[AdminUser, DomainError]:
    ...

# WRONG: don't raise for field validation
class IsValidAdminEmail(AbstractRule):
    def __call__(self, value, field_name):
        if "@" not in value:
            raise ValueError("invalid email")
```

## Logging

Always `get_logger(__name__)` from `lexigram.logging`. Never `print()`,
never `logging.getLogger`. Errors include structured fields, not
formatted strings:

```python
log.error("admin.resource_resolution_failed", resource=cls.__name__, error=str(exc))
```

## Async

All I/O is async. Background tasks use `asyncio.create_task()` and the
task reference is stored (no fire-and-forget): see
`src/lexigram/admin/services/background_jobs.py:137-138`.

## Frozen dataclasses

Value objects that cross package boundaries (events, configs, payloads)
use `@dataclass(frozen=True, kw_only=True)`. Internal mutable state
(stores, registries) is regular `@dataclass`.

## Enums

All enums inherit `(str, Enum)` so they JSON-serialize and compare to
strings. No bare `IntEnum` for domain enums.

## Imports

- Absolute imports only — no `from .` or `from ..`.
- No `Optional[X]` / `List[X]` — use `X | None` / `list[X]`.
- UI symbols come from `from lexigram.ui import X` only. Never deep-path
  into `lexigram.ui.atoms.*`, `lexigram.ui.molecules.*`, etc. The
  phantom-import guard test enforces this.

## Result pattern unwrapping

When unwrapping a `Result`, always check `is_ok()` first:
```python
result = await service.validate(payload)
if result.is_ok():
    value = result.unwrap()
else:
    error = result.unwrap_err()
```

Never `result.unwrap()` without the check — it raises on `Err`.
```

- [ ] **Step 2: Commit**

```bash
git add lexigram-admin/docs/CONVENTIONS.md
git commit -m "docs(lexigram-admin): document Result/Exception, logging, async, typing conventions

Codifies the hybrid Result-for-validation, Exception-for-domain rule plus
logging, async, frozen-dataclass, and import-style policies.

Closes REVIEW Medium #10."
```

---

## Phase 2 — Audit and Prune the Halo

The REVIEW flagged seven subsystems as stub-heavy, experimental, or pure shells: `monitoring/`, `realtime/`, `validation/`, `views/`, `middleware/` (incomplete portions), `cli/`, plus `models/`, `layout/`, `relations/` which turned out to be substantive on closer inspection.

Each gets a binary ship-or-delete decision recorded in `docs/HALO_AUDIT.md`. The audit is the deliverable; pruning follows the audit's findings.

### Task 2.1: Audit each subsystem and record decisions

**Files:**
- Create: `docs/HALO_AUDIT.md`

- [ ] **Step 1: Audit each subsystem with concrete read-then-decide**

For each subsystem below, do the work described and record the decision in `docs/HALO_AUDIT.md`. The format per entry:

```markdown
### <directory>
- **Files:** <count>, <total lines>
- **Stubs detected:** <count> (where a "stub" is `pass`, `NotImplementedError`, or a function body of only `...`)
- **Real content:** <one-line summary>
- **External importers:** <list of admin or downstream paths that import from this directory>
- **Reachable from runtime?** YES if at least one external importer is reachable from `AdminModule.configure()` or `AdminBundleProvider.register/boot`; NO otherwise.
- **Decision:** SHIP | DELETE | DELETE-PARTIAL | DEFER-TO-FOLLOWUP
- **Rationale:** <one paragraph>
- **Action:** <concrete steps; left blank if SHIP or DEFER>
```

Run these commands as part of each audit:
```bash
# File and line counts
find src/lexigram/admin/<dir>/ -name "*.py" | xargs wc -l

# Stub detection
grep -rn "raise NotImplementedError\|^    pass$\|^    \.\.\.$" src/lexigram/admin/<dir>/

# External importer detection
grep -rn "from lexigram\.admin\.<dir>\|import lexigram\.admin\.<dir>" src/ tests/ \
        | grep -v "^src/lexigram/admin/<dir>/"
```

**Universal decision rule** (apply to monitoring/, realtime/, validation/, middleware/, views/ — anywhere the audit says SHIP-or-DELETE):

| External importer grep result                              | Reachable from runtime? | Decision        |
|------------------------------------------------------------|-------------------------|-----------------|
| ≥1 hit                                                     | YES                     | SHIP (fill stubs, add tests) |
| ≥1 hit                                                     | NO (only test/stub paths) | DELETE-PARTIAL — keep what's imported, delete the rest |
| 0 hits                                                     | —                       | DELETE          |
| Cannot determine                                           | —                       | DELETE (re-add if needed) |

This eliminates judgment calls — every decision traces to a grep + reachability check.

- [ ] **Step 2: Audit `models/`**

Read all three files: `__init__.py`, `provider_models.py`, `setting.py`. Confirm:
- `__init__.py` is a 10-line re-export of `AdminUser` from `auth.integration`.
- `provider_models.py` defines `Command` and `AdminProviderState` (used by the AdminBundleProvider).
- `setting.py` defines `SystemSetting`.

Likely outcome: **SHIP**. The REVIEW's "delete this" recommendation was based on an incomplete view. The directory holds real dataclasses. Optionally consolidate `__init__.py`'s `AdminUser` re-export to direct callers to `auth.integration` over a deprecation cycle.

- [ ] **Step 3: Audit `layout/`**

Read `layout_manager.py` (~172 lines). Confirm it defines `LayoutType` enum (LIST/GRID/CALENDAR/KANBAN/TIMELINE/MAP/TREE/CUSTOM) and `LayoutConfig` dataclass. Note: this is the layout-strategy selector, distinct from `ui/layouts/` which holds component primitives. The REVIEW called this a stub; it isn't.

Likely outcome: **SHIP**. The directory holds substantive layout-strategy types. The REVIEW's "delete or wire" recommendation was based on its initial reading; reality is "already wired through resource/page rendering". Verify with:
```bash
grep -rn "LayoutType\|LayoutConfig\|LayoutManager" src/ | grep -v "^.*layout/" | head -20
```
If callers exist, SHIP. If not, the path forward is to wire it into the resource render path, not delete.

- [ ] **Step 4: Audit `relations/`**

Read `manager.py`. Confirm `AbstractRelationManager` ABC with `table()`, `get_query()`, `count()`, `get_items()` methods.

Outcome: **DEFER-TO-FOLLOWUP**. This is the right starting point for the Filament-style RelationManager that the follow-up plan will build out. Keep as-is for now; the followup Filament plan extends this class with the inline render path.

- [ ] **Step 5: Audit `cli/`**

Read `cli/__init__.py`, `cli/contributor.py`, `cli/generators/`, `cli/templates/`. Confirm:
- Is it a runtime importer (something inside `admin/` runtime imports `from lexigram.admin.cli`)?
- Or is it only loaded via console-script entry points in `pyproject.toml`?

Run:
```bash
grep -rn "from lexigram.admin.cli\|import lexigram.admin.cli" src/ | grep -v "src/lexigram/admin/cli/"
```

If zero hits, the directory is tooling — **move out of the runtime import graph**. Options:
- Make it console-script-only (loaded via `[project.scripts]` entry points), and add a top-of-`__init__.py` guard that raises if imported at runtime.
- Or move the directory to a sibling `tools/` location alongside `src/`.

If there are runtime importers, keep in place; mark **SHIP**.

- [ ] **Step 6: Audit `monitoring/`**

Read `monitoring/__init__.py` and any monitoring submodules. The REVIEW flagged 4 stub portions and last-touch date 2026-04-22.

**Decision rule (concrete):**
1. Run:
   ```bash
   grep -rn "from lexigram\.admin\.monitoring\|import lexigram\.admin\.monitoring" src/ tests/ | grep -v "^src/lexigram/admin/monitoring/"
   ```
2. If the grep produces ≥1 hit, AND at least one hit is in a path reachable from `AdminModule` or `AdminBundleProvider` (i.e., the code runs in normal admin startup or request flow): **SHIP** — complete the stubs and add tests.
3. If the grep produces zero hits OR every hit is in another stub/experimental module: **DELETE** the directory.
4. If you cannot tell, default to **DELETE** with a follow-up issue to re-add if needed. Dead-code-by-default is the safer choice.

- [ ] **Step 7: Audit `realtime/`**

Read `realtime/__init__.py` and the SSE/WebSocket handlers (5 stubs reported). Decision rule:
- If admin's runtime depends on the SSE/WebSocket handlers (check controllers and the `AdminRealtimeSubProvider`), **SHIP** with a follow-up to fill stubs.
- If they are not on the request path, **DELETE-PARTIAL** the stub handlers; keep only what actually runs.

- [ ] **Step 8: Audit `validation/`**

Read all `validation/rules.py` and `validation/__init__.py`. 11 stubs reported. Same decision rule:
- If admin's services or contributors use the existing rules (IsValidAdminEmail, StrongPassword, IsValidUsername), **SHIP**.
- Stub portions: each rule that's just `raise NotImplementedError` either gets a real implementation or gets deleted. No middle ground.

- [ ] **Step 9: Audit `views/`**

Read `views/__init__.py` and the alternative-view files (Calendar, Kanban, Tree). 2 stubs reported.

Decision rule:
- These views overlap conceptually with the follow-up Filament plan's `Page` abstraction (LIST, CREATE, EDIT, VIEW as pages of a Resource). **DEFER-TO-FOLLOWUP**.
- For now, mark experimental in the file headers (a top-level comment like `# EXPERIMENTAL: see docs/plans/<TBD>-filament-evolution.md`).

- [ ] **Step 10: Audit `middleware/`**

Read every file in `middleware/`. 21 stubs reported. For each stub:
- Is it a placeholder for unfinished error handling, debug auth, or current-user context?
- Decision rule: each stub gets a real implementation in this task (small, scoped) or gets deleted (file an issue if it represents a planned-but-paused feature).

Aim to land with **zero stubs** in `middleware/` after this task. If any survive, they are documented in `HALO_AUDIT.md` with an explicit reason and a tracking link.

- [ ] **Step 11: Record all decisions in `docs/HALO_AUDIT.md`**

Aggregate every per-subsystem entry into one document. The file format:
```markdown
# Halo Audit — 2026-05-25

Each directory below was audited against three questions:
1. What real content exists?
2. Is it currently consumed?
3. Should we ship, delete, or defer?

## Summary

| Subsystem    | Files | Stubs | Decision           |
|--------------|------:|------:|--------------------|
| models/      |     3 |     0 | SHIP               |
| layout/      |     3 |     0 | SHIP               |
| relations/   |     3 |     0 | DEFER-TO-FOLLOWUP  |
| cli/         |    ?? |     ? | MOVE-OUT or SHIP   |
| monitoring/  |     3 |     4 | DELETE or SHIP     |
| realtime/    |     4 |     5 | SHIP or DELETE-PARTIAL |
| validation/  |     3 |    11 | SHIP (after fill)  |
| views/       |     2 |     2 | DEFER-TO-FOLLOWUP  |
| middleware/  |    10 |    21 | SHIP (after fill)  |

## Detailed findings

<one section per subsystem, as above>
```

- [ ] **Step 12: Commit the audit**

```bash
git add lexigram-admin/docs/HALO_AUDIT.md
git commit -m "docs(lexigram-admin): record halo audit decisions

Per-subsystem ship/delete/defer decisions for models, layout, relations,
cli, monitoring, realtime, validation, views, middleware. The audit is
the deliverable for this commit; subsequent commits implement each
decision.

Closes REVIEW High #4, #5, #6 (decision phase)."
```

### Task 2.2: Implement the audit decisions

**Files:** Determined by Task 2.1's outcomes — varies per subsystem.

For each subsystem with action items in `HALO_AUDIT.md`, implement the decisions one commit per subsystem. This task is intentionally template — the audit drives the work.

- [ ] **Step 1: Implement `cli/` decision**

If audit said MOVE-OUT:
- Move `src/lexigram/admin/cli/` to `tools/` at the package root, OR
- Add a top-of-`__init__.py` guard:
  ```python
  if not __name__.endswith(".__main__") and "_LEX_ADMIN_CLI_OK" not in os.environ:
      import warnings
      warnings.warn(
          "lexigram.admin.cli is tooling, not a runtime API. "
          "Use the `lexigram-admin` console script instead.",
          ImportWarning,
          stacklevel=2,
      )
  ```
- Run CI; commit.

- [ ] **Step 2: Implement `monitoring/` decision**

If audit said DELETE: `rm -r src/lexigram/admin/monitoring/`. Update any `monitoring/` re-exports in `__init__.py`. Run CI. Commit.

If audit said SHIP: fill the stub portions. Write tests for each. Commit per stub or per logical unit.

- [ ] **Step 3: Implement `realtime/` decision**

Same pattern — DELETE-PARTIAL means remove only the stub handlers, keep the actively-consumed ones. SHIP means fill stubs with real implementations and tests.

- [ ] **Step 4: Implement `validation/` decision**

For each stub rule, either implement (with a test) or delete (after confirming zero callers). Per-rule commits.

- [ ] **Step 5: Implement `middleware/` decision**

For each of the 21 stubs, decide: implement-with-test or delete. Per-middleware commits.

- [ ] **Step 6: Mark experimental directories**

For `views/` (DEFER), add a top-of-file comment in each file:
```python
"""<existing docstring>

# EXPERIMENTAL: This view type is paused. See the follow-up Filament
# evolution plan for the path forward (Page abstraction).
"""
```

- [ ] **Step 7: Final CI pass after each subsystem commit**

```bash
cd /home/admin/Documents/AI/applications/framework/lexigram && \
  uv run ruff check lexigram-admin --fix && \
  uv run ruff format lexigram-admin && \
  uv run mypy lexigram-admin/src/ && \
  uv run pytest lexigram-admin/ --tb=short
```

Expected: clean after each commit.

---

## Verification After All Phases

```bash
cd /home/admin/Documents/AI/applications/framework/lexigram && \
  uv run ruff check lexigram-admin --fix && \
  uv run ruff format lexigram-admin && \
  uv run mypy lexigram-admin/src/ && \
  uv run pytest lexigram-admin/ --tb=short
```

Spot-check that:
- `tests/integration/test_phantom_imports.py` passes — no deep-path imports remain
- `tests/integration/test_admin_provider_fail_fast.py` passes — strict mode raises, permissive mode logs
- `pyproject.toml:42` reads `"htpy>=0.9"`
- `src/lexigram/admin/ui/__init__.py` has no `from lexigram.ui.atoms.*`, `from lexigram.ui.molecules.*`, etc.
- `docs/CONVENTIONS.md` and `docs/HALO_AUDIT.md` exist with real content
- Every subsystem in `HALO_AUDIT.md` has either zero remaining stubs or an explicit `EXPERIMENTAL` marker pointing at the follow-up plan
- `from lexigram.admin import AdminModule, AdminBundleProvider` still works

---

## What This Plan Does NOT Cover (Deferred)

- **Phase 3 of REVIEW (Field-Type Triplet Consolidation):** collapsing `forms/fields/` + `ui/columns/` + `ui/filters/` into a single `SchemaField` model with three render strategies. This is the highest-leverage architectural change in the REVIEW; it needs its own plan once the foundation here is solid.
- **Phase 4 of REVIEW (Unify Action, add Page):** merging `actions/` and `ui/actions/` into one stateful `Action` class; introducing the `Page` abstraction. Deferred to the follow-up Filament plan.
- **Phase 5 of REVIEW (Cluster, RelationManager):** promoting `navigation_groups` config to first-class `Cluster`; growing `relations/AbstractRelationManager` into a full inline relation editor. Deferred — `relations/` is preserved here precisely so the follow-up has a foundation.
- **Phase 6 of REVIEW (IDataSource protocol):** replacing `Resource.fetch_list()` polymorphism with a typed protocol. Deferred.
- **Phase 7 of REVIEW (Full docs):** `docs/ARCHITECTURE.md`, `docs/RESOURCES.md`, `docs/CONTRIBUTORS.md`, `docs/FILAMENT_PARITY.md`, `docs/PUBLIC_API.md`, scenario tests. Phase 7 of the REVIEW is naturally split between this plan (which adds `CONVENTIONS.md` and `HALO_AUDIT.md`) and the follow-up Filament plan (which adds the architecture docs).

The follow-up Filament-evolution plan should be drafted at
`lexigram-admin/docs/plans/<DATE>-filament-evolution.md` after this plan
is merged and the post-merge state has stabilized for a release cycle.

---

## Cross-Package Coordination Notes

This plan **requires `lexigram-ui` Phase 1 (Public API Hardening) to be merged before Task 1.2 can complete.** That phase adds 80+ symbols to ui's `_LAZY_IMPORTS` that admin needs to import through the public API. If ui Phase 1 is not yet done, pause here and run `lexigram-ui/docs/plans/2026-05-25-foundation-hardening.md` Phase 1 first.

`lexigram-ui` plan also has a coordination note pointing back here for the htpy constraint resolution (Task 1.1).
