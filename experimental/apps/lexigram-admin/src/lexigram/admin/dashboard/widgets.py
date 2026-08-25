"""Admin dashboard widget types and infrastructure.

Facade module: widget type definitions live in
:mod:`lexigram.admin.dashboard.widget_defs`, contributor card rendering in
:mod:`lexigram.admin.dashboard.widget_cards`, and the config popup in
:mod:`lexigram.admin.dashboard.widget_config_popup`. Widget definitions
from lexigram-contracts are also re-exported here.
"""

from __future__ import annotations

from lexigram.admin.dashboard.widget_cards import (
    WidgetRegistry as WidgetRegistry,
)
from lexigram.admin.dashboard.widget_cards import (
    render_dashboard_widgets as render_dashboard_widgets,
)
from lexigram.admin.dashboard.widget_config_popup import (
    render_widget_config_popup as render_widget_config_popup,
)
from lexigram.admin.dashboard.widget_defs import (
    DashboardConfig as DashboardConfig,
)
from lexigram.admin.dashboard.widget_defs import (
    IDashboardStore as IDashboardStore,
)
from lexigram.admin.dashboard.widget_defs import (
    InMemoryDashboardStore as InMemoryDashboardStore,
)
from lexigram.admin.dashboard.widget_defs import IWidget as IWidget
from lexigram.admin.dashboard.widget_defs import (
    WidgetConfig as WidgetConfig,
)
from lexigram.admin.dashboard.widget_defs import WidgetType as WidgetType
from lexigram.admin.dashboard.widget_types import ConfigField as ConfigField
from lexigram.contracts.admin.types import (
    DashboardWidgetDefinition as DashboardWidgetDefinition,
)
from lexigram.contracts.admin.types import WidgetCategory as WidgetCategory
from lexigram.contracts.admin.types import WidgetSize as WidgetSize

__all__ = [
    "ConfigField",
    "DashboardConfig",
    "DashboardWidgetDefinition",
    "IDashboardStore",
    "IWidget",
    "InMemoryDashboardStore",
    "WidgetCategory",
    "WidgetConfig",
    "WidgetRegistry",
    "WidgetSize",
    "WidgetType",
    "render_dashboard_widgets",
    "render_widget_config_popup",
]
