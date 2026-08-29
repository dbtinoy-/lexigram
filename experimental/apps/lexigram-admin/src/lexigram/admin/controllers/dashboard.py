"""Dashboard controller."""

from __future__ import annotations

from collections import defaultdict
import contextvars
from datetime import datetime
from typing import Any

from starlette.requests import Request
from starlette.responses import HTMLResponse

from lexigram.admin.controllers.base import AdminController
from lexigram.admin.dashboard.assembler import DashboardAssembler
from lexigram.admin.dashboard.page_filters import (
    applied_from_query,
    read_page_filters,
    render_page_filter_form,
    save_page_filters,
)
from lexigram.admin.dashboard.widgets import WidgetRegistry
from lexigram.admin.engine.renderer import AdminRenderer
from lexigram.contracts.admin.types import PageFilterField, WidgetSize
from lexigram.contracts.web import get
from lexigram.di.decorators import inject
from lexigram.ui import el

# Request-scoped in-memory dict, isolated per async context.
_request_cache_var: contextvars.ContextVar[dict[str, Any] | None] = (
    contextvars.ContextVar(
        "admin_request_cache",
        default=None,
    )
)


def _get_request_cache() -> dict[str, Any]:
    """Return the request-scoped cache dict for the current async context."""
    cache = _request_cache_var.get()
    return cache if cache is not None else {}


