"""Data table component package with modular architecture."""

from __future__ import annotations

from lexigram.admin.config import TableConfiguration
from lexigram.admin.ui.organisms.data_table.actions import ActionManager
from lexigram.admin.ui.organisms.data_table.coordinator import DataTable
from lexigram.admin.ui.organisms.data_table.layout import LayoutComposer
from lexigram.admin.ui.organisms.data_table.permissions import PermissionManager
from lexigram.admin.ui.organisms.data_table.rendering import DataTableRenderer
from lexigram.admin.ui.organisms.data_table.states import StateRenderer
from lexigram.admin.ui.organisms.data_table.views import (
    ViewStrategy,
    ViewStrategyRegistry,
    view_strategy_registry,
)
from lexigram.ui import TableState

__all__ = [
    "ActionManager",
    "DataTable",
    "DataTableRenderer",
    "LayoutComposer",
    "PermissionManager",
    "StateRenderer",
    "TableConfiguration",
    "TableState",
    "ViewStrategy",
    "ViewStrategyRegistry",
    "view_strategy_registry",
]
