"""Lexigram UI — HTMX/htpy component library for Lexigram web applications.

Provides general-purpose UI components, layouts, and utilities for building
server-rendered HTMX applications.
"""

from __future__ import annotations

__path__ = __import__("pkgutil").extend_path(__path__, __name__)

import importlib.metadata
from typing import TYPE_CHECKING, Any

from lexigram.ui.constants import __version__ as __version__

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
    from lexigram.ui.atoms.badge import Badge
    from lexigram.ui.atoms.button import Button, SubmitButton
    from lexigram.ui.atoms.divider import Divider
    from lexigram.ui.atoms.editors import MarkdownEditor, RichEditor
    from lexigram.ui.atoms.fieldset import Fieldset
    from lexigram.ui.atoms.file_upload import FileUpload
    from lexigram.ui.atoms.icon import Icon
    from lexigram.ui.atoms.inputs import (
        AbstractInput,
        AvatarUpload,
        BelongsTo,
        Checkbox,
        CheckboxList,
        ColorPicker,
        DateInput,
        EmailInput,
        Hidden,
        Input,
        KeyValueField,
        LazySelect,
        MorphTo,
        MultiFileUpload,
        MultiSelect,
        NativeMultiSelect,
        NumberInput,
        PasswordInput,
        Radio,
        Rating,
        Select,
        Slider,
        TagsInput,
        TextArea,
        TextInput,
        TimePicker,
        Toggle,
    )
    from lexigram.ui.atoms.label import Label
    from lexigram.ui.atoms.layout import Aside, Col, Container, Grid, Row
    from lexigram.ui.atoms.link import Link
    from lexigram.ui.atoms.progress_bar import ProgressBar
    from lexigram.ui.atoms.skeleton import Skeleton
    from lexigram.ui.atoms.spinner import Spinner
    from lexigram.ui.atoms.switch import Switch
    from lexigram.ui.atoms.tooltip import Tooltip
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
    from lexigram.ui.htmx import HTMXAttrs, HTMXAttrsBuilder, helpers, htmx, sse
    from lexigram.ui.layouts import (
        BaseLayoutContext,
        CSSManager,
        HTMLDocument,
        JSManager,
        LayoutBase,
    )
    from lexigram.ui.layouts.footer import FooterLink, FooterRenderer
    from lexigram.ui.layouts.head import HeadRenderer
    from lexigram.ui.module import UIModule
    from lexigram.ui.molecules.action_button import ActionButton
    from lexigram.ui.molecules.alert import Alert
    from lexigram.ui.molecules.breadcrumbs import Breadcrumbs
    from lexigram.ui.molecules.builder import Builder
    from lexigram.ui.molecules.card import Card
    from lexigram.ui.molecules.data_table_client_logic import DataTableScriptRenderer
    from lexigram.ui.molecules.date_hierarchy import DateHierarchyFilter
    from lexigram.ui.molecules.date_range_filter import DateRangeFilter
    from lexigram.ui.molecules.dropdown import Dropdown
    from lexigram.ui.molecules.empty_state import EmptyState
    from lexigram.ui.molecules.error_state import ErrorState
    from lexigram.ui.molecules.filter_dropdown import FilterDropdown
    from lexigram.ui.molecules.form_actions import FormActions
    from lexigram.ui.molecules.form_field import FormField
    from lexigram.ui.molecules.infolist import (
        InfolistEntry,
        InfolistEntryType,
        InfolistWidget,
    )
    from lexigram.ui.molecules.inline_edit_cell import InlineEditCell
    from lexigram.ui.molecules.input_group import InputGroup
    from lexigram.ui.molecules.jump_to_page import JumpToPage
    from lexigram.ui.molecules.layout_switcher import LayoutSwitcher
    from lexigram.ui.molecules.loading_overlay import LoadingOverlay
    from lexigram.ui.molecules.metric_card import MetricCard
    from lexigram.ui.molecules.modal import Modal
    from lexigram.ui.molecules.page_size_selector import PageSizeSelector
    from lexigram.ui.molecules.pagination_links import PaginationLinks
    from lexigram.ui.molecules.popover import Popover
    from lexigram.ui.molecules.realtime import LiveCounter, RealTimeFeed
    from lexigram.ui.molecules.rich_select import RichSelect
    from lexigram.ui.molecules.section import Section
    from lexigram.ui.molecules.simple_alert import SimpleAlert
    from lexigram.ui.molecules.stack import Stack
    from lexigram.ui.molecules.stat_card import StatCard
    from lexigram.ui.molecules.tab_group import Tab, TabGroup
    from lexigram.ui.molecules.table_pagination import TablePagination
    from lexigram.ui.molecules.tabs import TabPanel, Tabs
    from lexigram.ui.molecules.toast import (
        InlineToast,
        ServerToastChannel,
        Toast,
        ToastData,
        ToastRenderer,
        ToastType,
        flash_to_toast,
    )
    from lexigram.ui.molecules.toggle import ToggleIcon
    from lexigram.ui.molecules.virtual_scroll import (
        InfiniteScrollTrigger,
        VirtualScroll,
    )
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

