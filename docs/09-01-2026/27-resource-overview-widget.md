# 27 — R31: Resource Overview dashboard widget (live per-resource record counts)

## 1. Problem

The admin dashboard renders four core contributor widgets (Framework Health,
Framework Metrics, Live Events, Recent Activity), but **none of them tells the
operator anything about their own data**: there is no per-resource record
count anywhere on the dashboard. The only stat-card path that mentions
resources is the *fallback* "default overview" branch in
`controllers/dashboard.py`, which renders a "Resources" count plus three
literal `—` placeholders — and that branch is dead whenever any contributor
registers widgets (i.e. always, since the core contributor is built in).

A professional admin tool's landing page answers "how much data do I have?"
at a glance (Django admin index, Filament stats overview, Laravel Nova
metrics). We already have every building block:

- `WidgetKind.STAT` + `StatContent`/`Stat` contracts and a working renderer
  (`dashboard/content_renderer.py:_render_stat_content`).
- `WidgetCategory.RESOURCES` — defined in contracts, **never used anywhere**.
- Mounted resource instances with wired data sources in `ctx.resources`
  (mount pipeline), each countable via `IDataSource.count(QuerySpec)`.
- An HTMX lazy-load widget pipeline (`{prefix}/core/widgets/{name}` →
  `CoreAdminContributor.render_widget`) with fail-soft error cards.

What is missing is only the *bridge*: contributors have no access to the
mounted resource instances (they receive the DI container at boot, but
resources are materialized later, at mount time, in `MountContext`).

## 2. Design

### 2.1 `ResourceInventory` (new: `dashboard/resource_inventory.py`)

A small read-model over the mounted resources dict, designed as a long-term
shared surface (future widgets/pages can reuse it):

- `ResourceCount` frozen dataclass: `name`, `label`, `icon`,
  `count: int | None` (`None` = unavailable → rendered as `—`).
- `ResourceInventory(resources: Mapping[str, Any])` — holds a **reference**
  to the live `ctx.resources` mapping (resources wired later in the mount
  are visible without re-wiring).
- `async snapshot(limit: int = 8) -> tuple[ResourceCount, ...]`:
  - iterates resources in mount order (matches sidebar order), capped at
    `limit`;
  - label preference: `meta.label_plural` → `resource.label` → titled name;
  - icon: `resource.icon` (default `box`, same default as the nav builder);
  - count: `get_resource_data_source(resource)` (the canonical accessor,
    normalizes `_data_source` / `get_data_source()` / legacy services), then
    `await ds.count(QuerySpec(per_page=1))`; if the source lacks `count`,
    fall back to `find_many(QuerySpec(page=1, per_page=1)).total`;
  - **fail-soft per resource**: any exception → `count=None`, one debug log,
    the other stats still render. No exception ever escapes `snapshot()`.

### 2.2 Mount wiring (`di/mount/contributors.py`)

At the end of `_mount_contributors` (after all data-source/search wiring),
build one `ResourceInventory(ctx.resources)` and push it to every contributor
exposing a `set_resource_inventory(inventory)` hook (duck-typed — any
third-party contributor can opt in, keeping the contracts package untouched).
Log `admin.resource_inventory_wired` with the contributor count. Best-effort:
wiring failure is logged, never aborts the mount.

### 2.3 Core widget (`contributors/core.py`)

- `__init__`: `self._resource_inventory = None`; new
  `set_resource_inventory()` setter.
- `get_dashboard_widgets()` adds:
  `DashboardWidgetDefinition(name="resources", title="Resource Overview",
  contributor="core", render_endpoint=…/core/widgets/resources,
  size=FULL, category=WidgetCategory.RESOURCES, view_kind=WidgetKind.STAT,
  refresh_interval_seconds=60, order=10, icon="database",
  description="Live record counts for each registered resource.")`.
