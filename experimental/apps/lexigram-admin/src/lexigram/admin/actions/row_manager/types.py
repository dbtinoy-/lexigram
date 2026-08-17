"""
Types and data structures for row action management.

Provides enums, dataclasses, and protocols for row actions.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol, TypeVar

T = TypeVar("T")


class ActionStyle(StrEnum):
    """Visual style for actions."""

    PRIMARY = "primary"
    SECONDARY = "secondary"
    SUCCESS = "success"
    DANGER = "danger"
    WARNING = "warning"
    INFO = "info"


class ActionPosition(StrEnum):
    """Where to display the action."""

    ROW_START = "row_start"  # Before row content
    ROW_END = "row_end"  # After row content (default)
    DROPDOWN = "dropdown"  # In overflow menu


@dataclass(slots=True)
class RowAction:
    """Configuration for a row action."""

    name: str
    """Action identifier."""

    label: str
    """Display label."""

    handler: Callable[[Any], Any] | None = None
    """Async function to execute the action."""

    icon: str | None = None
    """Icon name (e.g., 'eye', 'edit', 'trash')."""

    style: ActionStyle = ActionStyle.SECONDARY
    """Visual style."""

    position: ActionPosition = ActionPosition.ROW_END
    """Where to display the action."""

    confirm: bool = False
    """Whether to show confirmation dialog."""

    confirm_message: str | None = None
    """Custom confirmation message."""

    url: str | None = None
    """URL for link-based actions (alternative to handler)."""

    method: str = "GET"
    """HTTP method for URL-based actions."""

    open_in_modal: bool = False
    """Whether to open URL in a modal."""

    keyboard_shortcut: str | None = None
    """Keyboard shortcut (e.g., 'e', 'Ctrl+D')."""

    visible: Callable[[Any], bool] = lambda _: True
    """Function to determine if action is visible for a record."""

    disabled: Callable[[Any], bool] = lambda _: False
    """Function to determine if action is disabled for a record."""

    tooltip: str | None = None
    """Tooltip text."""

    badge: str | None = None
    """Badge text (e.g., "New", "Beta")."""

    group: str | None = None
    """Group name for organizing actions in dropdown."""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Additional metadata."""


@dataclass(slots=True)
class ActionGroup:
    """Group of related actions shown in a dropdown menu."""

    name: str
    """Group identifier."""

    label: str
    """Display label for the dropdown button."""

    icon: str | None = "menu"
    """Icon for dropdown button."""

    actions: list[RowAction] = field(default_factory=list)
    """Actions in this group."""

    style: ActionStyle = ActionStyle.SECONDARY
    """Visual style."""

    visible: Callable[[Any], bool] = lambda _: True
    """Function to determine if group is visible."""


class IRowDataSource(Protocol[T]):  # type: ignore[misc]
    """Protocol for data sources that support row operations."""

    async def get_by_id(self, record_id: Any) -> T | None:
        """Get a single record by ID."""
        ...

    async def delete(self, record_id: Any) -> bool:
        """Delete a record."""
        ...

    async def duplicate(self, record_id: Any) -> T:
        """Duplicate a record."""
        ...
