# lexigram-admin Filament Evolution Plan

> **For agentic workers:** This is a strategic design + phased implementation plan covering REVIEW Phases 3–7. It is NOT a bite-sized TDD task list — those live in per-phase implementation plans (`docs/plans/2026-XX-XX-phase-<N>-<topic>.md`) that should be written after each ADR below is approved. Use this document to align on architecture, validate effort, and sequence the work.

**Goal:** Take `lexigram-admin` from "solid foundation" (post-foundation-hardening) to "Filament-grade admin framework" by consolidating duplicated field/action/column/filter models, adding first-class Page/Cluster/RelationManager abstractions, and enforcing the existing `IDataSource` Protocol everywhere. Net result: defining a Resource produces forms, tables, filters, actions, related-record management, dashboard widgets, and navigation with one consistent declarative API — what Filament gives Laravel users, adapted to Lexigram's contract-first, async, typed Python idiom.

**Architecture:** Five sequential phases (3 through 7, matching REVIEW), with one orthogonal track (Phase 6 — IDataSource) and one parallel track (Phase 7 — docs). Each phase produces an independently-shippable consolidation. Phase 3 (SchemaField) is the highest-leverage and highest-risk; Phase 5 (RelationManager) is the highest-complexity. Phase 6 (IDataSource) is the lowest-risk but blocks several Phase 5 use cases.

**Spec sources:**
- `lexigram-admin/REVIEW.md` — full architectural review (§9 Phases 3–7)
- `lexigram-admin/docs/plans/2026-05-25-foundation-hardening.md` — completed Phase 1–2 (assumed merged)
- `lexigram-admin/docs/CONVENTIONS.md` — Result/Exception doctrine
- `lexigram-admin/docs/HALO_AUDIT.md` — subsystem decisions
- Filament documentation (for pattern reference, not direct adoption)

**Working directory:** `/home/admin/Documents/AI/applications/framework/lexigram/lexigram-admin`

**Total effort estimate:** **14–18 weeks for one senior developer**, validated against REVIEW's 12–16 week estimate (slight upward revision reflects the SchemaField surface area being larger than REVIEW assumed). Two developers in parallel can compress this to **~10 weeks** by running Phase 6 (IDataSource) and Phase 7 (docs) parallel to Phases 3–5.

---

## Hard Prerequisites

This plan **assumes the foundation plans are merged**:
1. `lexigram-ui/docs/plans/2026-05-25-foundation-hardening.md` — all phases merged. Public API expanded; deep-path imports eliminated; toast schism resolved.
2. `lexigram-admin/docs/plans/2026-05-25-foundation-hardening.md` — all phases merged. htpy pinned; phantom-import guard active; fail-fast resource resolution; halo audit decisions implemented.

Verify before starting any phase below:
```bash
cd /home/admin/Documents/AI/applications/framework/lexigram && \
  uv run pytest lexigram-admin/ --tb=short && \
  uv run pytest lexigram-ui/ --tb=short
```
Both must pass cleanly. If not, return to the foundation plans.

---

# Part I — Architectural Decision Records

Each ADR is a self-contained design rationale. Read the ADR for a phase before reading that phase's implementation tasks.

## ADR-001: SchemaField — One Field, Three Presentations

**Status:** Accepted (this plan)
**Affects:** Phase 3
**Closes REVIEW finding:** §4 Critical #1 — Field-Type Triplet Duplication

### Context

Three independent field models exist today:
- `src/lexigram/admin/forms/fields/` — `TextField`, `IntegerField`, `BooleanField`, `DateField`, `SelectField`, `MarkdownField`, `RichTextField`, `JsonField`, etc. — declarative form-input definitions.
- `src/lexigram/admin/ui/columns/` — `Column`, `TextColumn`, `BadgeColumn`, `DateColumn`, etc. — table-cell renderers with sortable/searchable metadata.
- `src/lexigram/admin/ui/filters/` — `SelectFilter`, `RangeFilter`, `DateFilter`, etc. — filter-bar widgets.

