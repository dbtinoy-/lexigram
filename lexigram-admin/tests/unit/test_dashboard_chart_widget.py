from __future__ import annotations

from lexigram.admin.dashboard.chart_widget import ChartWidget
from lexigram.admin.dashboard.widget_types import ConfigField
from lexigram.ui.charts.types import ChartConfig, ChartDataPoint, ChartType


class TestChartWidget:
    def test_renders_title(self) -> None:
        widget = ChartWidget("Sales", ChartType.BAR, [ChartDataPoint("A", 10)])
        html = str(widget.render())
        assert "Sales" in html

    def test_renders_description(self) -> None:
        widget = ChartWidget("Sales", ChartType.BAR, [], description="Monthly data")
        html = str(widget.render())
        assert "Monthly data" in html

    def test_empty_data_no_source(self) -> None:
        widget = ChartWidget("Sales", ChartType.BAR, [])
        html = str(widget.render())
        assert "No data" in html

    def test_empty_data_with_source_shows_skeleton(self) -> None:
        widget = ChartWidget("Sales", ChartType.BAR, [], data_source="/api/chart")
        html = str(widget.render())
        assert "hx-get" in html
        assert "animate-pulse" in html

    def test_col_span_class(self) -> None:
        widget = ChartWidget("Sales", ChartType.BAR, [], col_span=2)
        html = str(widget.render())
        assert "lg:col-span-2" in html

    def test_col_span_1_no_class(self) -> None:
        widget = ChartWidget("Sales", ChartType.BAR, [], col_span=1)
        html = str(widget.render())
        assert "lg:col-span" not in html

    def test_refresh_interval_adds_trigger(self) -> None:
        widget = ChartWidget("Sales", ChartType.BAR, [], data_source="/api/chart", refresh_interval=30)
        html = str(widget.render())
        assert "hx-trigger" in html
        assert "every" in html


class TestChartWidgetFilters:
    def test_renders_select_filter(self) -> None:
        widget = ChartWidget(
            "Sales",
            ChartType.BAR,
            [],
            data_source="/api/chart",
            filters=[
                ConfigField(
                    name="period",
                    type="select",
                    label="Period",
                    options=[("30d", "Last 30 days"), ("90d", "Last 90 days")],
                    default="30d",
                ),
            ],
        )
        html = str(widget.render())
        assert '<form class="chart-filters' in html
        assert 'name="period"' in html
        assert "<select" in html
        assert '<option value="30d" selected>Last 30 days</option>' in html
        assert '<option value="90d"' in html

    def test_renders_number_and_boolean_filters(self) -> None:
        widget = ChartWidget(
            "Sales",
            ChartType.BAR,
            [],
            filters=[
                ConfigField(name="min", type="number", label="Min", default=5),
                ConfigField(name="active", type="boolean", label="Active"),
            ],
        )
        html = str(widget.render())
        assert 'type="number"' in html
        assert 'value="5"' in html
        assert 'type="checkbox"' in html

    def test_text_filters_label_rendered(self) -> None:
        widget = ChartWidget(
            "Sales",
            ChartType.BAR,
            [],
            filters=[ConfigField(name="q", type="text", label="Search")],
        )
        html = str(widget.render())
        assert 'name="q"' in html
        assert "Search" in html

    def test_filter_change_refetches_data_source(self) -> None:
        widget = ChartWidget(
            "Sales",
            ChartType.BAR,
            [],
            data_source="/api/chart",
            filters=[ConfigField(name="period", type="select", label="Period")],
        )
        html = str(widget.render())
        assert 'hx-get="/api/chart"' in html
        assert 'hx-trigger="change"' in html
        assert 'hx-target="#chart-body-' in html
        assert 'hx-swap="innerHTML"' in html

    def test_filters_suppress_poll_trigger(self) -> None:
        widget = ChartWidget(
            "Sales",
            ChartType.BAR,
            [],
            data_source="/api/chart",
            refresh_interval=30,
            filters=[ConfigField(name="period", type="select", label="Period")],
        )
        html = str(widget.render())
        assert 'hx-trigger="load"' in html
        assert "every" not in html

    def test_body_targeted_by_load_trigger(self) -> None:
        widget = ChartWidget("Sales", ChartType.BAR, [], data_source="/api/chart")
        html = str(widget.render())
        assert 'hx-target="#chart-body-' in html
        assert 'id="chart-body-' in html

    def test_no_filters_form_when_none(self) -> None:
        widget = ChartWidget("Sales", ChartType.BAR, [])
        html = str(widget.render())
        assert "chart-filters" not in html


class TestChartWidgetEmptyState:
    def test_custom_title_message_icon(self) -> None:
        widget = ChartWidget(
            "Sales",
            ChartType.BAR,
            [],
            empty_state_title="Nothing yet",
            empty_state_message="Adjust your filters.",
            empty_state_icon="📊",
        )
        html = str(widget.render())
        assert "Nothing yet" in html
        assert "Adjust your filters." in html
        assert "📊" in html

    def test_default_title_preserved(self) -> None:
        widget = ChartWidget("Sales", ChartType.BAR, [])
        html = str(widget.render())
        assert "No data" in html