- `render_widget("resources", …)`:
  - no inventory or empty inventory → `_empty("Resource overview",
    "No resources registered.")` (same unavailable-state pattern as health);
  - else `snapshot()` → `StatContent(stats=(Stat(label, value, icon), …))`
    with `value = f"{count:,}"` or `—` when count is `None`.

Assembler sorting is `(category.value, order)`; `resources` (category value
`"resources"`) lands between `metrics` and the fallback ordering naturally —
no dashboard-side changes required. Widget prefs, config popup, refresh and
error-card behavior all come for free from the existing pipeline.

### 2.4 Explicitly out of scope

- Per-user, per-resource permission filtering inside the widget: the
  fragment renderer does not pass the authenticated user into
  `render_widget` (contract limitation, `WidgetParams` has no user). The
  widget exposes aggregate counts only; hosts can gate the whole widget via
  `DashboardWidgetDefinition.permission` if needed.
- Sparkline/delta trends (`Stat.sparkline_data`) — needs a time-series
  store; future work.
- The playground "Live Events" loading state (SSE contributor lives outside
  the admin package).

## 3. Implementation steps

1. `src/lexigram/admin/dashboard/resource_inventory.py` — new module.
2. `src/lexigram/admin/di/mount/contributors.py` — wire inventory at end of
   `_mount_contributors`.
3. `src/lexigram/admin/contributors/core.py` — setter + widget definition +
   render branch.
4. Tests:
   - `tests/unit/dashboard/test_resource_inventory.py` — snapshot counts,
     label/icon fallbacks, `count()` fallback to `find_many().total`,
     per-resource fail-soft, limit cap, live-mapping semantics.
   - extend `tests/unit/contributors/test_core_builtin_contributor.py` —
     definition present (category RESOURCES, kind STAT), render with stub
     inventory → StatContent with formatted values, no inventory →
     EmptyContent.
5. Live playground verify: dashboard shows "Resource Overview" card with
   real counts (products = 20 from the seeded playground).
6. Fill §4, README index row, commit + push (PR #26 stays unmerged).

## 4. Verification

- Unit: `tests/unit/dashboard/test_resource_inventory.py` — **10/10 passed**
  (counts via `count()`, total fallback for count-less sources through the
  legacy adapter, label preference `meta.label_plural` → `label` → titled
  name, icon default `box`, fail-soft on raising sources → `count=None`,
  resources without a data source included as unavailable, limit cap +
  mount-order preservation, live-mapping semantics — resources added after
  construction are visible, empty inventory, negative limit).
- Unit: `test_core_builtin_contributor.py` extended (+4) — **12/12 passed**
  (definition present with `view_kind=STAT`, `category=RESOURCES`, endpoint
  `…/core/widgets/resources`, title "Resource Overview"; render with stub
  inventory → StatContent with `1,234`-formatted values, per-stat icons, and
  `—` for a broken source; EmptyContent both when no inventory is wired and
  when the inventory is empty). Note: content dataclasses carry no `kind`
  attribute (kind lives on the widget definition) — asserted via isinstance.
- Full admin unit suite: **5570 passed / 7 skipped** (was 5556/7; +14, no
  regressions), coverage 76.84%.
- Live playground loop (serve.py restarted with new code, fresh login):
  - Mount log: `admin.resource_inventory_wired contributors=1 resources=2`.
  - `GET /admin/core/widgets/resources` → 200, stat grid with
    **Products 20** and **Customers 10**.
  - `GET /admin/` → 200; "Resource Overview" card present in the dashboard
    grid (5 occurrences: card title + config popup metadata, same pattern as
    the other core widgets), fragment endpoint referenced twice
    (lazy-load + refresh).
  - Cross-check against list pages: products "Showing 1 to 10 of **20**
    results", customers "of **10** results" — widget counts match exactly.
    (Playground products/customers are in-memory seeded sources, so the
    check was done via the admin list pages, not SQLite.)
- Known limits: counts are aggregate (no per-user row-level filtering — see
  §2.4); widget refreshes every 60s via the standard HTMX refresh pipeline;
  snapshot caps at 8 resources by default.