Adding a new field type today requires changes in three places, kept in sync manually. The duplication produces inconsistent behavior (a column that's filterable in one resource but not in another, even though both share the underlying type), and slows feature development.

### Decision

A single `SchemaField` abstract base class lives in `src/lexigram/admin/schema/` (new directory). Concrete subclasses (`TextField`, `NumberField`, etc.) declare their identity once. Three render strategies surface the field in three contexts:

```python
# src/lexigram/admin/schema/base.py
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

from lexigram.result import Result
from lexigram.ui import Element

T = TypeVar("T")  # Python type the field holds (str, int, datetime, ...)


@dataclass(frozen=True, kw_only=True)
class SchemaField(ABC, Generic[T]):
    """A typed field that can be rendered as a form input, a table column, or a filter widget.

    Subclasses implement the three render methods. A SchemaField is the single
    source of truth for a field's identity — name, label, type, validation,
    visibility — and is consumed by FormRenderer, TableRenderer, and FilterRenderer.
    """

    name: str
    label: str | None = None
    help_text: str | None = None
    placeholder: str | None = None

    # Behavior flags (read by the render strategies)
    nullable: bool = True
    readonly: bool = False
    required: bool = False
    sortable: bool = True
    searchable: bool = False
    filterable: bool = True
    visible_in_form: bool = True
    visible_in_list: bool = True
    visible_in_view: bool = True

    # Validation
    validators: list[FieldValidator] = field(default_factory=list)

    # Default and serialization
    default: T | None = None

    @abstractmethod
    def render_form(self, value: T | None, *, errors: list[str] | None = None) -> Element:
        """Render this field as a form input."""

    @abstractmethod
    def render_column(self, record: Any, value: T | None) -> Element:
        """Render this field as a table-cell value."""

    def render_filter(self, current_value: Any | None = None) -> Element | None:
        """Render this field as a filter widget. Return None to opt out.

        Default returns None — fields opt in by overriding. This makes filter
        rendering an explicit choice per field type rather than a flag.
        """
        return None

    # Value coercion at the form boundary
    def from_form(self, raw: str | None) -> Result[T | None, FieldError]:
        """Coerce a raw form string to the field's Python type."""
        return Ok(raw)  # type: ignore[arg-type]

    def to_form(self, value: T | None) -> str:
        """Coerce the field's Python value to a form-display string."""
        return "" if value is None else str(value)
```

### Concrete subclass hierarchy

```
SchemaField (abstract)
├── TextField              (str)
│   ├── EmailField
│   ├── PasswordField
│   └── URLField
├── TextAreaField          (str)
│   └── MarkdownField
│       └── RichTextField
├── NumberField            (int | float)
│   ├── IntegerField
│   ├── FloatField
│   └── CurrencyField
├── BooleanField           (bool)
│   └── ToggleField
├── DateField              (date)
│   ├── DateTimeField
│   └── TimeField
├── SelectField            (T from a fixed set)
│   ├── EnumField
│   ├── MultiSelectField
│   └── RadioField
├── RelationField          (T = related record ID)
│   ├── BelongsToField
│   ├── HasManyField       (replaces MorphTo for the simple case)
│   └── MorphField
├── JsonField              (dict | list)
├── FileField              (UploadedFile)
│   ├── ImageField
│   └── AvatarField
├── ColorField             (str hex)
├── RatingField            (int 1–5)
├── TagsField              (list[str])
├── KeyValueField          (dict[str, str])
└── HiddenField            (Any)
```

### Why three render methods and not three strategy classes

We considered:
1. **Three sibling types per field** with a registry that links them (today's structure) — rejected; preserves duplication.
2. **One method per render context on the field** (chosen) — pros: single class, single import, no registry indirection. Cons: classes can grow large.
3. **One field + three strategy classes** (`FormStrategy`, `ColumnStrategy`, `FilterStrategy`) injected at construction — rejected; adds three classes per type for negligible flexibility. Strategies that vary by field are rare; when they do exist, subclassing the field is cleaner than swapping a strategy.

Each render method is short (3–30 lines) because it delegates to `lexigram.ui` components. The class stays readable.

### Migration strategy

Three sub-phases inside Phase 3 (see Part III for tasks):
- **3a — Build:** Implement `SchemaField` and ~30 concrete subclasses in `src/lexigram/admin/schema/`. Full test coverage per field.
- **3b — Bridge:** Add deprecation shims to `forms/fields/`, `ui/columns/`, `ui/filters/` — each old class becomes a thin wrapper that wraps a `SchemaField` and emits `DeprecationWarning` with the recommended replacement.
- **3c — Migrate:** Update internal admin resources to declare `SchemaField`s. Add a Resource class-level `fields: list[SchemaField]` attribute that supersedes `columns: list[Column]`, `filters: list[Filter]`, and the `form_class` field collection.
- **3d — Cleanup:** After one release cycle with deprecation warnings active, delete the three old directories.

### Backward compatibility

During Phases 3b–3c, both old and new APIs work in parallel. The `Resource.columns: list[Column]` attribute continues to render tables; `Resource.fields: list[SchemaField]` is the new path. A Resource may declare either — but not both. Validation at registration time enforces this.

### Risks

See Part IV — Risk Register, RISK-001.

---

## ADR-002: Action — One Stateful Class

**Status:** Accepted
**Affects:** Phase 4
**Closes REVIEW finding:** §4 High #9 — `actions/` vs `ui/actions/` split

### Context

Two parallel action concepts exist:
- `src/lexigram/admin/actions/` (20 files) — managers for bulk operations, header operations (column visibility, density), row operations (the CRUD execution layer). Returns Results, dispatches commands.
- `src/lexigram/admin/ui/actions/` — `EditAction`, `DeleteAction`, action button base classes. Renders UI.

The split is defensible (business logic vs presentation) but every action requires touches in both directories. Users perceive a single concept.

### Decision

A single `Action` class. Subclasses define behavior via methods. Three flavors via type variables, not separate classes:

```python
# src/lexigram/admin/actions/base.py (new home — old contents migrate here)
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Generic, TypeVar

from lexigram.result import Err, Ok, Result
from lexigram.ui import Element

R = TypeVar("R")  # record type (single record, list, or None for "no record")
O = TypeVar("O")  # outcome type


class ActionColor(str, Enum):
    GRAY = "gray"
    PRIMARY = "primary"
    SUCCESS = "success"
    WARNING = "warning"
    DANGER = "danger"
    INFO = "info"


@dataclass(frozen=True, kw_only=True)
class Action(ABC, Generic[R, O]):
    """A stateful admin action.

    Subclasses define:
    - `execute()` — the business logic, returns Result[O, ActionError]
    - `visible_for(record, user)` — predicate; default True
    - `authorize(record, user)` — Result; default Ok(None)
    - `form()` — optional form for action arguments; default None
    - `confirm()` — optional confirmation; default None
    """

    name: str
    label: str | None = None
    icon: str | None = None
    color: ActionColor = ActionColor.GRAY
    keyboard_shortcut: str | None = None

    @abstractmethod
    async def execute(self, record_or_records: R, ctx: ActionContext) -> Result[O, ActionError]:
        ...

    def visible_for(self, record: R, user: AdminUser | None) -> bool:
        return True

    def authorize(self, record: R, user: AdminUser | None) -> Result[None, PermissionDenied]:
        return Ok(None)

    def form(self) -> Form | None:
        return None

    def confirm(self) -> ConfirmationConfig | None:
        return None

    def render_button(self, record: R, ctx: ActionContext) -> Element:
        """Default button rendering — override for custom styling."""
        ...  # delegate to lexigram.ui.Button with action metadata
```

Three specializations distinguished by their record type:

```python
class RowAction(Action[Any, "ActionOutcome"]):
    """An action against a single record."""

class BulkAction(Action[list[Any], "ActionOutcome"]):
    """An action against multiple records (selection-driven)."""

class HeaderAction(Action[None, "ActionOutcome"]):
    """An action with no record context (e.g., 'Create New', 'Export All')."""
```

### Why not three unrelated classes

Single `Action` base with `Generic[R, O]` keeps the contract uniform — visibility, authorization, forms, confirmations behave identically regardless of record context. The execute signature varies only in its single argument. UI rendering picks the right button/icon by inspecting the subclass.

### Migration

- `src/lexigram/admin/actions/managers/` business logic absorbs into `Action.execute()` overrides.
- `src/lexigram/admin/ui/actions/EditAction`, `DeleteAction` become `RowAction` subclasses.
- Deprecation aliases at old import paths for one release.

Old `Resource.actions: list[Action]` and `Resource.bulk_actions: list[BulkAction]` are now both `list[Action]` (or specifically typed if Resource wants to constrain). The Resource list is split at registration time by inspecting `isinstance(a, BulkAction)`.

### Risks

See RISK-002. Naming collision between old `Action` ABCs in `ui/actions/` and new `Action` in `actions/` must be carefully sequenced.

---

## ADR-003: Page — First-Class Routing Unit

**Status:** Accepted
**Affects:** Phase 4
**Closes REVIEW finding:** §5 Recommended Target Architecture

### Context

Today every non-resource page (settings, custom dashboards, reports) is an ad-hoc controller in `src/lexigram/admin/controllers/`. Resource pages (list, create, edit, view) are implicit — the routing is hardcoded inside the resource controller.

### Decision

A first-class `Page` class. Resources declare a `pages` list. Custom pages extend `Page` directly.

```python
# src/lexigram/admin/pages/base.py
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, ClassVar

from lexigram.ui import Element

from lexigram.admin.rbac.schema import Permission


@dataclass(frozen=True, kw_only=True)
class Page(ABC):
    """Base class for admin pages.

    A Page is the unit of routing. Each Page declares its URL fragment, its
    title, and (optionally) its required permissions. Subclasses implement
    `get()` and optionally `post()`.
    """

    title: str
    path: str  # URL fragment relative to the admin prefix
    permissions: ClassVar[list[Permission]] = []
    breadcrumbs: bool = True  # auto-build from path by default

    @abstractmethod
    async def get(self, request: AdminRequest) -> Element:
        """Render the page (GET request)."""

    async def post(self, request: AdminRequest) -> Element | RedirectResponse:
        """Handle form submission (POST). Default raises MethodNotAllowed."""
        raise MethodNotAllowed("This page does not accept POST")

    def navigation(self) -> NavigationEntry | None:
        """Optional navigation entry. Resources auto-generate; custom pages opt in."""
        return None
```

### Resource pages (built-in)

```python
# src/lexigram/admin/pages/resource_pages.py

class ListPage(Page):
    """Default resource list page — table with filters, search, pagination, bulk actions."""

class CreatePage(Page):
    """Default resource create page — form for a new record."""

class EditPage(Page):
    """Default resource edit page — form pre-filled with the existing record."""

class ViewPage(Page):
    """Default resource view page — read-only detail with relation managers."""
```

Resource declares:
```python
class UserResource(Resource):
    model = User
    fields = [...]
    pages = [ListPage, CreatePage, EditPage, ViewPage]  # default
```

If `pages` is not declared, all four defaults are used. To suppress one (e.g., a write-locked resource without Create/Edit), pass an explicit shorter list.

### Custom pages

```python
class SalesReportPage(Page):
    title = "Sales Report"
    path = "/reports/sales"
    permissions = [Permission("reports.view")]

    async def get(self, request):
        # arbitrary admin page
        ...
```

Custom pages register through `AdminContributor.pages()` or `AdminBuilder.page(SalesReportPage)`.

### Why this is not just "controllers, but a class"

The Page abstraction layers permissions, navigation, breadcrumbs, and (optionally) Cluster membership into one declarative artifact. A controller in the current codebase carries none of this metadata cleanly. Pages also become the natural unit for inheriting layout/chrome from a Cluster — a controller has no semantic for that.

### Backward compatibility

Existing controllers continue to work — they are registered as routes the same way. The first Resource refactor lands two systems in parallel: legacy controllers and Pages. Over Phase 4c, resources migrate to Pages; legacy controllers remain valid for any standalone routes.

---

## ADR-004: Cluster — First-Class Navigation Grouping

**Status:** Accepted
**Affects:** Phase 5 (first task; small)
**Closes REVIEW finding:** §5 Recommended Target Architecture (Cluster)

### Context

Today, navigation groups are configured via `AdminConfig.navigation_groups: dict[str, AdminNavigationGroup]` and resources reference a group by string name (`Resource.group: str | None`). This is config-driven — there is no way to attach permissions, shared chrome, or shared behavior to a group.

### Decision

A first-class `Cluster` class that holds resources and pages.

```python
# src/lexigram/admin/clusters/base.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from lexigram.admin.pages.base import Page
from lexigram.admin.rbac.schema import ClusterPermissions
from lexigram.admin.resources.base import Resource


@dataclass(frozen=True, kw_only=True)
class Cluster:
    """A grouping of resources and pages with shared label, icon, and permissions."""

    name: str
    label: str
    icon: str | None = None
    order: int = 0
    collapsible: bool = True
    collapsed_by_default: bool = False
    permissions: ClusterPermissions | None = None
    # Populated at registration time from contributors and the AdminBuilder DSL:
    resources: list[type[Resource]] = field(default_factory=list)
    pages: list[type[Page]] = field(default_factory=list)
```

### Migration

`AdminConfig.navigation_groups` (dict) is converted to `clusters: list[Cluster]` at config load time, emitting `DeprecationWarning` if the old dict shape is used. New apps declare clusters directly:

```python
# Inside app's admin configuration
clusters = [
    Cluster(name="content", label="Content", icon="document"),
    Cluster(name="users", label="Users & Access", icon="users", permissions=ClusterPermissions(view="admin.users.view")),
]
```

Resources declare cluster by name:
```python
class UserResource(Resource):
    cluster = "users"  # replaces the old `group` attribute
```

`Resource.group` is kept as a deprecated alias for `cluster`.

---

## ADR-005: RelationManager — Inline Related-Record Editor

**Status:** Accepted
**Affects:** Phase 5
**Closes REVIEW finding:** §4 High #5 — `relations/` is a stub

### Context

`src/lexigram/admin/relations/manager.py` already defines `AbstractRelationManager` (ABC, 127 lines) with `relationship_name`, `parent_id`, `parent`, `table()`, `get_query()`, `count()`, `get_items()`, `get_relationship_name()`. It is the right starting point — but it does not yet support inline editing, only inline display.

### Decision

Extend `AbstractRelationManager` (not replace it) with HTMX-driven inline edit, create, delete, and detach. The render path lives on the resource's `ViewPage`.

```python
# src/lexigram/admin/relations/manager.py — extended

@dataclass(frozen=True, kw_only=True)
class RelationManager(AbstractRelationManager, ABC):
    """A relation manager with inline editing support.

    Subclasses define:
    - `table()` — list of SchemaField (was `Column` in the legacy ABC)
    - `get_query()` — load related records for the parent
    - `create_form()` — optional; enables an "add related" button
    - `edit_form()` — optional; enables row-level edit
    - `can_detach`, `can_delete`, `can_create` — permission predicates
    """

    # Inline rendering policy
    inline_create: bool = True
    inline_edit: bool = True
    inline_delete: bool = True
    inline_detach: bool = False  # only for many-to-many; default off

    # Forms (default to forms derived from `table()`)
    def create_form(self) -> Form | None:
        return self._derive_form_from_table()

    def edit_form(self, record: Any) -> Form | None:
        return self._derive_form_from_table(initial=record)

    # Permissions
    def can_create(self, user: AdminUser | None) -> Result[None, PermissionDenied]:
        return Ok(None)

    def can_edit(self, record: Any, user: AdminUser | None) -> Result[None, PermissionDenied]:
        return Ok(None)

    def can_delete(self, record: Any, user: AdminUser | None) -> Result[None, PermissionDenied]:
        return Ok(None)

    # Render entry point — invoked by ViewPage
    async def render(self, request: AdminRequest) -> Element:
        ...
```

### HTMX inline-edit cycle

The user's experience and the implementation pattern:

| User action          | HTMX request                                  | Server response                                          |
|----------------------|-----------------------------------------------|----------------------------------------------------------|
| Click "Add"          | `GET /admin/{r}/{id}/relations/{rel}/new`     | Returns the create form rendered into the relation panel |
| Submit create form   | `POST /admin/{r}/{id}/relations/{rel}`        | Creates record; returns the updated relation panel       |
| Click row "Edit"     | `GET /admin/{r}/{id}/relations/{rel}/{rid}/edit` | Replaces the row with an edit form                    |
| Submit edit form     | `PUT /admin/{r}/{id}/relations/{rel}/{rid}`   | Updates record; replaces the form with the display row   |
| Click row "Delete"   | `DELETE /admin/{r}/{id}/relations/{rel}/{rid}` (with confirm) | Removes the row                              |

All swaps use HTMX `hx-swap="outerHTML"` targeted at the row or the relation panel. The relation panel is registered as a `Zone` (per `lexigram-ui`'s zone registry) so multiple managers on a ViewPage don't collide.

### Risks

See RISK-005. This is the highest-complexity phase — it touches data layer, UI components, HTMX zone wiring, and permissions simultaneously.

---

## ADR-006: IDataSource — Enforce the Existing Protocol

**Status:** Accepted
**Affects:** Phase 6
**Closes REVIEW finding:** §4 High #6 — fragile `fetch_list()` polymorphism

### Context

`IDataSource[T]` already exists at `src/lexigram/admin/data/data_source.py:35` and is implemented by `APIDataSource[T]` at `src/lexigram/admin/data/adapters/api_adapter.py:24`. The polymorphism issue is in `src/lexigram/admin/resources/base.py:141-243` (REVIEW reference), which tries three method signatures (`find_many`, `find`, `list`) on whatever object is attached as the resource's data source. This bypasses the typed Protocol entirely.

### Decision

Phase 6 is **enforcement, not invention**:
1. Audit `IDataSource` Protocol for completeness (does it cover create/update/delete? Search? Pagination? Counting?).
2. Remove the three-signature fallback in `Resource.fetch_list()`. Require data sources to implement `IDataSource`.
3. Add a CI-time guard test: every data source registered with admin must pass `isinstance(ds, IDataSource)` (at type-check time via `runtime_checkable` Protocol).
4. Update existing data sources (`APIDataSource`, any others) to match the audited Protocol.

```python
# src/lexigram/admin/data/data_source.py — audited Protocol

from typing import Generic, Protocol, TypeVar, runtime_checkable

from lexigram.admin.data.query_builder import Query
from lexigram.result import Result

T = TypeVar("T")


@runtime_checkable
class IDataSource(Protocol, Generic[T]):
    """Typed data-source contract.

    Every admin Resource holds an IDataSource. Implementations may target
    SQL, an external API, in-memory data, or any source — the Protocol
    abstracts the access pattern.
    """

    async def find_many(self, query: Query) -> Result[PaginatedResult[T], DataError]: ...
    async def find_one(self, id: Any) -> Result[T | None, DataError]: ...
    async def count(self, query: Query) -> Result[int, DataError]: ...
    async def create(self, data: dict[str, Any]) -> Result[T, DataError]: ...
    async def update(self, id: Any, data: dict[str, Any]) -> Result[T, DataError]: ...
    async def delete(self, id: Any) -> Result[None, DataError]: ...
```

### Migration

- Update `IDataSource` Protocol to include any missing methods (verified via Phase 6 Task 6.1 audit).
- Update `APIDataSource` and any other implementations to satisfy the audited Protocol.
- In `Resource.fetch_list()`, replace the three-signature sniffing with a single typed call: `await self._data_source.find_many(query)`. If `self._data_source` does not satisfy `IDataSource`, raise `TypeError` at registration time, not lazily at first query.

### Why Phase 6 is independent of Phases 3–5

Phase 6 doesn't change the field/action/page/cluster/relation surface — it cleans up the data-access plumbing. It can run **in parallel** with the other consolidation phases. A second developer can own Phase 6 entirely.

### Risks

See RISK-006. Smallest risk of all phases; existing implementations are likely close to the Protocol already.

---

## ADR-007: Documentation Strategy

**Status:** Accepted
**Affects:** Phase 7 (parallel with all others)

### Context

`docs/ARCHITECTURE.md`, `docs/SECURITY.md` exist as stubs (per the foundation review). `docs/CONVENTIONS.md` and `docs/HALO_AUDIT.md` were written during Phase 1–2. The Filament-evolution work adds five major abstractions that need documenting: `SchemaField`, `Action`, `Page`, `Cluster`, `RelationManager` — plus `IDataSource` enforcement.

### Decision

Documentation is written **alongside** each phase, not deferred. Each phase's exit criteria include the docs landing. A documentation-only sub-phase (7) ties together a Resource walkthrough, Filament parity map, and stability-tier registry.

Six documents:

| Document                       | Owner phase | Purpose                                              |
|--------------------------------|-------------|------------------------------------------------------|
| `docs/ARCHITECTURE.md`         | Phase 7     | Three-ring model + abstraction overview              |
| `docs/RESOURCES.md`            | Phase 3+4   | How to define a Resource end-to-end                  |
| `docs/CONTRIBUTORS.md`         | Phase 7     | How to write an `AdminContributor`                   |
| `docs/SECURITY.md`             | Phase 7     | RBAC, audit, CSRF, rate limiting                     |
| `docs/FILAMENT_PARITY.md`      | Phase 7     | Filament ↔ Lexigram concept map for migrators        |
| `docs/PUBLIC_API.md`           | Phase 7     | Every exported symbol with stability tier            |

Each ADR in this plan becomes a section of `docs/ARCHITECTURE.md` (lightly edited).

---

# Part II — Protocol Inventory

New and updated Protocols, with placement decisions.

| Protocol               | Lives in           | Justification                                                        |
|------------------------|--------------------|----------------------------------------------------------------------|
| `SchemaFieldProtocol`  | `lexigram-admin`   | Admin-specific surface; field rendering is bound to admin UI idioms |
| `ActionProtocol`       | `lexigram-admin`   | Admin-specific; tied to record + permission concepts admin owns      |
| `PageProtocol`         | `lexigram-admin`   | Admin-specific routing concept                                       |
| `ClusterProtocol`      | `lexigram-admin`   | Admin-specific navigation concept                                    |
| `RelationManagerProtocol` | `lexigram-admin` | Admin-specific; depends on `SchemaFieldProtocol` and `ActionProtocol` |
| `IDataSource`          | `lexigram-admin`   | Already lives here (`data/data_source.py`); stays                    |

**Rationale for keeping all in `lexigram-admin`:** these protocols all reference admin-domain types (`AdminUser`, `Permission`, `AdminRequest`, `Zone`, `Cluster`) that themselves live in admin. Hoisting any single one to `lexigram-contracts` would force the contracts package to either (a) re-import admin types (circular) or (b) replace them with placeholder Protocols (creates indirection without value). The Lexigram framework convention says contracts hold cross-package agreements; these are intra-admin agreements.

**Future hoisting candidate:** If a second admin-style package emerges in the framework (e.g., a developer portal that shares `Page` semantics), `PageProtocol` could move to `lexigram-contracts`. Defer that decision until the second use case is concrete.

---

# Part III — Implementation Plan (Phases 3–7)

Phases run in this order:
- **Phase 3** — SchemaField (3–5 weeks)
- **Phase 4** — Action + Page (3–4 weeks)
- **Phase 5** — Cluster + RelationManager (3–4 weeks)
- **Phase 6** — IDataSource enforcement (1–2 weeks) — **can run parallel with 3, 4, or 5**
- **Phase 7** — Documentation (2 weeks) — **partially parallel** (each phase contributes docs as it lands; Phase 7 is the final polish)

Dependency graph:

```
Phase 3 (SchemaField) ──┐
                        ├──► Phase 4 (Action + Page) ──┐
                        │                              ├──► Phase 5 (Cluster + RelationManager)
                        └──────────────────────────────┘
                                       │
                                       └──► Phase 7 (Documentation final polish)

Phase 6 (IDataSource) — independent, can start any time
```

Each phase below lists tasks at the **task-level**, not the bite-sized step level. Per-phase implementation plans with TDD steps are written separately, one per phase, after this strategic plan is approved.

## Phase 3 — SchemaField Consolidation

**Estimate:** 3–5 weeks single developer
**Risk:** **HIGH** — broadest surface area; touches every existing resource
**Deliverable:** `src/lexigram/admin/schema/` with full hierarchy; old `forms/fields/`, `ui/columns/`, `ui/filters/` deprecated; internal resources migrated; migration guide written.

### Task 3.1 — Design freeze (1 week)

Output a sub-plan at `lexigram-admin/docs/plans/2026-XX-XX-phase-3-schemafield.md` with:
- Full `SchemaField` base class signature (frozen)
- Every concrete subclass signature (~30 classes)
- Render-method contracts (what HTML structure each emits)
- Validator integration contract
- File layout under `src/lexigram/admin/schema/`
- Migration shim API for `forms/fields/`, `ui/columns/`, `ui/filters/`

Review with the team; only proceed after sign-off.

### Task 3.2 — Build `SchemaField` base + first 5 subclasses (1 week)

TDD: write tests for the base class + `TextField`, `NumberField`, `BooleanField`, `DateField`, `SelectField`. Implement until green. These five exercise every render method and validator pattern.

### Task 3.3 — Implement remaining ~25 subclasses (1–2 weeks)

Per-subclass TDD. Group by family:
- Text family (Email, Password, URL, TextArea, Markdown, RichText)
- Numeric family (Integer, Float, Currency)
- Selection family (Enum, MultiSelect, Radio, RelationField, BelongsTo, HasMany, Morph)
- Date/time family (DateTime, Time)
- Composite (JsonField, FileField, ImageField, AvatarField, ColorField, RatingField, TagsField, KeyValueField, HiddenField, ToggleField)

### Task 3.4 — Deprecation shims (3 days)

For each class in `forms/fields/`, `ui/columns/`, `ui/filters/`:
- Add a `DeprecationWarning` on import
- Re-implement as a thin wrapper around the corresponding `SchemaField`
- Document the recommended replacement in the warning message

Add `Resource.fields: list[SchemaField]` as the new declarative path. `Resource.columns`, `Resource.filters`, `form_class` remain accepted but warn.

### Task 3.5 — Migrate internal resources (3 days)

Walk the admin's internal resources (the ones inside admin itself, not external apps). Convert each to `SchemaField` declarations. This validates the API at scale.

### Task 3.6 — Migration documentation (2 days)

Write `docs/MIGRATION_FROM_TRIPLET.md`:
- Old → new mapping table per field type
- Code snippets for common migration patterns
- Tooling script for automated rewrites (if feasible)
- Timeline: when old paths will be removed

### Task 3.7 — Cleanup (deferred to next release)

After one release cycle with deprecation warnings, delete `forms/fields/`, `ui/columns/`, `ui/filters/`. This is **outside this plan's scope** — it lives in the next release's plan.

---

## Phase 4 — Action and Page

**Estimate:** 3–4 weeks single developer
**Risk:** **MEDIUM** — naming collisions during migration; routing layer touched
**Deliverable:** Unified `Action` class; `Page` abstraction with built-in resource pages; internal resources migrated.

### Task 4.1 — Action design freeze (3 days)

Sub-plan: `docs/plans/2026-XX-XX-phase-4-action-page.md`. Decide:
- Final `Action` base class signature
- `RowAction` / `BulkAction` / `HeaderAction` specializations
- `ActionContext` shape (what's available inside `execute()`)
- `ActionOutcome` and `ActionError` types
- Naming-collision migration strategy (old `Action` ABC in `ui/actions/` vs new `Action` in `actions/`)

### Task 4.2 — Action implementation (1 week)

TDD: new `Action`, `RowAction`, `BulkAction`, `HeaderAction` in `src/lexigram/admin/actions/base.py`. Add `ActionContext`, `ActionOutcome`, `ActionError` types.

Migrate one row action (`EditAction`), one bulk action (`BulkDeleteAction`), one header action (`CreateAction`) end-to-end to validate the API.

### Task 4.3 — Action migration shim (3 days)

`ui/actions/EditAction`, `DeleteAction` become aliases. Old `Action` ABC in `ui/actions/__init__.py` gets a careful rename — keep the old name working as a deprecation alias pointing at the new `RowAction` for one release. The naming collision is the risk; the sub-plan handles it explicitly.

### Task 4.4 — Page design freeze (2 days)

Decide:
- Final `Page` base class signature
- Built-in `ListPage`, `CreatePage`, `EditPage`, `ViewPage`
- How Resource declares `pages = [...]` and how defaults apply
- Routing integration: how `AdminRouter` discovers Pages
- Permission integration: `Page.permissions` + RBAC check at routing time

### Task 4.5 — Page implementation (1 week)

TDD: `Page` base, built-in resource pages. Migrate one internal Resource (e.g., the AdminUser resource) end-to-end through Pages. Add `AdminRouter` page-discovery path.

### Task 4.6 — Backward compatibility validation (3 days)

Verify that any existing controller continues to work alongside Pages. Add an integration test that registers both a controller-only route and a Page-based resource simultaneously.

### Task 4.7 — Docs (1 day)

Update `docs/RESOURCES.md` with the Action and Page sections. Cross-link from `docs/ARCHITECTURE.md`.

---

## Phase 5 — Cluster and RelationManager

**Estimate:** 3–4 weeks single developer
**Risk:** **HIGH** (RelationManager) / LOW (Cluster)
**Deliverable:** `Cluster` first-class class; full `RelationManager` with inline create/edit/delete via HTMX.

### Task 5.1 — Cluster (3 days)

Small. Implement `Cluster` per ADR-004:
- Class definition under `src/lexigram/admin/clusters/`
- `AdminConfig.clusters: list[Cluster]` field; `navigation_groups` dict converted at load time with deprecation
- `Resource.cluster: str | None = None`; `Resource.group` aliased
- Navigation builder consumes `Cluster` list
- Tests + docs section

### Task 5.2 — RelationManager design freeze (3 days)

Sub-plan: `docs/plans/2026-XX-XX-phase-5-relation-manager.md`. This is the most complex piece. Decide:
- Whether to extend `AbstractRelationManager` or supersede it
- HTMX zone allocation per relation panel
- Form derivation from `table()` (auto-generate or require explicit `edit_form()`?)
- Permission integration
- How relations appear on `ViewPage` — composition pattern
- Concurrency: two users editing the same related record simultaneously
- The `Result[T, E]` shape for create/edit/delete outcomes

### Task 5.3 — RelationManager core (1–1.5 weeks)

TDD per HTMX cycle:
- GET create form
- POST create → updated panel
- GET edit form (row swap)
- PUT edit → display row
- DELETE confirm + execute
- DETACH (many-to-many only)

Each cycle is a separate test family. The end-to-end test is a fully populated relation panel that walks one full edit cycle.

### Task 5.4 — Wire into ViewPage (3 days)

`Resource.relations: list[type[RelationManager]]`. `ViewPage` renders each manager into its own Zone. Add HTMX route registration for the relation paths under each Resource.

### Task 5.5 — Docs (2 days)

Update `docs/RESOURCES.md` with the RelationManager section. Add walkthroughs.

---

## Phase 6 — IDataSource Enforcement

**Estimate:** 1–2 weeks single developer (parallel with Phases 3–5 by a second developer)
**Risk:** **LOW** — surface area is small; existing implementations are close to the Protocol.
**Deliverable:** `IDataSource` audited and complete; `Resource.fetch_list()` polymorphism removed; existing data sources updated; CI guard test.

### Task 6.1 — Audit (2 days)

Read `IDataSource` at `src/lexigram/admin/data/data_source.py:35`. Compare its surface against what `Resource.fetch_list()` actually uses, what `APIDataSource` implements, and what app data sources are expected to provide. Catalog gaps.

Output: a list of methods to add/refine on the Protocol.

### Task 6.2 — Update Protocol (1 day)

Apply the gaps from 6.1. Add `@runtime_checkable` decorator if not already present. Document each method.

### Task 6.3 — Update implementations (3 days)

`APIDataSource` and any other in-tree implementations must satisfy the audited Protocol. Add tests that verify `isinstance(impl, IDataSource)` for each.

### Task 6.4 — Remove polymorphism in Resource (2 days)

Replace `Resource.fetch_list()` (lines 141–243) with a single typed call to the data source's audited Protocol methods. Resource registration validates `isinstance(data_source, IDataSource)` at boot — failures surface immediately via the strict-mode flag from foundation Task 1.4.

### Task 6.5 — Docs (1 day)

Add `docs/DATA_SOURCES.md` (new) — how to write a custom data source. Cross-link from `RESOURCES.md`.

---

## Phase 7 — Documentation Final Polish

**Estimate:** 2 weeks single developer (some content authored in earlier phases)
**Deliverable:** All six documents complete with content; cross-links wired; stability-tier registry alive.

### Task 7.1 — `docs/ARCHITECTURE.md` (3 days)

Three-ring model (per REVIEW §5). Abstraction overview: Resource, Page, Action, Widget, Cluster, RelationManager, SchemaField. Lifecycle and routing. Result/Exception doctrine.

### Task 7.2 — `docs/RESOURCES.md` (consolidate from Phases 3–5) (3 days)

End-to-end Resource definition walkthrough. Every section is grounded in a real working example.

### Task 7.3 — `docs/CONTRIBUTORS.md` (2 days)

How to write an `AdminContributor`. What contributors can contribute (resources, pages, widgets, navigation, health checks). Examples per category.

### Task 7.4 — `docs/SECURITY.md` (3 days)

RBAC model. Permission inheritance. Audit log. Session management. CSRF. Rate limiting. Security validation in `AdminConfig.validate_for_environment()`.

### Task 7.5 — `docs/FILAMENT_PARITY.md` (2 days)

Concept map for users coming from Filament:
- Filament Resource ↔ Lexigram Resource
- Filament Schema/Form ↔ Lexigram SchemaField
- Filament Table ↔ Lexigram Table (via SchemaField column rendering)
- Filament Filter ↔ Lexigram SchemaField filter rendering
- Filament Action ↔ Lexigram Action
- Filament Page ↔ Lexigram Page
- Filament Widget ↔ Lexigram Widget
- Filament Cluster ↔ Lexigram Cluster
- Filament RelationManager ↔ Lexigram RelationManager

For each pair, note what's the same, what's different, and why.

### Task 7.6 — `docs/PUBLIC_API.md` + stability tiers (3 days)

Every exported symbol from `lexigram.admin` and `lexigram.admin.ui` with a stability tier:
- `@stable` — committed API, breaking changes only in major releases
- `@experimental` — may change without notice
- `@deprecated` — will be removed; includes target removal release

Add the tier annotations as decorators (`@stable`, `@experimental`, `@deprecated(removed_in="0.X")`) so they appear in docs and emit warnings at use time.

---

# Part IV — Risk Register

| ID       | Description                                                                                | Impact | Likelihood | Mitigation                                                                                                                                |
|----------|--------------------------------------------------------------------------------------------|--------|------------|-------------------------------------------------------------------------------------------------------------------------------------------|
| RISK-001 | SchemaField surface is larger than estimated; ~30 subclasses become ~50                    | HIGH   | MEDIUM     | Time-box Phase 3 at 5 weeks; if more types emerge, ship the core 30 and defer the rest as `experimental` with their old shims still active |
| RISK-002 | Action naming collision during migration breaks downstream apps                            | HIGH   | LOW        | The migration shim's deprecation alias **must** keep `from lexigram.admin.ui.actions import Action` working as `RowAction` for one release |
| RISK-003 | Page abstraction collides with custom controllers in downstream apps                       | MEDIUM | LOW        | Controllers continue to work in parallel with Pages indefinitely; Page is opt-in for Resource-style pages                                  |
| RISK-004 | Cluster migration breaks `navigation_groups` consumers                                     | LOW    | LOW        | Convert old dict to `Cluster` list at config load with deprecation warning; one release of overlap                                         |
| RISK-005 | RelationManager HTMX cycle is more complex than the design assumes (concurrency, validation, optimistic updates) | HIGH | MEDIUM | Land create/edit/delete in three separate commits with end-to-end tests per commit; build the panel-level test harness first              |
| RISK-006 | `IDataSource` audit finds the Protocol needs major surgery                                 | MEDIUM | LOW        | The Protocol is already implemented by `APIDataSource`; surgery on the Protocol is bounded by what existing implementations already do    |
| RISK-007 | Docs lag behind implementation; "experimental" abstractions ship without real docs         | MEDIUM | HIGH       | Each phase's exit criteria include the relevant doc section; Phase 7 is final polish, not initial write                                    |
| RISK-008 | Effort estimate of 14–18 weeks is optimistic for one developer                             | MEDIUM | MEDIUM     | Plan for 18 weeks; allocate Phase 6 + Phase 7 in parallel where possible; treat under-running as a bonus, not the baseline                 |
| RISK-009 | Cross-phase regressions — Phase 4 lands and breaks something Phase 3 introduced            | HIGH   | MEDIUM     | CI gate per phase; no Phase N+1 work starts until Phase N's full test suite is green and a release has been cut (or a feature flag set)    |
| RISK-010 | Filament users expect specific patterns that don't translate (e.g., Eloquent magic)        | LOW    | HIGH       | `docs/FILAMENT_PARITY.md` is explicit about what does NOT translate; surface differences as design decisions, not gaps                     |
| RISK-011 | SchemaField render methods produce HTML that doesn't compose with existing layouts         | MEDIUM | MEDIUM     | Each render method test asserts both shape and integration with `lexigram.ui` zones; visual regression tests at the resource level         |
| RISK-012 | Form derivation in RelationManager (auto from `table()`) misses fields users want          | LOW    | MEDIUM     | Auto-derivation is the default; explicit `edit_form()` override always wins. Document the precedence                                       |

---

# Part V — Validation Strategy Across All Phases

Every phase exits when:

1. **CI green** — `uv run ruff check . --fix && uv run mypy lexigram-admin/src/ && uv run pytest lexigram-admin/ --tb=short` passes
2. **Coverage gate** — overall coverage ≥70%, new modules ≥80%
3. **Deprecation warnings clean** — running tests with `-W error::DeprecationWarning` passes (no internal code triggers its own deprecations)
4. **Public-API guard** — `test_public_api.py` (admin's analog) lists every new public symbol; `test_phantom_imports.py` finds zero deep-path imports into ui internals
5. **Docs landed** — the doc section corresponding to this phase exists and renders
6. **Migration story** — for breaking changes, the deprecation shim is in place AND `docs/MIGRATION_*.md` describes the upgrade path

A phase that fails any of the six does not merge.

---

# Part VI — What This Plan Does NOT Cover (Future Work)

- **Deletion of deprecated paths** — `forms/fields/`, `ui/columns/`, `ui/filters/`, old `Action` aliases. These get deleted in a post-evolution cleanup plan after one release cycle of warnings.
- **Filament's enhancement features:** global search across resources, command palette refactor to Resource-aware, multi-tenancy-aware Page routing, Resource cloning, soft-delete UI affordances. Each is a separate plan once the foundation here ships.
- **Performance optimization** — Phase 6 establishes correct data access; performance work (query result caching, partial column hydration, virtual scrolling at scale) is a separate plan with its own benchmarks.
- **Theming + design tokens evolution** — depends on `lexigram-ui` Phase 6 (Livewire/Tailwind/Alpine layering) landing first.
- **Schema-driven OpenAPI** — once `SchemaField` exists, a separate plan can derive admin's REST surface from it. Out of scope here.

---

# Part VII — Glossary

| Term                       | Definition                                                                                                                  |
|----------------------------|-----------------------------------------------------------------------------------------------------------------------------|
| **Resource**               | Declarative artifact defining a model-backed admin entity (fields, actions, pages, permissions, navigation, relations)      |
| **Page**                   | A unit of admin routing — built-in (List/Create/Edit/View) or custom                                                       |
| **SchemaField**            | The single source of truth for a field's type, validation, and three-context rendering                                      |
| **Action**                 | A stateful unit of work against a record (Row), a record selection (Bulk), or no record (Header)                            |
| **Cluster**                | A first-class grouping of resources and pages with shared label/icon/permissions                                            |
| **RelationManager**        | An inline list+edit panel for records related to a parent record on a `ViewPage`                                            |
| **IDataSource**            | The typed Protocol every Resource's data backend must satisfy                                                              |
| **AdminContributor**       | The extension point through which features contribute resources, pages, widgets, navigation entries, and health checks      |
| **AdminBundleProvider**    | The DI provider that registers admin's seven sub-providers and resolves resources/controllers/widgets at boot               |
| **AdminRenderer**          | The single HTML composition point for admin pages (layout, navigation, chrome, theme)                                       |
| **Zone**                   | A named HTMX swap target from `lexigram.ui.core.zones` — admin uses these for relation panels, modal targets, etc.          |

---

# Part VIII — Execution Order Summary

```
Week 1–5    │ Phase 3: SchemaField                 ─┐
Week 4–5    │ Phase 6 (parallel): IDataSource      ─┤── First milestone
Week 6      │ Buffer / phase review                 │
                                                    │
Week 7–10   │ Phase 4: Action + Page                │── Second milestone
Week 11     │ Buffer / phase review                 │
                                                    │
Week 12–15  │ Phase 5: Cluster + RelationManager    │── Third milestone (Filament-parity feature complete)
Week 16     │ Buffer / phase review                 │
                                                    │
Week 16–18  │ Phase 7: Docs final polish            │── Release-candidate
```

If single developer: 18 weeks total.
If two developers (one on Phases 3/4/5, one on Phase 6 and starting Phase 7 doc authoring in parallel): ~12 weeks.

---

# Part IX — Sub-Plan Roadmap

This strategic plan is intentionally above the bite-sized TDD task layer. Each phase below produces its own implementation plan in `docs/plans/`:

| Phase   | Sub-plan path                                                              | Owner ADR  | Status         |
|---------|----------------------------------------------------------------------------|------------|----------------|
| 3       | `lexigram-admin/docs/plans/2026-XX-XX-phase-3-schemafield.md`              | ADR-001    | To be written  |
| 4       | `lexigram-admin/docs/plans/2026-XX-XX-phase-4-action-page.md`              | ADR-002, 003 | To be written |
| 5       | `lexigram-admin/docs/plans/2026-XX-XX-phase-5-cluster-relation-manager.md` | ADR-004, 005 | To be written |
| 6       | `lexigram-admin/docs/plans/2026-XX-XX-phase-6-idatasource.md`              | ADR-006    | To be written  |
| 7       | `lexigram-admin/docs/plans/2026-XX-XX-phase-7-docs.md`                     | ADR-007    | To be written  |

Each sub-plan must:
1. Reference this strategic plan as its parent
2. Reference the relevant ADR
3. Decompose tasks to the 2–5 minute bite-sized step level (per `superpowers:writing-plans`)
4. Be reviewed by the plan-document-reviewer subagent before execution
5. Be executed via `superpowers:subagent-driven-development` or `superpowers:executing-plans`

---

# Appendix A — Filament Concepts Not Adopted

Patterns from Filament that we deliberately do NOT adopt:

| Filament pattern                                  | Why we don't adopt                                                                          |
|---------------------------------------------------|---------------------------------------------------------------------------------------------|
| Eloquent magic / model auto-discovery             | Lexigram is contract-first; explicit field declaration is doctrine                          |
| Livewire-coupled lifecycle (`mount`, `hydrate`, …)| `lexigram-ui`'s HTMX/Alpine model is the substrate; Livewire semantics don't translate     |
| PHP-style trait mixins                            | Stay typed; stay frozen-dataclass; stay Result-based                                       |
| Spatie-style global tenancy scopes                | Admin's `multitenancy/` already scopes via `IDataSource`; doesn't need Eloquent scope ports |
| Action as a builder-fluent chain (`->color()->icon()->visible()->action()`) | Python frozen dataclasses with explicit fields; one expression, clearer typing |
| Resource auto-route generation from Model class   | Routes derive from declared Pages, not from reflecting on the model                         |
| Implicit form generation from migrations          | Forms derive from declared `SchemaField` list                                              |

These are intentional architectural distinctions. They go in `docs/FILAMENT_PARITY.md` so users coming from Filament understand the rationale.

---

# Appendix B — Estimate Validation Against REVIEW

REVIEW (§9) estimated 12–16 weeks for full consolidation (Phases 3–7). This plan revises to **14–18 weeks** based on:

- **Phase 3 upward revision (+1–2 weeks):** REVIEW estimated 3–4 weeks; this plan estimates 3–5. Reason: REVIEW assumed ~15 SchemaField subclasses; reality is closer to 30 once every input/column/filter combination is unified.
- **Phase 5 unchanged (3–4 weeks):** matches REVIEW.
- **Phase 6 (1–2 weeks):** REVIEW didn't separately estimate; this plan accounts for it.
- **Phase 7 (2 weeks):** matches REVIEW's 2-week documentation estimate.
- **Buffer (1 week per major phase):** explicit buffer per phase for cross-phase regression issues, design adjustments after review.

With two developers in parallel (Phase 6 + Phase 7 doc-authoring concurrent with main track), the calendar compresses to **10–12 weeks** — within REVIEW's original window. The 14–18 week single-developer estimate is the safer baseline.
