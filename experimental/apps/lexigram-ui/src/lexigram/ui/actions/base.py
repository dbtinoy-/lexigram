"""
Base Action classes for DataTable interactions.

Provides a fluent API for defining row actions, header actions, and bulk actions.
Consistent with the Column system's builder pattern.
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Any, Self, cast

from lexigram.ui import Zones

if TYPE_CHECKING:
    from collections.abc import Callable


class ActionTarget(str, Enum):
    """Where the action result should be rendered."""

    DATA = "data"  # Refresh data zone
    MODAL = "modal"  # Open in modal
    SLIDE_OVER = "slide_over"  # Open in side panel
    ROW = "row"  # Target the row itself
    FULL_TABLE = "full_table"  # Full table refresh
    EXTERNAL = "external"  # New tab/window


class Action:
    """Base class for all actions (row, header, etc.).

    Implements a fluent API for configuration.

    Example:
        >>> Action("approve")
        ...     .icon("check")
        ...     .color("success")
        ...     .requires_confirmation()
    """

    def __init__(self, name: str, label: str | None = None):
        """
        Initialize an action.

        Args:
            name: Unique identifier for the action
            label: Display label (defaults to title-cased name)
        """
        self.name = name
        self.label = label or name.replace("_", " ").title()
        self._icon: str | None = None
        self._icon_position: str = "left"
        self._color: str = "primary"  # primary, success, warning, danger, info, gray
        self._url: str | Callable | None = None
        self._action: Callable | None = None  # HTMX or callback
        self._visible: bool = True
        self._visible_callback: Callable | None = None
        self._disabled: bool = False
        self._disabled_callback: Callable | None = None
        self._requires_confirmation: bool = False
        self._confirmation_title: str = "Are you sure?"
        self._confirmation_message: str | None = None
        self._open_modal: bool = False
        self._open_slide_over: bool = False
        self._modal_component: str | None = None
        self._target: str = "_self"  # _self, _blank

        # HTMX specifics
        # HTMX specifics
        self._hx_get: str | None = None
        self._hx_post: str | None = None
        self._hx_delete: str | None = None
        self._hx_target: str | None = None
        self._hx_swap: str = "outerHTML"
        self._hx_push_url: str | None = None

    def icon(self, icon: str, position: str = "left") -> Self:
        """Set action icon."""
        self._icon = icon
        self._icon_position = position
        return self

    def color(self, color: str) -> Self:
        """Set button color variant (primary, success, danger, etc.)."""
        self._color = color
        return self

    def danger(self) -> Self:
        """Set action color to danger."""
        return self.color("danger")

    def success(self) -> Self:
        """Set action color to success."""
        return self.color("success")

    def warning(self) -> Self:
        """Set action color to warning."""
        return self.color("warning")

    def info(self) -> Self:
        """Set action color to info."""
        return self.color("info")

    def gray(self) -> Self:
        """Set action color to gray."""
        return self.color("gray")

    def url(self, url: str | Callable, target: str = "_self") -> Self:
        """Set URL for navigation actions."""
        self._url = url
        self._target = target
        return self

    def action(self, callback: Callable) -> Self:
        """Set backend action handler."""
        self._action = callback
        return self

    def open_modal(self, component: str | None = None) -> Self:
        """Open a modal when clicked."""
        self._open_modal = True
        self._modal_component = component
        self._hx_push_url = "false"
        return self

    def slide_over(self) -> Self:
        """Open in a side panel (SlideOver) when clicked."""
        self._open_slide_over = True
        self._hx_target = Zones.SLIDE_OVER.selector
        self._hx_swap = Zones.SLIDE_OVER.swap_mode.value
        self._hx_push_url = "false"
        return self

    def requires_confirmation(
        self,
        title: str = "Are you sure?",
        message: str | None = None,
    ) -> Self:
        """Require confirmation before execution."""
        self._requires_confirmation = True
        self._confirmation_title = title
        self._confirmation_message = message
        return self

    def visible(self, visible: bool | Callable = True) -> Self:
        """Control visibility."""
        if callable(visible):
            self._visible_callback = visible
        else:
            self._visible = visible
        return self

    def disabled(self, disabled: bool | Callable = True) -> Self:
        """Control enabled/disabled state."""
        if callable(disabled):
            self._disabled_callback = disabled
        else:
            self._disabled = disabled
        return self

    # HTMX Shortcuts for advanced usage
    def hx(
        self,
        get: str | None = None,
        post: str | None = None,
        delete: str | None = None,
        target: str | None = None,
        swap: str | None = None,
        push_url: str | None = None,
    ) -> Self:
        """Configure HTMX attributes manually."""
        if get:
            self._hx_get = get
        if post:
            self._hx_post = post
        if delete:
            self._hx_delete = delete
        if target:
            self._hx_target = target
        if swap:
            self._hx_swap = swap
        if push_url:
            self._hx_push_url = push_url
        return self

    # Logic methods
    def is_visible(
        self,
        user: Any = None,
        resource_name: str | None = None,
        record: dict | Any | None = None,
        permission_service: Any = None,
    ) -> bool:
        """Check if action should be visible."""
        # 1. Check callback if set
        if self._visible_callback:
            return cast("bool", self._visible_callback(record or {}))

        # 2. Check PermissionService if user, resource_name, and service are provided
        if user and resource_name and permission_service is not None:
            # Ensure we are not accidentally treating record as user
            if (
                hasattr(user, "roles") or hasattr(user, "user_id")
            ) and not permission_service.can_perform_action(
                user,
                resource_name,
                self.name,
            ):
                return False

        return self._visible

    def is_disabled(self, record: dict | None = None) -> bool:
        """Check if action should be disabled."""
        if self._disabled_callback:
            return cast("bool", self._disabled_callback(record or {}))
        return self._disabled

    def get_url(self, record: dict | None = None) -> str | None:
        """Resolve URL if it's a callable."""
        if callable(self._url):
            return cast("str | None", self._url(record or {}))
        return self._url

    def get_hx_get(self) -> str | None:
        """Get the HTMX GET URL."""
        return self._hx_get

    def get_hx_post(self) -> str | None:
        """Get the HTMX POST URL."""
        return self._hx_post

    def get_hx_delete(self) -> str | None:
        """Get the HTMX DELETE URL."""
        return self._hx_delete

    def render(
        self,
        record: dict | Any | None = None,
        user: Any = None,
        resource_name: str | None = None,
    ) -> Any:
        """Render action as a button using ActionButton."""
        if not self.is_visible(user=user, resource_name=resource_name, record=record):
            return ""

        from lexigram.ui import ActionButton

        url = self.get_url(record)

        # Helper for dynamic attribute formatting
        def fmt(val: str | None) -> str | None:
            if val and record:
                try:
                    data = record if isinstance(record, dict) else vars(record)

                    # Use fallback for user_id/pk if id is missing in the record object
                    if "{id}" in val and "id" not in data:
                        for fallback in ["user_id", "pk"]:
                            if hasattr(record, fallback):
                                data = {**data, "id": getattr(record, fallback)}
                                break

                    return val.format(**data)
                except (KeyError, ValueError, TypeError):
                    # Fallback if keys missing or format invalid
                    return val
            return val

        # Determine HTMX params with formatting
        hx_delete = fmt(self._hx_delete)
        hx_get = fmt(self._hx_get)
        hx_post = fmt(self._hx_post)

        # Build CSS classes based on color
        color_map = {
            "primary": "primary",
            "success": "green",
            "danger": "red",
            "warning": "yellow",
            "info": "blue",
            "gray": "gray",
        }
        color = color_map.get(self._color, self._color)
        text_color_class = (
            f"text-{color}-600 hover:text-{color}-900 dark:text-{color}-400"
        )

        return ActionButton(
            label=self.label,
            variant="ghost",  # Actions in table usually ghost
            icon=self._icon,
            size="sm",
            href=url,
            hx_delete=hx_delete,
            hx_get=hx_get,
            hx_post=hx_post,
            hx_target=self._hx_target,
            hx_swap=self._hx_swap,
            hx_push_url=self._hx_push_url,
            hx_confirm=self._confirmation_message or self._confirmation_title
            if self._requires_confirmation
            else None,
            class_=text_color_class,
        ).render()


class BulkAction(Action):
    """Action that applies to multiple selected items."""

    def __init__(self, name: str, label: str | None = None):
        super().__init__(name, label)
        self._deselect_after: bool = True

    def deselect_after(self, deselect: bool = True) -> Self:
        """Deselect all items after action completes."""
        self._deselect_after = deselect
        return self
