# Dashboard Widgets

**Goal:** Transform the admin dashboard from a static overview into a living HTMX-driven widget grid where contributor packages render live data via lazy-loaded cards. Add reusable chart components, wire `AutoRefreshWidget` for live updates, and add dashboard zones.

## What Exists

- **`DashboardWidgetDefinition`** — typed widget metadata in `lexigram-contracts`
- **`DashboardAssembler`** — collects widgets from all `AdminContributorProtocol` implementations
- **`WidgetController`** — HTMX route `GET /{contributor_id}/widgets/{widget_name}` that delegates to `contributor.render_widget()`
- **`WidgetRegistry.render_contributor_widgets()`** — renders HTMX card shells with `hx-get`/`hx-trigger="load"` — **NOT wired into DashboardController**
- **`StatCard`, `StatCardGrid`, `ActivityFeed`, `SystemHealthWidget`** — static UI components
- **`AutoRefreshWidget`** — HTMX polling component, NOT wired into dashboard
- **`WidgetSize`** (SMALL/MEDIUM/LARGE/FULL) — size variants defined but not applied
- **Package contributors** — cache, sql, web, auth, events, tasks, queue all provide widget definitions + handlers + templates

## What's Missing

1. **DashboardController uses bare `<h3>` titles** instead of `WidgetRegistry.render_contributor_widgets()` with HTMX lazy-load cards
2. **No dashboard zones** in `Zones` class — `WidgetController` routes use hardcoded IDs
3. **No reusable chart component** — only static StatCards, no bar/line/pie rendering
4. **AutoRefreshWidget not integrated** — widgets can't self-refresh
5. **Widget sizing ignored** — `WidgetSize` defined but DashboardController renders all widgets in uniform grid cells
6. **IWidget registration missing** — `WidgetRegistry` has no registered `IWidget` implementations for contributor widgets

## Plan

### Task A — Dashboard zones + fix DashboardController to use WidgetRegistry (1 day)

Add `DASHBOARD_GRID` and `WIDGET_CONTAINER` zones to `lexigram-ui/core/zones.py`. Modify `DashboardController.index()` to use `WidgetRegistry.render_contributor_widgets()` instead of inline `<h3>` rendering, with proper HTMX lazy loading.

### Task B — ChartWidget component (2 days)

Create `lexigram-admin/src/lexigram/admin/ui/organisms/dashboard/chart_widget.py` with pure-HTML/SVG chart components (no JS dependency):
- `BarChart` — horizontal bar chart using CSS flex + inline styles
- `LineChart` — simple polyline SVG chart
- `PieChart` — CSS conic-gradient pie chart
- `ChartWidget` — wrapper with title, legend, sizing, `AutoRefreshWidget` integration

### Task C — Wire AutoRefreshWidget + widget sizing into dashboard (1 day)

Modify the dashboard grid rendering to:
- Apply `WidgetSize` → CSS grid column spans (SMALL=1, MEDIUM=2, LARGE=3, FULL=4)
- Wrap each widget body in `AutoRefreshWidget` when `refresh_interval_seconds > 0`
- Add `WidgetCard` component that composes `AutoRefreshWidget` + sizing + HTMX lazy-load

### Task D — Register IWidget implementations + verify contributor rendering (1 day)

Create `DefaultStatWidget`, `DefaultChartWidget`, `DefaultHealthWidget` implementations of `IWidget` and register them in `WidgetRegistry`. Verify end-to-end that contributor widgets render as HTMX lazy-load cards on the dashboard.

---

## ADR-008: Why Pure-HTML/SVG Charts

**Status:** Proposed

**Context:** Adding Chart.js or similar would require a new JS dependency, bundle the admin with ~50KB+ of charting library, and add build complexity for Tailwind/Alpine integration.

**Decision:** Use pure CSS/SVG for common chart types (bar, line, pie). These render server-side with no JS dependency, work with HTMX swaps, and cover 90% of admin dashboard use cases (counts, trends, distributions). If advanced charting (interactive zoom, real-time streaming, 3D) is needed later, add Chart.js as an optional dependency.

**Why not Chart.js now:** The framework's admin surface deliberately avoids client-side JS libraries beyond Alpine.js + HTMX. Adding Chart.js would be the first third-party JS dependency, setting a precedent. Pure CSS/SVG is sufficient for stat cards, simple bar charts, trend lines, and pie distributions — the common dashboard widget vocabulary.
