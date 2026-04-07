"""Dashboard assembly — collects and composes dashboard surfaces from contributors."""

from __future__ import annotations

from lexigram.admin.dashboard.assembler import DashboardAssembler
from lexigram.admin.dashboard.chart_widget import ChartWidget
from lexigram.admin.dashboard.widgets import (
    DashboardConfig,
    InMemoryDashboardStore,
    WidgetConfig,
    WidgetRegistry,
    WidgetType,
)

__all__ = [
    "ChartWidget",
    "DashboardAssembler",
    "DashboardConfig",
    "InMemoryDashboardStore",
    "WidgetConfig",
    "WidgetRegistry",
    "WidgetType",
]
