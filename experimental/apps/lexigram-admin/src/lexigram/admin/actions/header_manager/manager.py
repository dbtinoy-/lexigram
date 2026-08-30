"""
Header action manager implementation.

Provides the main HeaderActionManager class for managing header actions.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from lexigram.admin.actions.header_manager.actions import (
    BASIC_ACTIONS,
    BULK_ACTIONS,
    IMPORT_EXPORT_ACTIONS,
    UTILITY_ACTIONS,
)
from lexigram.admin.actions.header_manager.density import DensityManager
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
from lexigram.primitives.registry import Registry


class HeaderActionManager:
    """Manages header actions for data tables."""

    def __init__(
        self,
        data_source: IHeaderDataSource[Any] | None = None,
        storage: Callable[[str, str], None] | None = None,
        retriever: Callable[[str], str | None] | None = None,
    ) -> None:
        """Initialize the header action manager.

        Args:
            data_source: Data source for table operations
            storage: Function to store user preferences
            retriever: Function to retrieve user preferences
        """
        self.data_source = data_source
        self._storage = storage
        self._retriever = retriever

        # Initialize sub-managers
        self.visibility_manager = ColumnVisibilityManager(
            ColumnVisibilityConfig(),
            storage,
            retriever,
        )
        self.density_manager = DensityManager(
            DensityConfig(),
            storage,
            retriever,
        )
        self.shortcut_manager = KeyboardShortcutManager()

        # Action registry keyed by action name (core Registry; re-registering
        # an action name replaces the previous binding).
        self._actions: Registry[str, HeaderAction] = Registry(
            name="admin.header_actions",
            allow_overwrite=True,
        )

        # Initialize with default actions
        self._initialize_default_actions()

    def _initialize_default_actions(self) -> None:
        """Initialize default header actions."""
        # Add basic actions
        for action in BASIC_ACTIONS:
            self.add_action(action)

        # Add import/export actions
        for action in IMPORT_EXPORT_ACTIONS:
            self.add_action(action)

        # Add utility actions
        for action in UTILITY_ACTIONS:
            self.add_action(action)

        # Add bulk actions (initially hidden)
        for action in BULK_ACTIONS:
            self.add_action(action)

    def add_action(self, action: HeaderAction) -> None:
        """Add a header action."""
        self._actions.register(action.name, action)
        self.shortcut_manager.register_action(action)

    def remove_action(self, action_name: str) -> None:
        """Remove a header action."""
        if self._actions.has(action_name):
            action = self._actions.get(action_name)
            if action and action.keyboard_shortcut:
                self.shortcut_manager.unregister_action(action.keyboard_shortcut)
            self._actions.unregister(action_name)

    def get_action(self, action_name: str) -> HeaderAction | None:
        """Get a header action by name."""
        return self._actions.get(action_name)

    def get_all_actions(self) -> list[HeaderAction]:
        """Get all header actions."""
        return list(self._actions.values())

    def get_visible_actions(self, position: str | None = None) -> list[HeaderAction]:
        """Get actions that are currently visible."""
        actions = [action for action in self._actions.values() if action.visible()]
        if position:
            actions = [action for action in actions if action.position == position]
        return actions

    async def execute_action(self, action_name: str) -> Any:
        """Execute a header action."""
        action = self.get_action(action_name)
        if action and action.handler:
            result = action.handler()
            # If the result is a coroutine, await it
            if hasattr(result, "__await__"):
                return await result
            return result
        return None

    def handle_keyboard_shortcut(self, shortcut: str) -> HeaderAction | None:
        """Handle a keyboard shortcut."""
        return self.shortcut_manager.get_action_for_shortcut(shortcut)

    # Column visibility methods
    def show_column(self, column: str) -> None:
        """Show a column."""
        self.visibility_manager.show_column(column)

    def hide_column(self, column: str) -> None:
        """Hide a column."""
        self.visibility_manager.hide_column(column)

    def toggle_column_visibility(self, column: str) -> None:
        """Toggle column visibility."""
        self.visibility_manager.toggle_column(column)

    def get_visible_columns(self) -> set[str]:
        """Get visible columns."""
        return self.visibility_manager.visible_columns

    def is_column_visible(self, column: str) -> bool:
        """Check if column is visible."""
        return self.visibility_manager.is_column_visible(column)

    # Density methods
    def set_table_density(self, density: TableDensity) -> None:
        """Set table density."""
        self.density_manager.set_density(density)

    def cycle_table_density(self) -> TableDensity:
        """Cycle to next density option."""
        return self.density_manager.cycle_density()

    def get_current_density(self) -> TableDensity:
        """Get current table density."""
        return self.density_manager.current_density

    def get_density_css_class(self) -> str:
        """Get CSS class for current density."""
        return self.density_manager.get_css_class()

    # Bulk action management
    def update_bulk_actions_visibility(self, has_selection: bool) -> None:
        """Update visibility of bulk actions based on selection."""
        for action_name in ["bulk_delete", "bulk_edit"]:
            action = self.get_action(action_name)
            if action:
                # Create new action with updated visibility
                updated_action = HeaderAction(
                    name=action.name,
                    label=action.label,
                    handler=action.handler,
                    icon=action.icon,
                    style=action.style,
                    url=action.url,
                    method=action.method,
                    open_in_modal=action.open_in_modal,
                    keyboard_shortcut=action.keyboard_shortcut,
                    visible=lambda: has_selection,
                    disabled=action.disabled,
                    tooltip=action.tooltip,
                    badge=action.badge,
                    position=action.position,
                    metadata=action.metadata,
                )
                self.add_action(updated_action)

    # Data source operations
    async def refresh_data(self) -> list[Any]:
        """Refresh table data."""
        if self.data_source:
            return await self.data_source.refresh()
        return []

    async def create_record(self, data: dict[str, Any]) -> Any:
        """Create a new record."""
        if self.data_source:
            return await self.data_source.create(data)
        return None

    async def import_data(self, file_path: str, file_format: str = "csv") -> int:
        """Import data from file."""
        if self.data_source:
            return await self.data_source.import_data(file_path, file_format)
        return 0

    async def export_data(self, file_format: str = "csv") -> str:
        """Export data to file."""
        if self.data_source:
            return await self.data_source.export_all(file_format)
        return ""

    # Configuration methods
    def configure_visibility(
        self,
        enabled: bool = True,
        default_visible: list[str] | None = None,
        always_visible: list[str] | None = None,
        save_preference: bool = True,
    ) -> None:
        """Configure column visibility settings."""
        config = ColumnVisibilityConfig(
            enabled=enabled,
            default_visible=default_visible or [],
            always_visible=always_visible or [],
            save_preference=save_preference,
        )
        self.visibility_manager = ColumnVisibilityManager(
            config,
            self._storage,
            self._retriever,
        )

    def configure_density(
        self,
        enabled: bool = True,
        default: TableDensity = TableDensity.NORMAL,
        options: list[TableDensity] | None = None,
        save_preference: bool = True,
    ) -> None:
        """Configure table density settings."""
        config = DensityConfig(
            enabled=enabled,
            default=default,
            options=options
            or [
                TableDensity.COMPACT,
                TableDensity.NORMAL,
                TableDensity.COMFORTABLE,
            ],
            save_preference=save_preference,
        )
        self.density_manager = DensityManager(
            config,
            self._storage,
            self._retriever,
        )

    # Standard actions
    def add_create_action(self, **kwargs) -> None:
        """Add a create action."""
        from lexigram.admin.actions.header_manager.actions import create_create_action

        action = create_create_action(**kwargs)
        self.add_action(action)

    def add_import_action(self, **kwargs) -> None:
        """Add an import action."""
        from lexigram.admin.actions.header_manager.actions import create_import_action

        action = create_import_action(**kwargs)
        self.add_action(action)

    def add_export_action(self, **kwargs) -> None:
        """Add an export action."""
        from lexigram.admin.actions.header_manager.actions import create_export_action

        action = create_export_action(**kwargs)
        if self.data_source:
            action = HeaderAction(
                name=action.name,
                label=action.label,
                handler=self.export_data,
                icon=action.icon,
                style=action.style,
                url=action.url,
                method=action.method,
                open_in_modal=action.open_in_modal,
                keyboard_shortcut=action.keyboard_shortcut,
                visible=action.visible,
                disabled=action.disabled,
                tooltip=action.tooltip,
                badge=action.badge,
                position=action.position,
                metadata=action.metadata,
            )
        self.add_action(action)

    def add_refresh_action(self, **kwargs) -> None:
        """Add a refresh action."""
        from lexigram.admin.actions.header_manager.actions import create_refresh_action

        action = create_refresh_action(**kwargs)
        if self.data_source:
            action = HeaderAction(
                name=action.name,
                label=action.label,
                handler=self.refresh_data,
                icon=action.icon,
                style=action.style,
                url=action.url,
                method=action.method,
                open_in_modal=action.open_in_modal,
                keyboard_shortcut=action.keyboard_shortcut,
                visible=action.visible,
                disabled=action.disabled,
                tooltip=action.tooltip,
                badge=action.badge,
                position=action.position,
                metadata=action.metadata,
            )
        self.add_action(action)

    def add_custom_action(
        self,
        name: str,
        label: str,
        handler: Callable[[], Any] | None = None,
        **kwargs,
    ) -> None:
        """Add a custom header action."""
        action = HeaderAction(
            name=name,
            label=label,
            handler=handler,
            icon=kwargs.get("icon"),
            style=kwargs.get("style", HeaderActionStyle.SECONDARY),
            url=kwargs.get("url"),
            method=kwargs.get("method"),  # type: ignore[arg-type]
            open_in_modal=kwargs.get("open_in_modal", False),
            keyboard_shortcut=kwargs.get("keyboard_shortcut"),
            visible=kwargs.get("visible", lambda: True),
            disabled=kwargs.get("disabled", lambda: False),
            tooltip=kwargs.get("tooltip"),
            badge=kwargs.get("badge"),
            position=kwargs.get("position", "end"),
            metadata=kwargs.get("metadata", {}),
        )
        self.add_action(action)

    # Utility methods
    def get_action_groups(self) -> dict[str, list[HeaderAction]]:
        """Get actions grouped by position."""
        groups: dict[str, list[HeaderAction]] = {"start": [], "end": []}
        for action in self.get_visible_actions():
            position = action.position
            if position in groups:
                groups[position].append(action)
        return groups

    def get_registered_shortcuts(self) -> dict[str, str]:
        """Get all registered keyboard shortcuts."""
        return self.shortcut_manager.get_registered_shortcuts()

    def clear_all_actions(self) -> None:
        """Clear all actions and shortcuts."""
        self._actions.clear()
        self.shortcut_manager.clear_all_shortcuts()
