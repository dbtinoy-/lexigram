# Phase 4 — Action and Page Unification

> **Parent:** `docs/plans/2026-05-25-filament-evolution.md`
> **ADRs:** ADR-002 (Action), ADR-003 (Page)
> **Estimate:** 3–4 weeks
> **Risk:** MEDIUM — naming collisions during migration; routing layer touched

## Architecture

Three parallel action concepts → one unified `Action[R, O]` (per ADR-002):
- `actions/row_manager/types.py:RowAction` (dataclass config) — legacy, stays
- `ui/actions/base.py:Action` (fluent builder, HTMX rendering) — deprecated, becomes alias
- `services/action_registry.py:ActionConfig/ActionHandler` (backend execution) — absorbed into new Action.execute()

New hierarchy in `actions/base.py`:
```
Action[R, O] (ABC, Generic)
├── RowAction(Action[Any, ActionResult]) — single record
├── BulkAction(Action[list[Any], ActionResult]) — multiple records
└── HeaderAction(Action[None, ActionResult]) — no record context
```

Page abstraction (ADR-003) in `pages/base.py`:
```
Page (ABC)
├── ListPage — default resource list
├── CreatePage — default resource create
├── EditPage — default resource edit
└── ViewPage — default resource detail
```

## File Layout

```
src/lexigram/admin/actions/
├── __init__.py       # Re-export new types + legacy lazy-loads
├── base.py           # Action, RowAction, BulkAction, HeaderAction
├── types.py          # ActionColor, ActionContext, ConfirmationConfig
├── exceptions.py     # ActionError, PermissionDenied
└── standard.py       # EditAction, DeleteAction, CreateAction, DeleteBulkAction, ViewAction

src/lexigram/admin/ui/actions/
├── __init__.py       # Updated: re-export from actions/ with DeprecationWarning
├── base.py           # Updated: DeprecationWarning emit, delegate to new Action
└── standard.py       # Updated: DeprecationWarning emit, delegate to new standard actions

src/lexigram/admin/pages/
├── __init__.py       # Re-exports
├── base.py           # Page ABC
├── types.py          # PageResponse, NavigationEntry
└── resource_pages.py # ListPage, CreatePage, EditPage, ViewPage

tests/unit/actions/
├── test_action_base.py
├── test_action_types.py
├── test_action_exceptions.py
└── test_standard_actions.py

tests/unit/pages/
├── test_page_base.py
└── test_resource_pages.py
```

## Bite-Sized TDD Steps

### Task 4.2a — Action types and base class

**Step 1: `actions/types.py`** (5 min)
- `ActionColor(str, Enum)` — GRAY, PRIMARY, SUCCESS, WARNING, DANGER, INFO
- `ActionContext` — dataclass with `request: Any | None = None`, `user: Any | None = None`, `resource_name: str = ""`
- `ConfirmationConfig` — frozen dataclass with `title: str`, `message: str | None = None`, `style: ActionColor = ActionColor.WARNING`

Tests: verify enum values, dataclass fields, factory/construction patterns.

**Step 2: `actions/exceptions.py`** (5 min)
- `ActionError(DomainError)` — base for action errors
- `PermissionDenied(ActionError)` — authorization failure

Tests: verify inheritance chain, instance checks.

**Step 3: `actions/base.py` — Action base** (15 min)
- `Action(ABC, Generic[R, O])` — frozen dataclass with `name: str`, `label: str | None = None`, `icon: str | None = None`, `color: ActionColor = ActionColor.GRAY`, `keyboard_shortcut: str | None = None`
- `@abstractmethod async def execute(self, record_or_records: R, ctx: ActionContext) -> Result[O, ActionError]`
- `def visible_for(self, record: R, user: AdminUser | None) -> bool` — default True
- `def authorize(self, record: R, user: AdminUser | None) -> Result[None, PermissionDenied]` — default Ok(None)
- `def form(self) -> Form | None` — default None
- `def confirm(self) -> ConfirmationConfig | None` — default None
- `def render_button(self, record: R, ctx: ActionContext) -> Element` — renders a simple button via htpy

