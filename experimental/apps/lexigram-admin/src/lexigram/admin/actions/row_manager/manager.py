"""
Row action manager implementation.

Provides the main RowActionManager class for managing row actions.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from lexigram.admin.actions.row_manager.actions import (
    BASIC_ROW_ACTIONS,
    create_delete_action,
    create_duplicate_action,
    create_edit_action,
    create_view_action,
)
from lexigram.admin.actions.row_manager.groups import ActionGroupManager
from lexigram.admin.actions.row_manager.shortcuts import KeyboardShortcutManager
from lexigram.admin.actions.row_manager.types import (
    ActionPosition,
    ActionStyle,
    IRowDataSource,
    RowAction,
)


class RowActionManager:
    """Manager for row-level actions in data tables."""

    def __init__(self, data_source: IRowDataSource[Any] | None = None):
        """Initialize row action manager.

        Args:
            data_source: Optional data source for built-in actions
        """
        self.data_source = data_source
        self._actions: list[RowAction] = []
        self._group_manager = ActionGroupManager()
        self._shortcut_manager = KeyboardShortcutManager()

        # Initialize with default actions
        self._initialize_default_actions()

    def _initialize_default_actions(self) -> None:
        """Initialize default row actions."""
        for action in BASIC_ROW_ACTIONS:
            self.add_action(action)

    def add_action(self, action: RowAction) -> None:
        """Add a row action."""
        self._actions.append(action)
        self._shortcut_manager.register_action(action)

    def remove_action(self, action_name: str) -> None:
        """Remove a row action."""
        self._actions = list(
            filter(lambda action: action.name != action_name, self._actions),
        )
        # Note: Keyboard shortcuts are managed by the shortcut manager

    def get_action(self, name: str) -> RowAction | None:
        """Get an action by name."""
        # Check direct actions
        for action in self._actions:
            if action.name == name:
                return action

        # Check actions in groups
        for group in self._group_manager.get_all_groups():
            for action in group.actions:
                if action.name == name:
                    return action

        return None

    def get_all_actions(self) -> list[RowAction]:
        """Get all direct actions (not including grouped actions)."""
        return self._actions.copy()

    def get_visible_actions(
        self,
        record: Any,
        position: ActionPosition | None = None,
    ) -> list[RowAction]:
        """Get visible actions for a record."""
        actions = []

        for action in self._actions:
            # Check position filter
            if position and action.position != position:
                continue

            # Check visibility
            if action.visible(record):
                actions.append(action)

        return actions

    def get_all_visible_actions(self, record: Any) -> list[RowAction]:
        """Get all visible actions for a record (including grouped actions)."""
        actions = self.get_visible_actions(record)

        # Add visible actions from groups
        for group in self._group_manager.get_visible_groups(record):
            actions.extend(group.actions)

        return actions

    async def execute_action(
        self,
        action_name: str,
        record_id: Any,
        record: Any | None = None,
    ) -> Any:
        """Execute a row action."""
        action = self.get_action(action_name)
        if not action:
            raise ValueError(f"Action not found: {action_name}")

        if not action.handler:
            raise ValueError(f"Action has no handler: {action_name}")

        return await action.handler(record_id)

    def handle_keyboard_shortcut(
        self,
        shortcut: str,
        record_id: Any,
        record: Any | None = None,
    ) -> RowAction | None:
        """Handle a keyboard shortcut."""
        return self._shortcut_manager.execute_shortcut(shortcut, record_id, record)

    def get_keyboard_shortcuts(self) -> dict[str, str]:
        """Get all registered keyboard shortcuts."""
        return self._shortcut_manager.get_registered_shortcuts_with_labels()

    # Action group management
    def create_action_group(
        self,
        name: str,
        label: str,
        actions: list[RowAction],
        **kwargs,
    ) -> None:
        """Create an action group (dropdown menu)."""
        self._group_manager.create_group(name, label, actions, **kwargs)

    def get_visible_groups(self, record: Any) -> list:
        """Get visible action groups for a record."""
        return self._group_manager.get_visible_groups(record)

    # Standard actions
    def add_view_action(self, **kwargs) -> None:
        """Add a view action."""
        action = create_view_action(**kwargs)
        self.add_action(action)

    def add_edit_action(self, **kwargs) -> None:
        """Add an edit action."""
        action = create_edit_action(**kwargs)
        self.add_action(action)

    def add_delete_action(self, **kwargs) -> None:
        """Add a delete action."""
        action = create_delete_action(**kwargs)
        if self.data_source:
            action = RowAction(
                name=action.name,
                label=action.label,
                handler=self.delete_record,
                icon=action.icon,
                style=action.style,
                position=action.position,
                confirm=action.confirm,
                confirm_message=action.confirm_message,
                url=action.url,
                method=action.method,
                open_in_modal=action.open_in_modal,
                keyboard_shortcut=action.keyboard_shortcut,
                visible=action.visible,
                disabled=action.disabled,
                tooltip=action.tooltip,
                badge=action.badge,
                group=action.group,
                metadata=action.metadata,
            )
        self.add_action(action)

    def add_duplicate_action(self, **kwargs) -> None:
        """Add a duplicate action."""
        action = create_duplicate_action(**kwargs)
        if self.data_source:
            action = RowAction(
                name=action.name,
                label=action.label,
                handler=self.duplicate_record,
                icon=action.icon,
                style=action.style,
                position=action.position,
                confirm=action.confirm,
                confirm_message=action.confirm_message,
                url=action.url,
                method=action.method,
                open_in_modal=action.open_in_modal,
                keyboard_shortcut=action.keyboard_shortcut,
                visible=action.visible,
                disabled=action.disabled,
                tooltip=action.tooltip,
                badge=action.badge,
                group=action.group,
                metadata=action.metadata,
            )
        self.add_action(action)

    def add_custom_action(
        self,
        name: str,
        label: str,
        handler: Callable[[Any], Any],
        **kwargs,
    ) -> None:
        """Add a custom row action."""
        action = RowAction(
            name=name,
            label=label,
            handler=handler,
            icon=kwargs.get("icon"),
            style=kwargs.get("style", ActionStyle.SECONDARY),
            confirm=kwargs.get("confirm", False),
            confirm_message=kwargs.get("confirm_message"),
            keyboard_shortcut=kwargs.get("keyboard_shortcut"),
            tooltip=kwargs.get("tooltip"),
            visible=kwargs.get("visible", lambda _: True),
            disabled=kwargs.get("disabled", lambda _: False),
            metadata=kwargs.get("metadata", {}),
        )
        self.add_action(action)

    # Data source operations
    async def get_record(self, record_id: Any) -> Any:
        """Get a record by ID."""
        if self.data_source:
            return await self.data_source.get_by_id(record_id)
        return None

    async def delete_record(self, record_id: Any) -> bool:
        """Delete a record."""
        if self.data_source:
            return await self.data_source.delete(record_id)
        return False

    async def duplicate_record(self, record_id: Any) -> Any:
        """Duplicate a record."""
        if self.data_source:
            return await self.data_source.duplicate(record_id)
        return None

    # Utility methods
    def clear_all_actions(self) -> None:
        """Clear all actions and shortcuts."""
        self._actions.clear()
        self._group_manager.clear_groups()
        self._shortcut_manager.clear_all_shortcuts()

    def get_action_count(self) -> int:
        """Get total number of actions."""
        direct_actions = len(self._actions)
        grouped_actions = sum(
            len(group.actions) for group in self._group_manager.get_all_groups()
        )
        return direct_actions + grouped_actions

    def get_group_count(self) -> int:
        """Get number of action groups."""
        return len(self._group_manager.get_all_groups())
