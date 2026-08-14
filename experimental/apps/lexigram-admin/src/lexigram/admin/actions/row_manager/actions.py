"""
Row action definitions and configurations.

Provides predefined actions for common row operations.
"""

from __future__ import annotations

from lexigram.admin.actions.row_manager.types import ActionStyle, RowAction


def create_view_action(
    url_template: str = "/admin/{resource}/{id}",
    open_in_modal: bool = True,
    label: str = "View",
    icon: str = "eye",
    keyboard_shortcut: str = "v",
) -> RowAction:
    """Create a view action."""
    return RowAction(
        name="view",
        label=label,
        icon=icon,
        style=ActionStyle.INFO,
        url=url_template,
        method="GET",
        open_in_modal=open_in_modal,
        keyboard_shortcut=keyboard_shortcut,
        tooltip="View details",
    )


def create_edit_action(
    url_template: str = "/admin/{resource}/{id}/edit",
    open_in_modal: bool = False,
    label: str = "Edit",
    icon: str = "pencil",
    keyboard_shortcut: str = "e",
) -> RowAction:
    """Create an edit action."""
    return RowAction(
        name="edit",
        label=label,
        icon=icon,
        style=ActionStyle.PRIMARY,
        url=url_template,
        method="GET",
        open_in_modal=open_in_modal,
        keyboard_shortcut=keyboard_shortcut,
        tooltip="Edit record",
    )


def create_delete_action(
    confirm_message: str = "Are you sure you want to delete this record?",
    label: str = "Delete",
    icon: str = "trash",
    keyboard_shortcut: str = "Delete",
) -> RowAction:
    """Create a delete action."""
    return RowAction(
        name="delete",
        label=label,
        icon=icon,
        style=ActionStyle.DANGER,
        confirm=True,
        confirm_message=confirm_message,
        keyboard_shortcut=keyboard_shortcut,
        tooltip="Delete record",
    )


def create_duplicate_action(
    label: str = "Duplicate",
    icon: str = "copy",
    keyboard_shortcut: str = "Ctrl+D",
) -> RowAction:
    """Create a duplicate action."""
    return RowAction(
        name="duplicate",
        label=label,
        icon=icon,
        style=ActionStyle.SECONDARY,
        keyboard_shortcut=keyboard_shortcut,
        tooltip="Duplicate record",
    )


# Predefined action sets
BASIC_ROW_ACTIONS = [
    create_view_action(),
    create_edit_action(),
    create_delete_action(),
]

STANDARD_ROW_ACTIONS = [
    create_view_action(),
    create_edit_action(),
    create_duplicate_action(),
    create_delete_action(),
]