Tests: verify ABC cannot be instantiated, all defaults work, abstract execute forces override, render_button produces an Element.

**Step 4: `actions/base.py` — specializations** (10 min)
- `RowAction(Action[Any, ActionResult])` — no additional overrides
- `BulkAction(Action[list[Any], ActionResult])` — no additional overrides
- `HeaderAction(Action[None, ActionResult])` — no additional overrides

Tests: verify isinstance(a, Action), generic type variance, concrete instantiation with simple mock execute.

**Step 5: `actions/__init__.py` update** (5 min)
Add new exports to the lazy-loading mechanism.

### Task 4.2b — Standard action subclasses

**Step 1: `actions/standard.py` — EditAction**
- `EditAction(RowAction)` — name="edit", label="Edit", icon="pencil", color=PRIMARY
- `execute(self, record, ctx)` — delegates to `ctx.data_source.update(record, ...)` but since ActionContext doesn't have data_source yet in the first iteration, make it a simple stub that returns ActionResult

**Step 2: `actions/standard.py` — DeleteAction**
- `DeleteAction(RowAction)` — name="delete", label="Delete", icon="trash", color=DANGER
- `confirm()` returns ConfirmationConfig with delete message

**Step 3: `actions/standard.py` — CreateAction**
- `CreateAction(HeaderAction)` — name="create", label="Create", icon="plus", color=PRIMARY

**Step 4: `actions/standard.py` — DeleteBulkAction**
- `DeleteBulkAction(BulkAction)` — name="delete", label="Delete Selected", icon="trash", color=DANGER

**Step 5: `actions/standard.py` — ViewAction**
- `ViewAction(RowAction)` — name="view", label="View", icon="eye", color=GRAY

### Task 4.2c — Migration shim

**Step 1: Update `ui/actions/base.py`**
The old `Action` and `BulkAction` classes stay as-is but `__init__` emits `DeprecationWarning("Use lexigram.admin.actions.base.Action instead")`.

**Step 2: Update `ui/actions/standard.py`**
`EditAction`, `DeleteAction`, etc. become thin subclasses of the new `actions/standard.py` equivalents, emitting deprecation warnings.

**Step 3: Update `ui/actions/__init__.py`**
Add deprecation warnings to each re-export pointing at new import paths.

### Task 4.5a — Page base class

**Step 1: `pages/types.py`**
- `PageResponse` — dataclass with `content: Element`, `title: str`, `breadcrumbs: list[tuple[str, str]] | None = None`
- `NavigationEntry` — dataclass with `label: str`, `url: str`, `icon: str | None = None`, `permissions: list[str] | None = None`

**Step 2: `pages/base.py`**
- `Page(ABC)` — ABC with `title: str` (frozen dataclass field), `path: str = ""`
- `@abstractmethod async def view(self, request: Any) -> PageResponse` — main entry point
- `async def post(self, request: Any) -> PageResponse` — default raises MethodNotAllowed
- `def navigation(self) -> NavigationEntry | None` — default None

### Task 4.5b — Resource pages

**Step 1: `pages/resource_pages.py` — ListPage(Page)**
- `__init__(self, resource: type[Resource], ...)` — takes resource class
- `view()` renders list view via existing resource controller patterns

**Step 2–4:** CreatePage, EditPage, ViewPage — similar pattern.

## Validation Gate

```bash
cd /home/admin/Documents/AI/applications/framework/lexigram
uv run ruff check lexigram-admin/ && \
  uv run ruff format --check lexigram-admin/ && \
  uv run mypy lexigram-admin/src/ && \
  uv run pytest lexigram-admin/tests/unit/actions/ lexigram-admin/tests/unit/pages/ --tb=short -x -W ignore::DeprecationWarning
```

## Task Dependencies

```
4.2a (Action types+base) ──► 4.2b (Standard actions) ──► 4.2c (Migration shim)
4.5a (Page base) ──► 4.5b (Resource pages)
     ↑ both independent of action track
```
