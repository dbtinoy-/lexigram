"""
Action group management for row actions.

Handles grouping of related actions in dropdown menus.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from lexigram.admin.actions.row_manager.types import ActionGroup, ActionStyle, RowAction


class ActionGroupManager:
    """Manages action groups and their visibility."""

    def __init__(self) -> None:
        """Initialize the action group manager."""
        self._groups: dict[str, ActionGroup] = {}

    def add_group(self, group: ActionGroup) -> None:
        """Add an action group."""
        self._groups[group.name] = group

    def get_group(self, name: str) -> ActionGroup | None:
        """Get an action group by name."""
        return self._groups.get(name)

    def get_all_groups(self) -> list[ActionGroup]:
        """Get all action groups."""
        return list(self._groups.values())

    def get_visible_groups(self, record: Any) -> list[ActionGroup]:
        """Get visible action groups for a record."""
        groups = []

        for group in self._groups.values():
            # Check group visibility
            if not group.visible(record):
                continue

            # Filter visible actions in group
            visible_actions = [
                action for action in group.actions if action.visible(record)
            ]

            if visible_actions:
                # Create filtered group
                filtered_group = ActionGroup(
                    name=group.name,
                    label=group.label,
                    icon=group.icon,
                    actions=visible_actions,
                    style=group.style,
                    visible=group.visible,
                )
                groups.append(filtered_group)

        return groups

    def create_group(
        self,
        name: str,
        label: str,
        actions: list[RowAction],
        icon: str | None = "menu",
        style: ActionStyle = ActionStyle.SECONDARY,
        visible: Callable[[Any], bool] | None = None,
    ) -> ActionGroup:
        """Create a new action group."""
        if visible is None:

            def visible(record) -> Any:
                return True

        group = ActionGroup(
            name=name,
            label=label,
            actions=actions,
            icon=icon,
            style=style,
            visible=visible,
        )
        self.add_group(group)
        return group

    def remove_group(self, name: str) -> None:
        """Remove an action group."""
        if name in self._groups:
            del self._groups[name]

    def clear_groups(self) -> None:
        """Clear all action groups."""
        self._groups.clear()
