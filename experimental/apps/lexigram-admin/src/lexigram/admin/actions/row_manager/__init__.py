"""
Row action management package.

Provides components for managing row-level actions in data tables.
"""

from __future__ import annotations

from lexigram.admin.actions.row_manager.actions import (
    BASIC_ROW_ACTIONS,
    STANDARD_ROW_ACTIONS,
    create_delete_action,
    create_duplicate_action,
    create_edit_action,
    create_view_action,
)
from lexigram.admin.actions.row_manager.decorators import (
    ThrottlerProtocol,
    debounce,
    requires_confirmation,
    requires_permission,
    row_action,
    with_error_handling,
    with_loading_indicator,
)
from lexigram.admin.actions.row_manager.groups import ActionGroupManager
from lexigram.admin.actions.row_manager.manager import RowActionManager
from lexigram.admin.actions.row_manager.shortcuts import KeyboardShortcutManager
from lexigram.admin.actions.row_manager.types import (
    ActionGroup,
    ActionPosition,
    ActionStyle,
    IRowDataSource,
    RowAction,
)

__all__ = [
    "BASIC_ROW_ACTIONS",
    "STANDARD_ROW_ACTIONS",
    "ActionGroup",
    "ActionGroupManager",
    "ActionPosition",
    "ActionStyle",
    "IRowDataSource",
    "KeyboardShortcutManager",
    "RowAction",
    "RowActionManager",
    "ThrottlerProtocol",
    "create_duplicate_action",
    "create_edit_action",
    "create_view_action",
    "debounce",
    "requires_confirmation",
    "requires_permission",
    "row_action",
    "with_error_handling",
    "with_loading_indicator",
]