@inject
class DashboardController(AdminController):
    """Controller for managing and viewing dashboards."""

    prefix = ""

    # Declared page-level filter schema (Filament HasFiltersForm parity).
    # Subclass to declare filters; the dashboard renders an apply/reset bar
    # and propagates the values to widget fetch URLs.
    page_filters: list[PageFilterField] = []

    def __init__(
        self,
        renderer: AdminRenderer,
        assembler: DashboardAssembler | None = None,
        widget_registry: WidgetRegistry | None = None,
    ):
        super().__init__(renderer)
        self.assembler = assembler
        self.widget_registry = widget_registry
        self._settings_service: Any = None

    def _size_to_grid_cols(self, size: WidgetSize) -> int:
        """Map WidgetSize to CSS grid column span."""
        mapping = {
            WidgetSize.SMALL: 1,
            WidgetSize.MEDIUM: 2,
            WidgetSize.LARGE: 3,
            WidgetSize.FULL: 4,
        }
        return mapping.get(size, 1)

    @get("/")
    async def index(self, request: Request) -> HTMLResponse:
        """Render the main dashboard overview."""
        from lexigram.admin.ui.organisms.dashboard.widgets import (
            ActivityFeed,
            ActivityItem,
            HealthEntry,
            Stat,
            StatCardGrid,
            SystemHealthWidget,
        )
        from lexigram.ui.core.base import raw

        dashboard_id = request.query_params.get("id", "default")

        # Page-level filter state: schema defaults → session → query params
        filter_state: dict[str, Any] = {}
        if self.page_filters:
            filter_state = read_page_filters(request, "dashboard", self.page_filters)
            if applied_from_query(request, self.page_filters):
                save_page_filters(request, "dashboard", filter_state)

        breadcrumbs = self.generate_breadcrumbs(
            ("Home", "/admin/"),
            current="Dashboard",
        )

        # Use assembler widgets when available; fall back to default overview
        if self.assembler:
            user = getattr(getattr(request, "state", None), "user", None)
            contributor_widgets = list(await self.assembler.get_all_widgets(user=user))
        else:
            contributor_widgets = []

        # Load user preferences for widget visibility and ordering
        widget_prefs = (
            await self._settings_service.get_widget_prefs("default", "default")
            if self._settings_service
            else {}
        )
        # Filter and sort widgets. No saved prefs means everything is on.
        if "enabled" in widget_prefs:
            enabled_set = set(widget_prefs["enabled"])
            contributor_widgets = [
                w for w in contributor_widgets if w.name in enabled_set
            ]
        custom_order = widget_prefs.get("order", {})
        if custom_order:
            contributor_widgets.sort(key=lambda w: custom_order.get(w.name, w.order))

        if contributor_widgets and self.widget_registry:
            # Render HTMX lazy-load widget cards via the registry, annotating
            # each fetch URL with the current page filter values
            rendered_html = self.widget_registry.render_contributor_widgets(
                contributor_widgets,
                page_filters=filter_state,
            )
            widgets_section = el(
                "div",
                raw(rendered_html),
                id="dashboard-grid",
                class_="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4",
            )
        elif contributor_widgets and not self.widget_registry:
            # Fallback: basic title rendering when no registry is available
            rendered_widgets: list[Any] = []
            for w in contributor_widgets:
                rendered_widgets.append(
                    el(
                        "div",
                        el("h3", w.title, class_="font-semibold"),
                        class_="bg-card rounded-lg p-4 shadow",
                    )
                )
            widgets_section = el(
                "div",
                *rendered_widgets,
                class_="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4",
            )
        else:
            # Provide a beautiful default overview dashboard
            default_stats = [
                Stat(
                    label="Resources",
                    value=str(len(self._get_resource_list(request))),
                    icon="layers",
                    color="blue",
                    description="Registered admin resources",
                ),
                Stat(
                    label="Active Now",
                    value="—",
                    icon="users",
                    color="green",
                    description="Live sessions",
                ),
                Stat(
                    label="Actions Today",
                    value="—",
                    icon="zap",
                    color="primary",
                    description="Admin operations today",
                ),
                Stat(
                    label="Errors (24h)",
                    value="—",
                    icon="alert-triangle",
                    color="red",
                    description="Last 24 hours",
                ),
            ]
            default_activity: list[ActivityItem] = []
            default_health = [
                HealthEntry(name="Admin API", status="ok"),
            ]

            from lexigram.admin.dashboard.chart_widget import ChartWidget
            from lexigram.admin.resources.urls import admin_prefix_from_request
            from lexigram.ui import ChartType

            resources_chart = ChartWidget(
                title="Registered Resources",
                chart_type=ChartType.BAR,
                data_source=(
                    f"{admin_prefix_from_request(request)}/widgets/resources"
                ),
                description=(
                    "Every admin resource registered with this application."
                ),
                col_span=3,
                refresh_interval=120,
            )
            chart_row = el(
                "div",
                resources_chart,
                class_="grid grid-cols-1 lg:grid-cols-3 gap-4",
            )

            bottom_row = el(
                "div",
                el(
                    "div",
                    ActivityFeed(default_activity, title="Recent Activity"),
                    class_="lg:col-span-2",
                ),
                SystemHealthWidget(default_health),
                class_="grid grid-cols-1 lg:grid-cols-3 gap-4",
            )
            widgets_section = el(
                "div",
                StatCardGrid(default_stats, cols=4),
                chart_row,
                bottom_row,
                class_="space-y-6",
            )

        # SortableJS drag-and-drop controls + widget config helpers
        dnd_html = raw("""
<div id="dashboard-dnd-controls" class="mt-4 text-center">
  <button id="save-layout-btn"
          class="hidden bg-primary text-primary-foreground px-4 py-2 rounded hover:bg-primary/90 text-sm">
    💾 Save Layout
  </button>
</div>
<script>
(function() {
  var grid = document.getElementById('dashboard-grid');
  var saveBtn = document.getElementById('save-layout-btn');
  var sortableInstance = null;

  function initSortable() {
    grid = document.getElementById('dashboard-grid');
    if (!grid || sortableInstance || typeof Sortable === 'undefined') return;
    sortableInstance = new Sortable(grid, {
      animation: 150,
      handle: '.widget-card',
      onEnd: function() {
        saveBtn.classList.remove('hidden');
      }
    });
  }

  initSortable();
  if (!window.__adminDashboardListeners) {
    window.__adminDashboardListeners = 1;
    document.body.addEventListener('htmx:afterSwap', initSortable);
    document.body.addEventListener('htmx:afterSwap', function(e) {
      var t = e.detail && e.detail.target;
      if (t && window.htmx) { try { htmx.process(t); } catch (err) {} }
    });
  }

  if (saveBtn) {
    saveBtn.addEventListener('click', async function() {
      if (!sortableInstance) return;
      var order = Array.from(grid.querySelectorAll('.widget-card')).map(function(card) {
        return card.dataset.widgetName;
      });
      try {
        var resp = await fetch('/admin/core/widgets/reorder', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({order: order})
        });
        if (resp.ok) {
          saveBtn.classList.add('hidden');
          saveBtn.textContent = '✅ Saved!';
          setTimeout(function() { saveBtn.textContent = '💾 Save Layout'; }, 2000);
        }
      } catch(e) {}
    });
  }
})();
</script>
""")

        customize_btn = el(
            "button",
            "⚙ Customize Dashboard",
            **{
                "hx-get": "/admin/core/widgets/customize",
                "hx-target": "#slide-over-container",
                "hx-swap": "innerHTML",
                "hx-push-url": "false",
            },
            class_="text-sm bg-muted hover:bg-muted px-3 py-1.5 rounded border border-border cursor-pointer",
        )

        filter_form = (
            render_page_filter_form(self.page_filters, filter_state, "/admin/")
            if self.page_filters
            else None
        )

        content = el(
            "div",
            el(
                "div",
                el(
                    "h2",
                    dashboard_id,
                    class_="text-2xl font-bold text-foreground",
                ),
                customize_btn,
                class_="flex items-center justify-between",
            ),
            filter_form,
            widgets_section,
            dnd_html,
            class_="dashboard-view space-y-6",
        )

        return await self._render_with_flash(
            request, content, f"Dashboard: {dashboard_id}", breadcrumbs
        )

    @get("/widgets/resources")
    async def resources_chart(self, request: Request) -> HTMLResponse:
        """Render the registered-resources bar chart fragment.

        HTMX target for the default dashboard's ``ChartWidget``.  Returns an
        empty state when no resources are registered so the card body never
        renders a blank canvas.
        """
        from lexigram.admin.dashboard.content_renderer import render_chart_fragment
        from lexigram.contracts.admin.widget_content import ChartPoint
        from lexigram.ui import EmptyState, render_to_string

        resources = self._get_resource_list(request)
        if not resources:
            return HTMLResponse(
                render_to_string(
                    EmptyState(
                        title="No resources",
                        message="No admin resources are registered yet.",
                    )
                )
            )

        points = [ChartPoint(label=name, value=1) for name in resources]
        return HTMLResponse(render_chart_fragment("bar", points))

    @get("/widgets/stats")
    async def overview_stats(self, request: Request) -> HTMLResponse:
        """Render the default dashboard stat-grid fragment.

        HTMX target for ``StatsOverviewWidget(data_source=...)`` cards: the
        default overview's four headline stats, served through the shared
        content dispatcher so tone/delta rendering stays consistent with
        contributor-supplied stats.
        """
        from lexigram.admin.dashboard.content_renderer import render_stat_fragment
        from lexigram.contracts.admin.widget_content import Stat, Tone

        resources = self._get_resource_list(request)
        stats = [
            Stat(label="Resources", value=str(len(resources)), tone=Tone.PRIMARY),
            Stat(label="Active Now", value="—", tone=Tone.DEFAULT),
            Stat(label="Actions Today", value="—", tone=Tone.DEFAULT),
            Stat(label="Errors (24h)", value="—", tone=Tone.DEFAULT),
        ]
        return HTMLResponse(render_stat_fragment(stats))

    async def _render_with_flash(
        self,
        request: Request,
        content: Any,
        title: str,
        breadcrumbs: list[dict[str, Any]] | None,
    ) -> HTMLResponse:
        """Render the dashboard inside an admin context so flash messages
        (e.g. the sign-in toast) are consumed by the shell."""
        from lexigram.admin.state.context import AdminContextManager

        async with AdminContextManager(request):
            return await self.render_admin(
                request,
                content,
                title=title,
                breadcrumbs=breadcrumbs,
            )

    def _get_resource_list(self, request: Request) -> list[str]:
        """Return a list of registered resource names from app state."""
        try:
            app = request.app
            return sorted(getattr(app.state, "admin_resources", {}).keys())
        except Exception:  # noqa: BLE001
            return []

    # MetricProtocol aggregation helpers with caching

    def get_request_cache(self, request: Request) -> dict[str, Any]:
        """
        Get request-scoped cache.

        Returns the context-var-backed cache dict for the current request.
        The cache is isolated per async context — no shared state between
        concurrent requests.
        """
        return _get_request_cache()

    async def aggregate_metric(
        self,
        request: Request,
        metric_name: str,
        compute_func: Any,
        use_request_cache: bool = True,
    ) -> Any:
        """
        Aggregate metric with automatic caching.

        Args:
            request: Current request
            metric_name: Name of the metric
            compute_func: Async callable to compute metric value
            use_request_cache: Use request-scoped cache (default: True)

        Returns:
            Computed or cached metric value

        Example:
            ```python
            total_users = await self.aggregate_metric(
                request,
                "total_users",
                lambda: db.execute("SELECT COUNT(*) FROM users")
            )
            ```
        """
        if use_request_cache:
            cache = self.get_request_cache(request)
            key = f"metric:{metric_name}"
            if key not in cache:
                cache[key] = await compute_func()
            return cache[key]
        return await compute_func()

    # Time-series helpers

    def format_time_series(
        self,
        data: list[tuple[datetime, float]],
        interval: str = "hour",
    ) -> list[dict[str, Any]]:
        """
        Format time-series data for charting libraries.

        Args:
            data: List of (timestamp, value) tuples
            interval: Time interval ('hour', 'day', 'week', 'month')

        Returns:
            Formatted data for charting (Chart.js compatible)

        Example:
            ```python
            raw_data = [(datetime(2024, 1, 1, 10), 42.0), ...]
            chart_data = self.format_time_series(raw_data, interval='day')
            ```
        """
        return [
            {
                "timestamp": ts.isoformat(),
                "value": value,
                "label": self._format_timestamp_label(ts, interval),
            }
            for ts, value in data
        ]

    def _format_timestamp_label(self, ts: datetime, interval: str) -> str:
        """Format timestamp for display based on interval."""
        if interval == "hour":
            return ts.strftime("%H:%M")
        if interval == "day":
            return ts.strftime("%Y-%m-%d")
        if interval == "week":
            return f"Week {ts.isocalendar()[1]}, {ts.year}"
        if interval == "month":
            return ts.strftime("%b %Y")
        return ts.isoformat()

    def aggregate_time_series(
        self,
        data: list[tuple[datetime, float]],
        interval: str = "hour",
    ) -> list[tuple[datetime, float]]:
        """
        Aggregate time-series data into intervals.

        Groups data points by time interval and sums/averages values.

        Args:
            data: List of (timestamp, value) tuples
            interval: Aggregation interval ('hour', 'day', 'week', 'month')

        Returns:
            Aggregated time-series data
        """
        buckets: dict[str, list[float]] = defaultdict(list)

        for ts, value in data:
            bucket_key = self._get_bucket_key(ts, interval)
            buckets[bucket_key].append(value)

        # Compute average for each bucket
        result: list[tuple[datetime, float]] = []
        for key, values in sorted(buckets.items()):
            avg_value = sum(values) / len(values)
            # Parse bucket key back to datetime
            bucket_ts = self._parse_bucket_key(key, interval)
            result.append((bucket_ts, avg_value))

        return result

    def _get_bucket_key(self, ts: datetime, interval: str) -> str:
        """Generate bucket key for timestamp."""
        if interval == "hour":
            return ts.strftime("%Y-%m-%d %H:00")
        if interval == "day":
            return ts.strftime("%Y-%m-%d")
        if interval == "week":
            iso_year, iso_week, _ = ts.isocalendar()
            return f"{iso_year}-W{iso_week:02d}"
        if interval == "month":
            return ts.strftime("%Y-%m")
        return ts.isoformat()

    def _parse_bucket_key(self, key: str, interval: str) -> datetime:
        """Parse bucket key back to datetime."""
        if interval == "hour":
            return datetime.strptime(key, "%Y-%m-%d %H:00")
        if interval == "day":
            return datetime.strptime(key, "%Y-%m-%d")
        if interval == "week":
            year, week = key.split("-W")
            # ISO week to datetime
            return datetime.strptime(f"{year} {week} 1", "%Y %W %w")
        if interval == "month":
            return datetime.strptime(key, "%Y-%m")
        return datetime.fromisoformat(key)