_LAZY_IMPORTS: dict[str, str] = {
    # ---- Core primitives ----
    "Component": "lexigram.ui.core.base",
    "Element": "lexigram.ui.core.base",
    "RawHTML": "lexigram.ui.core.base",
    "el": "lexigram.ui.core.base",
    "raw": "lexigram.ui.core.base",
    "render_to_string": "lexigram.ui.core.base",
    # ---- Context ----
    "UIContext": "lexigram.ui.core.context",
    "get_ui_context": "lexigram.ui.core.context",
    "reset_ui_context": "lexigram.ui.core.context",
    "set_ui_context": "lexigram.ui.core.context",
    # ---- Zones ----
    "Zone": "lexigram.ui.core.zones",
    "Zones": "lexigram.ui.core.zones",
    "SwapMode": "lexigram.ui.core.zones",
    # ---- Table state ----
    "TableState": "lexigram.ui.state",
    # ---- Table actions ----
    "Action": "lexigram.ui.actions",
    "ActionTarget": "lexigram.ui.actions",
    "BulkAction": "lexigram.ui.actions",
    "CreateAction": "lexigram.ui.actions",
    "DeleteAction": "lexigram.ui.actions",
    "DeleteBulkAction": "lexigram.ui.actions",
    "EditAction": "lexigram.ui.actions",
    "ExportAction": "lexigram.ui.actions",
    "ExportBulkAction": "lexigram.ui.actions",
    "ViewAction": "lexigram.ui.actions",
    # ---- Table columns ----
    "Column": "lexigram.ui.columns",
    "TextColumn": "lexigram.ui.columns",
    "BadgeColumn": "lexigram.ui.columns",
    "BooleanColumn": "lexigram.ui.columns",
    "DateColumn": "lexigram.ui.columns",
    "ImageColumn": "lexigram.ui.columns",
    "CurrencyColumn": "lexigram.ui.columns",
    "ListColumn": "lexigram.ui.columns",
    # ---- Icons ----
    "get_icon": "lexigram.ui.atoms.icons",
    "IconDefinition": "lexigram.ui.atoms.icons",
    "IconLibrary": "lexigram.ui.atoms.icons",
    # ---- HTMX namespaces ----
    "htmx": "lexigram.ui.htmx",
    "helpers": "lexigram.ui.htmx",
    "sse": "lexigram.ui.htmx",
    "HtmxActionResponse": "lexigram.ui.htmx.action_response",
    "HTMXAttrs": "lexigram.ui.htmx.table_attrs",
    "HTMXAttrsBuilder": "lexigram.ui.htmx.table_attrs",
    # ---- Exceptions & errors ----
    "UIError": "lexigram.ui.exceptions",
    "ErrorCategory": "lexigram.ui.exceptions",
    "FieldError": "lexigram.ui.exceptions",
    "ErrorResponse": "lexigram.ui.exceptions",
    "validation_error": "lexigram.ui.exceptions",
    "not_found_error": "lexigram.ui.exceptions",
    "permission_error": "lexigram.ui.exceptions",
    "server_error": "lexigram.ui.exceptions",
    "timeout_error": "lexigram.ui.exceptions",
    "render_validation_errors": "lexigram.ui.exceptions",
    "htmx_error_response": "lexigram.ui.exceptions",
    # ---- DI ----
    "UIModule": "lexigram.ui.module",
    "UIProvider": "lexigram.ui.di.provider",
    # ---- Protocols ----
    "RenderableProtocol": "lexigram.ui.protocols",
    # ---- Decorators ----
    "component": "lexigram.ui.decorators",
    # ---- Hooks ----
    "UIComponentRenderedHook": "lexigram.ui.hooks",
    "UITemplateRenderedHook": "lexigram.ui.hooks",
    # ---- Accessibility ----
    "AriaAttrs": "lexigram.ui.accessibility",
    "AriaLive": "lexigram.ui.accessibility",
    "AriaRole": "lexigram.ui.accessibility",
    "SkipLink": "lexigram.ui.accessibility",
    "announce": "lexigram.ui.accessibility",
    "announce_action_complete": "lexigram.ui.accessibility",
    "announce_selection_change": "lexigram.ui.accessibility",
    "announce_table_update": "lexigram.ui.accessibility",
    "button_aria": "lexigram.ui.accessibility",
    "cell_aria": "lexigram.ui.accessibility",
    "dialog_aria": "lexigram.ui.accessibility",
    "header_aria": "lexigram.ui.accessibility",
    "keyboard_navigation_script": "lexigram.ui.accessibility",
    "live_region_aria": "lexigram.ui.accessibility",
    "row_aria": "lexigram.ui.accessibility",
    "search_aria": "lexigram.ui.accessibility",
    "tab_aria": "lexigram.ui.accessibility",
    "tabpanel_aria": "lexigram.ui.accessibility",
    "table_aria": "lexigram.ui.accessibility",
    # ---- Config ----
    "UIConfig": "lexigram.ui.config",
    "DebounceConfig": "lexigram.ui.config",
    "HTMLDocumentConfig": "lexigram.ui.config",
    "BaseLayoutConfig": "lexigram.ui.config",
    "HeadConfig": "lexigram.ui.config",
    "FooterConfig": "lexigram.ui.config",
    "ToastConfig": "lexigram.ui.config",
    # ---- Atoms — primitives ----
    "Button": "lexigram.ui.atoms.button",
    "SubmitButton": "lexigram.ui.atoms.button",
    "Badge": "lexigram.ui.atoms.badge",
    "Spinner": "lexigram.ui.atoms.spinner",
    "Icon": "lexigram.ui.atoms.icon",
    "Divider": "lexigram.ui.atoms.divider",
    "Link": "lexigram.ui.atoms.link",
    "Label": "lexigram.ui.atoms.label",
    "Fieldset": "lexigram.ui.atoms.fieldset",
    "FileUpload": "lexigram.ui.atoms.file_upload",
    "ProgressBar": "lexigram.ui.atoms.progress_bar",
    "Skeleton": "lexigram.ui.atoms.skeleton",
    "Switch": "lexigram.ui.atoms.switch",
    "Tooltip": "lexigram.ui.atoms.tooltip",
    "MarkdownEditor": "lexigram.ui.atoms.editors",
    "RichEditor": "lexigram.ui.atoms.editors",
    # ---- Atoms — layout primitives ----
    "Aside": "lexigram.ui.atoms.layout",
    "Col": "lexigram.ui.atoms.layout",
    "Container": "lexigram.ui.atoms.layout",
    "Grid": "lexigram.ui.atoms.layout",
    "Row": "lexigram.ui.atoms.layout",
    "Stack": "lexigram.ui.molecules.stack",
    "shadcn_css": "lexigram.ui.styles.theme",
    # ---- Atoms — inputs (base + text) ----
    "AbstractInput": "lexigram.ui.atoms.inputs",
    "Input": "lexigram.ui.atoms.inputs",
    "TextInput": "lexigram.ui.atoms.inputs",
    "PasswordInput": "lexigram.ui.atoms.inputs",
    "EmailInput": "lexigram.ui.atoms.inputs",
    "TextArea": "lexigram.ui.atoms.inputs",
    # ---- Atoms — inputs (numeric & date) ----
    "NumberInput": "lexigram.ui.atoms.inputs",
    "Slider": "lexigram.ui.atoms.inputs",
    "DateInput": "lexigram.ui.atoms.inputs",
    "TimePicker": "lexigram.ui.atoms.inputs",
    # ---- Molecules — table controls ----
    "DateHierarchyFilter": "lexigram.ui.molecules.date_hierarchy",
    "DateRangeFilter": "lexigram.ui.molecules.date_range_filter",
    "DataTableScriptRenderer": "lexigram.ui.molecules.data_table_client_logic",
    "FilterDropdown": "lexigram.ui.molecules.filter_dropdown",
    "InlineEditCell": "lexigram.ui.molecules.inline_edit_cell",
    "JumpToPage": "lexigram.ui.molecules.jump_to_page",
    "PageSizeSelector": "lexigram.ui.molecules.page_size_selector",
    "SearchBar": "lexigram.ui.molecules.search_bar",
    # ---- Molecules — pagination family ----
    "LayoutSwitcher": "lexigram.ui.molecules.layout_switcher",
    "PaginationLinks": "lexigram.ui.molecules.pagination_links",
    "TablePagination": "lexigram.ui.molecules.table_pagination",
    "ViewSwitcher": "lexigram.ui.molecules.view_switcher",
    "GroupBySwitcher": "lexigram.ui.molecules.group_by_switcher",
    # ---- Molecules — detail widgets ----
    "InfolistEntry": "lexigram.ui.molecules.infolist",
    "InfolistEntryType": "lexigram.ui.molecules.infolist",
    "InfolistWidget": "lexigram.ui.molecules.infolist",
    "Tab": "lexigram.ui.molecules.tab_group",
    "TabGroup": "lexigram.ui.molecules.tab_group",
    # ---- Atoms — inputs (selection) ----
    "Select": "lexigram.ui.atoms.inputs",
    "MultiSelect": "lexigram.ui.atoms.inputs",
    "NativeMultiSelect": "lexigram.ui.atoms.inputs",
    "LazySelect": "lexigram.ui.atoms.inputs",
    "CheckboxList": "lexigram.ui.atoms.inputs",
    "Radio": "lexigram.ui.atoms.inputs",
    "BelongsTo": "lexigram.ui.atoms.inputs",
    "MorphTo": "lexigram.ui.atoms.inputs",
    # ---- Atoms — inputs (toggle) ----
    "Checkbox": "lexigram.ui.atoms.inputs",
    "Toggle": "lexigram.ui.atoms.inputs",
    # ---- Atoms — inputs (special) ----
    "ColorPicker": "lexigram.ui.atoms.inputs",
    "Hidden": "lexigram.ui.atoms.inputs",
    "KeyValueField": "lexigram.ui.atoms.inputs",
    "Rating": "lexigram.ui.atoms.inputs",
    "TagsInput": "lexigram.ui.atoms.inputs",
    # ---- Atoms — inputs (file) ----
    "AvatarUpload": "lexigram.ui.atoms.inputs",
    "MultiFileUpload": "lexigram.ui.atoms.inputs",
    # ---- Action button ----
    "ActionButton": "lexigram.ui.molecules.action_button",
    # ---- Builder ----
    "Builder": "lexigram.ui.molecules.builder",
    # ---- Molecules ----
    "Alert": "lexigram.ui.molecules.alert",
    "SimpleAlert": "lexigram.ui.molecules.simple_alert",
    "Breadcrumbs": "lexigram.ui.molecules.breadcrumbs",
    "Card": "lexigram.ui.molecules.card",
    "Dropdown": "lexigram.ui.molecules.dropdown",
    "EmptyState": "lexigram.ui.molecules.empty_state",
    "ErrorState": "lexigram.ui.molecules.error_state",
    "FormField": "lexigram.ui.molecules.form_field",
    "FieldSchema": "lexigram.ui.molecules.form_field",
    "FormActions": "lexigram.ui.molecules.form_actions",
    "InputGroup": "lexigram.ui.molecules.input_group",
    "LoadingOverlay": "lexigram.ui.molecules.loading_overlay",
    "MetricCard": "lexigram.ui.molecules.metric_card",
    "Modal": "lexigram.ui.molecules.modal",
    "Popover": "lexigram.ui.molecules.popover",
    "RichSelect": "lexigram.ui.molecules.rich_select",
    "Section": "lexigram.ui.molecules.section",
    "StatCard": "lexigram.ui.molecules.stat_card",
    "Tabs": "lexigram.ui.molecules.tabs",
    "TabPanel": "lexigram.ui.molecules.tabs",
    # ---- Molecules — toggle ----
    "ToggleIcon": "lexigram.ui.molecules.toggle",
    # ---- Molecules — toasts ----
    "InlineToast": "lexigram.ui.molecules.toast",
    "Toast": "lexigram.ui.molecules.toast",  # deprecated alias for InlineToast
    "ToastData": "lexigram.ui.molecules.toast",
    "ServerToastChannel": "lexigram.ui.molecules.toast",
    "ToastRenderer": "lexigram.ui.molecules.toast",  # deprecated alias for ServerToastChannel
    "ToastType": "lexigram.ui.molecules.toast",
    "flash_to_toast": "lexigram.ui.molecules.toast",
    # ---- Molecules — realtime / scroll ----
    "InfiniteScrollTrigger": "lexigram.ui.molecules.virtual_scroll",
    "VirtualScroll": "lexigram.ui.molecules.virtual_scroll",
    "RealTimeFeed": "lexigram.ui.molecules.realtime",
    "LiveCounter": "lexigram.ui.molecules.realtime",
    # ---- Organisms ----
    "Form": "lexigram.ui.organisms.forms",
    "Repeater": "lexigram.ui.organisms.repeater",
    "AreaChart": "lexigram.ui.charts",
    "BarChart": "lexigram.ui.charts",
    "ChartConfig": "lexigram.ui.charts",
    "ChartDataPoint": "lexigram.ui.charts",
    "ChartType": "lexigram.ui.charts",
    "LineChart": "lexigram.ui.charts",
    "MiniBar": "lexigram.ui.charts",
    "PieChart": "lexigram.ui.charts",
    "Sparkline": "lexigram.ui.charts",
    "ActivityFeed": "lexigram.ui.organisms.activity_feed",
    "AdminCard": "lexigram.ui.organisms.admin",
    "PageLayout": "lexigram.ui.organisms.admin",
    "SlideOver": "lexigram.ui.organisms.slide_over",
    # ---- Organisms — admin-suite additions ----
    "AutoRefreshWidget": "lexigram.ui.organisms.live_polling",
    "LiveDataTable": "lexigram.ui.organisms.live_polling",
    "NotificationBell": "lexigram.ui.organisms.notification_bell",
    "TaskProgress": "lexigram.ui.organisms.task_progress",
    "UserBox": "lexigram.ui.organisms.userbox",
    "SystemBox": "lexigram.ui.organisms.systembox",
    "SortableRecordList": "lexigram.ui.organisms.sortable_list",
    "FilterDrawer": "lexigram.ui.organisms.filter_drawer",
    "SimplePagination": "lexigram.ui.organisms.simple_pagination",
    # ---- Layouts ----
    "LayoutBase": "lexigram.ui.layouts",
    "BaseLayoutContext": "lexigram.ui.layouts.base_layout",
    "CSSManager": "lexigram.ui.layouts",
    "JSManager": "lexigram.ui.layouts",
    "HTMLDocument": "lexigram.ui.layouts",
    "FooterLink": "lexigram.ui.layouts.footer",
    "FooterRenderer": "lexigram.ui.layouts.footer",
    "HeadRenderer": "lexigram.ui.layouts.head",
    # ---- Performance ----
    "RenderCache": "lexigram.ui.performance.performance",
    "RequestCoalescer": "lexigram.ui.performance.performance",
    "ResponseOptimizer": "lexigram.ui.performance.performance",
    "add_htmx_timing_header": "lexigram.ui.performance.performance",
    "cached_render": "lexigram.ui.performance.performance",
    "debounced_search_attrs": "lexigram.ui.performance.performance",
    "infinite_scroll_trigger": "lexigram.ui.performance.performance",
    "lazy_load_placeholder": "lexigram.ui.performance.performance",
    "measure_render_time": "lexigram.ui.performance.performance",
    "optimize_htmx_response": "lexigram.ui.performance.performance",
    # ---- Observability ----
    "MetricsCollector": "lexigram.ui.performance.observability",
    "MetricProtocol": "lexigram.ui.performance.observability",
    "MetricType": "lexigram.ui.performance.observability",
    # ---- CLI / Registry ----
    "COMPONENT_REGISTRY": "lexigram.ui.cli.registry",
}


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


