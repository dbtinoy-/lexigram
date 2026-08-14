"""Static molecule re-exports for the ``lexigram.ui`` public surface.

Type-checker only: the top-level package resolves names lazily via
``__getattr__`` at runtime, so these imports never execute eagerly.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
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

    __all__ = (
        "ActionButton",
        "Alert",
        "Breadcrumbs",
        "Builder",
        "Card",
        "DataTableScriptRenderer",
        "DateHierarchyFilter",
        "DateRangeFilter",
        "Dropdown",
        "EmptyState",
        "ErrorState",
        "FilterDropdown",
        "FormActions",
        "FormField",
        "InfolistEntry",
        "InfolistEntryType",
        "InfolistWidget",
        "InlineEditCell",
        "InputGroup",
        "JumpToPage",
        "LayoutSwitcher",
        "LoadingOverlay",
        "MetricCard",
        "Modal",
        "PageSizeSelector",
        "PaginationLinks",
        "Popover",
        "LiveCounter",
        "RealTimeFeed",
        "RichSelect",
        "Section",
        "SimpleAlert",
        "Stack",
        "StatCard",
        "Tab",
        "TabGroup",
        "TablePagination",
        "TabPanel",
        "Tabs",
        "InlineToast",
        "ServerToastChannel",
        "Toast",
        "ToastData",
        "ToastRenderer",
        "ToastType",
        "flash_to_toast",
        "ToggleIcon",
        "InfiniteScrollTrigger",
        "VirtualScroll",
)
