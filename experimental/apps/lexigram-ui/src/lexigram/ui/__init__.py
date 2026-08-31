"""Lexigram UI — HTMX/htpy component library for Lexigram web applications.

Provides general-purpose UI components, layouts, and utilities for building
server-rendered HTMX applications.
"""

from __future__ import annotations

__path__ = __import__("pkgutil").extend_path(__path__, __name__)

from typing import TYPE_CHECKING, Any

from lexigram.ui.constants import __version__ as __version__
from lexigram.ui.exports.lazy import LAZY_IMPORTS as _LAZY_IMPORTS
from lexigram.ui.exports.public import __all__

if TYPE_CHECKING:
    from lexigram.ui.accessibility import (
        AriaAttrs,
        AriaLive,
        AriaRole,
        SkipLink,
        announce,
        announce_action_complete,
        announce_selection_change,
        announce_table_update,
        button_aria,
        cell_aria,
        dialog_aria,
        header_aria,
        keyboard_navigation_script,
        live_region_aria,
        row_aria,
        search_aria,
        tab_aria,
        table_aria,
        tabpanel_aria,
    )
    from lexigram.ui.actions import (
        Action,
        ActionTarget,
        BulkAction,
        CreateAction,
        DeleteAction,
        DeleteBulkAction,
        EditAction,
        ExportAction,
        ExportBulkAction,
        ViewAction,
    )
    from lexigram.ui.charts import (
        AreaChart,
        BarChart,
        ChartConfig,
        ChartDataPoint,
        ChartType,
        LineChart,
        MiniBar,
        PieChart,
        Sparkline,
    )
    from lexigram.ui.columns import (
        BadgeColumn,
        BooleanColumn,
        Column,
        CurrencyColumn,
        DateColumn,
        ImageColumn,
        ListColumn,
        TextColumn,
    )
    from lexigram.ui.config import (
        BaseLayoutConfig,
        DebounceConfig,
        FooterConfig,
        HeadConfig,
        HTMLDocumentConfig,
        ToastConfig,
        UIConfig,
    )
    from lexigram.ui.core.base import (
        Component,
        Element,
        RawHTML,
        el,
        raw,
        render_to_string,
    )
    from lexigram.ui.core.context import (
        UIContext,
        get_ui_context,
        reset_ui_context,
        set_ui_context,
    )
    from lexigram.ui.core.js import js_json, js_string
    from lexigram.ui.core.url import is_safe_navigation_url
    from lexigram.ui.core.zones import SwapMode, Zone, Zones
    from lexigram.ui.decorators import component
    from lexigram.ui.di.provider import UIProvider
    from lexigram.ui.exceptions import (
        ErrorCategory,
        ErrorResponse,
        FieldError,
        UIError,
        htmx_error_response,
        not_found_error,
        permission_error,
        render_validation_errors,
        server_error,
        timeout_error,
        validation_error,
    )
    from lexigram.ui.exports.atoms import *  # noqa: F403
    from lexigram.ui.exports.layouts import *  # noqa: F403
    from lexigram.ui.exports.molecules import *  # noqa: F403
    from lexigram.ui.htmx import HTMXAttrs, HTMXAttrsBuilder, helpers, htmx, sse
    from lexigram.ui.module import UIModule
    from lexigram.ui.organisms.activity_feed import ActivityFeed
    from lexigram.ui.organisms.filter_drawer import FilterDrawer
    from lexigram.ui.organisms.forms import Form
    from lexigram.ui.organisms.live_polling import AutoRefreshWidget, LiveDataTable
    from lexigram.ui.organisms.notification_bell import NotificationBell
    from lexigram.ui.organisms.repeater import Repeater
    from lexigram.ui.organisms.simple_pagination import SimplePagination
    from lexigram.ui.organisms.slide_over import SlideOver
    from lexigram.ui.organisms.sortable_list import SortableRecordList
    from lexigram.ui.organisms.systembox import SystemBox
    from lexigram.ui.organisms.task_progress import TaskProgress
    from lexigram.ui.organisms.userbox import UserBox
    from lexigram.ui.performance.observability import (
        MetricProtocol,
        MetricsCollector,
        MetricType,
    )
    from lexigram.ui.performance.performance import (
        RenderCache,
        RequestCoalescer,
        ResponseOptimizer,
        add_htmx_timing_header,
        cached_render,
        debounced_search_attrs,
        infinite_scroll_trigger,
        lazy_load_placeholder,
        measure_render_time,
        optimize_htmx_response,
    )
    from lexigram.ui.protocols import RenderableProtocol
    from lexigram.ui.state import TableState
    from lexigram.ui.styles.theme import shadcn_css


def __getattr__(name: str) -> Any:
    if name in _LAZY_IMPORTS:
        import importlib

        module = importlib.import_module(_LAZY_IMPORTS[name])
        value = getattr(module, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(__all__) | set(_LAZY_IMPORTS.keys()))
