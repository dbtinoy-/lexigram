"""Chart Factory Service - DI-injectable chart generation."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from html import escape
from typing import Any, Protocol

from lexigram.di.decorators import inject
from lexigram.ui import js_json, js_string


class ChartBackend(StrEnum):
    """Supported chart rendering backends."""

    CHARTJS = "chartjs"
    PLOTLY = "plotly"


class ChartType(StrEnum):
    """Supported chart types."""

    LINE = "line"
    BAR = "bar"
    PIE = "pie"
    SCATTER = "scatter"
    AREA = "area"
    DONUT = "donut"


@dataclass
class ChartData:
    """Chart data structure."""

    labels: list[str] = field(default_factory=list)
    datasets: list[dict[str, Any]] = field(default_factory=list)
    title: str = ""
    x_label: str = ""
    y_label: str = ""


class IChartRenderer(Protocol):
    """Protocol for chart renderers."""

    def render(self, chart_type: ChartType, data: ChartData, **options) -> str:
        """Render chart as HTML/JS."""
        ...


class ChartJSRenderer:
    """Chart.js backend renderer."""

    def render(self, chart_type: ChartType, data: ChartData, **options) -> str:
        """Render Chart.js chart."""

        chart_id = options.get("id", "chart")
        width = options.get("width", "100%")
        height = options.get("height", "400px")

        config = {
            "type": chart_type.value,
            "data": {"labels": data.labels, "datasets": data.datasets},
            "options": {
                "responsive": True,
                "maintainAspectRatio": False,
                "plugins": {
                    "title": {"display": bool(data.title), "text": data.title},
                    "legend": {"display": True},
                },
                "scales": {
                    "x": {
                        "title": {"display": bool(data.x_label), "text": data.x_label},
                    },
                    "y": {
                        "title": {"display": bool(data.y_label), "text": data.y_label},
                    },
                },
            },
        }

        # js_json rather than a plain JSON dump: chart labels and titles are
        # caller data, and a label containing "</script>" ends the block for
        # the HTML tokenizer regardless of JSON quoting.
        config_json = js_json(config)

        return f"""
        <div style="width: {escape(str(width), quote=True)}; height: {escape(str(height), quote=True)};">
            <canvas id="{escape(str(chart_id), quote=True)}"></canvas>
        </div>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <script>
            (function() {{
                const ctx = document.getElementById({js_string(chart_id)}).getContext('2d');
                new Chart(ctx, {config_json});
            }})();
        </script>
        """


class PlotlyRenderer:
    """Plotly backend renderer."""

    def render(self, chart_type: ChartType, data: ChartData, **options) -> str:
        """Render Plotly chart."""

        chart_id = options.get("id", "chart")
        width = options.get("width", "100%")
        height = options.get("height", "400px")

        # Convert to Plotly format
        plotly_data = []
        for dataset in data.datasets:
            trace = {
                "x": data.labels,
                "y": dataset.get("data", []),
                "name": dataset.get("label", ""),
                "type": chart_type.value if chart_type != ChartType.DONUT else "pie",
            }
            if chart_type == ChartType.DONUT:
                trace["hole"] = 0.4
            plotly_data.append(trace)

        layout = {
            "title": data.title,
            "xaxis": {"title": data.x_label},
            "yaxis": {"title": data.y_label},
            "autosize": True,
        }

        data_json = js_json(plotly_data)
        layout_json = js_json(layout)

        return f"""
        <div id="{escape(str(chart_id), quote=True)}" style="width: {escape(str(width), quote=True)}; height: {escape(str(height), quote=True)};"></div>
        <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
        <script>
            Plotly.newPlot({js_string(chart_id)}, {data_json}, {layout_json}, {{responsive: true}});
        </script>
        """


@inject
class ChartFactory:
    """DI-injectable chart factory service."""

    def __init__(self, backend: ChartBackend = ChartBackend.CHARTJS):
        """Initialize chart factory with backend."""
        self.backend = backend
        self._renderers: dict[ChartBackend, IChartRenderer] = {
            ChartBackend.CHARTJS: ChartJSRenderer(),
            ChartBackend.PLOTLY: PlotlyRenderer(),
        }

    def set_backend(self, backend: ChartBackend) -> None:
        """Change rendering backend."""
        self.backend = backend

    def create_chart(
        self,
        chart_type: ChartType,
        data: ChartData,
        backend: ChartBackend | None = None,
        **options,
    ) -> str:
        """Create a chart with specified type and data."""
        renderer_backend = backend or self.backend
        renderer = self._renderers.get(renderer_backend)

        if not renderer:
            raise ValueError(f"Unsupported backend: {renderer_backend}")

        return renderer.render(chart_type, data, **options)

    def line_chart(self, data: ChartData, **options) -> str:
        """Create a line chart."""
        return self.create_chart(ChartType.LINE, data, **options)

    def bar_chart(self, data: ChartData, **options) -> str:
        """Create a bar chart."""
        return self.create_chart(ChartType.BAR, data, **options)

    def pie_chart(self, data: ChartData, **options) -> str:
        """Create a pie chart."""
        return self.create_chart(ChartType.PIE, data, **options)

    def scatter_chart(self, data: ChartData, **options) -> str:
        """Create a scatter chart."""
        return self.create_chart(ChartType.SCATTER, data, **options)

    def area_chart(self, data: ChartData, **options) -> str:
        """Create an area chart."""
        return self.create_chart(ChartType.AREA, data, **options)

    def donut_chart(self, data: ChartData, **options) -> str:
        """Create a donut chart."""
        return self.create_chart(ChartType.DONUT, data, **options)
