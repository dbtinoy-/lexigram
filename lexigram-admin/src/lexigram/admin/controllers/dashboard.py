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
from lexigram.admin.dashboard.widgets import WidgetRegistry
from lexigram.admin.engine.renderer import AdminRenderer
from lexigram.contracts.admin.types import WidgetSize
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

        breadcrumbs = self.generate_breadcrumbs(
            ("Home", "/admin/"),
            current="Dashboard",
        )

        # Use assembler widgets when available; fall back to default overview
        if self.assembler:
            contributor_widgets = list(await self.assembler.get_all_widgets())
        else:
            contributor_widgets = []

        # Load user preferences for widget visibility and ordering
        widget_prefs = (
            await self._settings_service.get_widget_prefs("default", "default")
            if self._settings_service
            else {}
        )
        enabled_set = set(widget_prefs.get("enabled", []))
        custom_order = widget_prefs.get("order", {})

        # Filter and sort widgets
        if enabled_set:
            contributor_widgets = [
                w for w in contributor_widgets if w.name in enabled_set
            ]
        if custom_order:
            contributor_widgets.sort(key=lambda w: custom_order.get(w.name, w.order))

        if contributor_widgets and self.widget_registry:
            # Render HTMX lazy-load widget cards via the registry
            rendered_html = self.widget_registry.render_contributor_widgets(
                contributor_widgets,
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
                        class_="bg-white dark:bg-gray-800 rounded-lg p-4 shadow",
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
                bottom_row,
                class_="space-y-6",
            )

        # SortableJS drag-and-drop controls + widget config helpers
        dnd_html = raw("""
<div id="dashboard-dnd-controls" class="mt-4 text-center">
  <button id="save-layout-btn"
          class="hidden bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 text-sm">
    💾 Save Layout
  </button>
</div>
<script>
function openWidgetConfig(url) {
  fetch(url)
    .then(function(r) { return r.text(); })
    .then(function(html) {
      var d = document.getElementById('widget-config-dialog');
      if (d) { d.innerHTML = html; d.showModal(); }
    });
}

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
  document.body.addEventListener('htmx:afterSwap', initSortable);

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
            onclick="openWidgetConfig('/admin/core/widgets/customize')",
            class_="text-sm bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 px-3 py-1.5 rounded border border-gray-300 dark:border-gray-600 cursor-pointer",
        )

        config_dialog = el(
            "dialog",
            id="widget-config-dialog",
            class_="rounded shadow-lg border p-0 min-w-[400px] max-w-lg",
        )

        content = el(
            "div",
            el(
                "div",
                el(
                    "h2",
                    dashboard_id,
                    class_="text-2xl font-bold text-gray-900 dark:text-white",
                ),
                customize_btn,
                class_="flex items-center justify-between",
            ),
            widgets_section,
            dnd_html,
            config_dialog,
            class_="dashboard-view space-y-6",
        )

        return await self.render_admin(
            request,
            content,
            title=f"Dashboard: {dashboard_id}",
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
