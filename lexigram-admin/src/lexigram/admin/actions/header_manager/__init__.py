"""
Header action management package.

Provides components for managing header actions in data tables.
"""

from __future__ import annotations

from lexigram.admin.actions.header_manager.actions import (
    BASIC_ACTIONS,
    BULK_ACTIONS,
    IMPORT_EXPORT_ACTIONS,
    UTILITY_ACTIONS,
    create_bulk_delete_action,
    create_bulk_edit_action,
    create_create_action,
    create_export_action,
    create_help_action,
    create_import_action,
    create_refresh_action,
    create_settings_action,
)
from lexigram.admin.actions.header_manager.decorators import (
    ThrottlerProtocol,
    debounce,
    header_action,
    requires_confirmation,
    requires_selection,
    with_error_handling,
    with_loading_indicator,
)
from lexigram.admin.actions.header_manager.density import DensityManager
from lexigram.admin.actions.header_manager.manager import HeaderActionManager
from lexigram.admin.actions.header_manager.shortcuts import KeyboardShortcutManager
from lexigram.admin.actions.header_manager.types import (
    ColumnVisibilityConfig,
    DensityConfig,
    HeaderAction,
    HeaderActionStyle,
    IHeaderDataSource,
    TableDensity,
)
from lexigram.admin.actions.header_manager.visibility import ColumnVisibilityManager

__all__ = [
    "BASIC_ACTIONS",
    "BULK_ACTIONS",
    "IMPORT_EXPORT_ACTIONS",
    "UTILITY_ACTIONS",
    "ColumnVisibilityConfig",
    "ColumnVisibilityManager",
    "DensityConfig",
    "DensityManager",
    "HeaderAction",
    "HeaderActionManager",
    "HeaderActionStyle",
    "IHeaderDataSource",
    "KeyboardShortcutManager",
    "TableDensity",
    "ThrottlerProtocol",
    "create_bulk_edit_action",
    "create_create_action",
    "create_export_action",
    "create_help_action",
    "create_import_action",
    "create_refresh_action",
    "create_settings_action",
    "debounce",
    "header_action",
    "requires_confirmation",
    "requires_selection",
    "with_error_handling",
    "with_loading_indicator",
]
