"""
Header action definitions and configurations.

Provides predefined actions for common header operations.
"""

from __future__ import annotations

from collections.abc import Callable

from lexigram.admin.actions.header_manager.types import HeaderAction, HeaderActionStyle


def create_refresh_action(
    handler: Callable[[], None] | None = None,
    label: str = "Refresh",
    icon: str = "refresh",
    **kwargs,
) -> HeaderAction:
    """Create a refresh action."""
    return HeaderAction(
        name="refresh",
        label=label,
        handler=handler,
        icon=icon,
        style=HeaderActionStyle.SECONDARY,
        tooltip="Refresh table data",
        **kwargs,
    )


def create_create_action(
    handler: Callable[[], None] | None = None,
    label: str = "Create",
    icon: str = "plus",
    url: str | None = None,
    **kwargs,
) -> HeaderAction:
    """Create a create action."""
    return HeaderAction(
        name="create",
        label=label,
        handler=handler,
        icon=icon,
        style=HeaderActionStyle.PRIMARY,
        url=url,
        tooltip="Create new record",
        **kwargs,
    )


def create_import_action(
    handler: Callable[[], None] | None = None,
    label: str = "Import",
    icon: str = "upload",
    url: str | None = None,
    **kwargs,
) -> HeaderAction:
    """Create an import action."""
    return HeaderAction(
        name="import",
        label=label,
        handler=handler,
        icon=icon,
        style=HeaderActionStyle.SECONDARY,
        url=url,
        tooltip="Import data from file",
        **kwargs,
    )


def create_export_action(
    handler: Callable[[], None] | None = None,
    label: str = "Export",
    icon: str = "download",
    url: str | None = None,
) -> HeaderAction:
    """Create an export action."""
    return HeaderAction(
        name="export",
        label=label,
        handler=handler,
        icon=icon,
        style=HeaderActionStyle.SECONDARY,
        url=url,
        tooltip="Export data to file",
    )


def create_bulk_delete_action(
    handler: Callable[[], None] | None = None,
    label: str = "Delete Selected",
    icon: str = "trash",
) -> HeaderAction:
    """Create a bulk delete action."""
    return HeaderAction(
        name="bulk_delete",
        label=label,
        handler=handler,
        icon=icon,
        style=HeaderActionStyle.DANGER,
        tooltip="Delete selected records",
        visible=lambda: False,  # Will be shown when items are selected
    )


def create_bulk_edit_action(
    handler: Callable[[], None] | None = None,
    label: str = "Edit Selected",
    icon: str = "edit",
) -> HeaderAction:
    """Create a bulk edit action."""
    return HeaderAction(
        name="bulk_edit",
        label=label,
        handler=handler,
        icon=icon,
        style=HeaderActionStyle.WARNING,
        tooltip="Edit selected records",
        visible=lambda: False,  # Will be shown when items are selected
    )


def create_settings_action(
    handler: Callable[[], None] | None = None,
    label: str = "Settings",
    icon: str = "settings",
    url: str | None = None,
) -> HeaderAction:
    """Create a settings action."""
    return HeaderAction(
        name="settings",
        label=label,
        handler=handler,
        icon=icon,
        style=HeaderActionStyle.SECONDARY,
        url=url,
        tooltip="Table settings",
    )


def create_help_action(
    handler: Callable[[], None] | None = None,
    label: str = "Help",
    icon: str = "help",
    url: str | None = None,
) -> HeaderAction:
    """Create a help action."""
    return HeaderAction(
        name="help",
        label=label,
        handler=handler,
        icon=icon,
        style=HeaderActionStyle.INFO,
        url=url,
        tooltip="Help and documentation",
    )


# Predefined action sets
BASIC_ACTIONS = [
    create_refresh_action(),
    create_create_action(),
]

IMPORT_EXPORT_ACTIONS = [
    create_import_action(),
    create_export_action(),
]

BULK_ACTIONS = [
    create_bulk_delete_action(),
    create_bulk_edit_action(),
]

UTILITY_ACTIONS = [
    create_settings_action(),
    create_help_action(),
]