__all__ = (
    "Component",
    "Element",
    "RawHTML",
    "el",
    "raw",
    "render_to_string",
    "UIContext",
    "get_ui_context",
    "reset_ui_context",
    "set_ui_context",
    "Zone",
    "Zones",
    "SwapMode",
    "TableState",
    "Action",
    "ActionTarget",
    "BulkAction",
    "CreateAction",
    "DeleteAction",
    "DeleteBulkAction",
    "EditAction",
    "ExportAction",
    "ExportBulkAction",
    "ViewAction",
    "Column",
    "TextColumn",
    "BadgeColumn",
    "BooleanColumn",
    "DateColumn",
    "ImageColumn",
    "CurrencyColumn",
    "ListColumn",
    "get_icon",
    "IconDefinition",
    "IconLibrary",
    "htmx",
    "helpers",
    "sse",
    "HtmxActionResponse",
    "HTMXAttrs",
    "HTMXAttrsBuilder",
    "UIError",
    "ErrorCategory",
    "FieldError",
    "ErrorResponse",
    "validation_error",
    "not_found_error",
    "permission_error",
    "server_error",
    "timeout_error",
    "render_validation_errors",
    "htmx_error_response",
    "UIModule",
    "UIProvider",
    "RenderableProtocol",
    "component",
    "UIComponentRenderedHook",
    "UITemplateRenderedHook",
    "AriaAttrs",
    "AriaLive",
    "AriaRole",
    "SkipLink",
    "announce",
    "announce_action_complete",
    "announce_selection_change",
    "announce_table_update",
    "button_aria",
    "cell_aria",
    "dialog_aria",
    "header_aria",
    "keyboard_navigation_script",
    "live_region_aria",
    "row_aria",
    "search_aria",
    "tab_aria",
    "tabpanel_aria",
    "table_aria",
    "UIConfig",
    "DebounceConfig",
    "HTMLDocumentConfig",
    "BaseLayoutConfig",
    "HeadConfig",
    "FooterConfig",
    "ToastConfig",
    "Button",
    "SubmitButton",
    "Badge",
    "Spinner",
    "Icon",
    "Divider",
    "Link",
    "Label",
    "Fieldset",
    "FileUpload",
    "ProgressBar",
    "Skeleton",
    "Switch",
    "Tooltip",
    "MarkdownEditor",
    "RichEditor",
    "Aside",
    "Col",
    "Container",
    "Grid",
    "Row",
    "Stack",
    "shadcn_css",
    "AbstractInput",
    "Input",
    "TextInput",
    "PasswordInput",
    "EmailInput",
    "TextArea",
    "NumberInput",
    "Slider",
    "DateInput",
    "TimePicker",
    "DateHierarchyFilter",
    "DateRangeFilter",
    "DataTableScriptRenderer",
    "FilterDropdown",
    "InlineEditCell",
    "JumpToPage",
    "PageSizeSelector",
    "SearchBar",
    "LayoutSwitcher",
    "PaginationLinks",
    "TablePagination",
    "ViewSwitcher",
    "GroupBySwitcher",
    "InfolistEntry",
    "InfolistEntryType",
    "InfolistWidget",
    "Tab",
    "TabGroup",
    "Select",
    "MultiSelect",
    "NativeMultiSelect",
    "LazySelect",
    "CheckboxList",
    "Radio",
    "BelongsTo",
    "MorphTo",
    "Checkbox",
    "Toggle",
    "ColorPicker",
    "Hidden",
    "KeyValueField",
    "Rating",
    "TagsInput",
    "AvatarUpload",
    "MultiFileUpload",
    "ActionButton",
    "Builder",
    "Alert",
    "SimpleAlert",
    "Breadcrumbs",
    "Card",
    "Dropdown",
    "EmptyState",
    "ErrorState",
    "FormField",
    "FieldSchema",
    "FormActions",
    "InputGroup",
    "LoadingOverlay",
    "MetricCard",
    "Modal",
    "Popover",
    "RichSelect",
    "Section",
    "StatCard",
    "Tabs",
    "TabPanel",
    "ToggleIcon",
    "InlineToast",
    "Toast",
    "ToastData",
    "ServerToastChannel",
    "ToastRenderer",
    "ToastType",
    "flash_to_toast",
    "InfiniteScrollTrigger",
    "VirtualScroll",
    "RealTimeFeed",
    "LiveCounter",
    "Form",
    "Repeater",
    "AreaChart",
    "BarChart",
    "ChartConfig",
    "ChartDataPoint",
    "ChartType",
    "LineChart",
    "MiniBar",
    "PieChart",
    "Sparkline",
    "ActivityFeed",
    "AdminCard",
    "PageLayout",
    "SlideOver",
    "AutoRefreshWidget",
    "LiveDataTable",
    "NotificationBell",
    "TaskProgress",
    "UserBox",
    "SystemBox",
    "SortableRecordList",
    "FilterDrawer",
    "SimplePagination",
    "LayoutBase",
    "BaseLayoutContext",
    "CSSManager",
    "JSManager",
    "HTMLDocument",
    "FooterLink",
    "FooterRenderer",
    "HeadRenderer",
    "RenderCache",
    "RequestCoalescer",
    "ResponseOptimizer",
    "add_htmx_timing_header",
    "cached_render",
    "debounced_search_attrs",
    "infinite_scroll_trigger",
    "lazy_load_placeholder",
    "measure_render_time",
    "optimize_htmx_response",
    "MetricsCollector",
    "MetricProtocol",
    "MetricType",
    "COMPONENT_REGISTRY",
)
