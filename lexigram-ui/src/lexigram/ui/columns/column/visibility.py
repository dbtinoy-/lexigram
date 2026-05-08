"""
Column visibility control methods.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Self, cast


class ColumnVisibilityMixin:
    """Mixin class containing visibility control methods."""

    def visible(self, visible: bool | Callable = True) -> Self:
        """
        Control column visibility.

        Can accept a boolean or a callable that returns a boolean,
        allowing for dynamic visibility based on record data.

        Args:
            visible: Boolean or callable that returns boolean

        Returns:
            Self for method chaining

        Example:
            >>> # Static visibility
            >>> TextColumn("internal_id").visible(False)
            >>>
            >>> # Dynamic visibility
            >>> def show_if_admin(record):
            ...     return record.get("role") == "admin"
            >>> TextColumn("secret").visible(show_if_admin)
        """
        if callable(visible):
            self._visible_callback = visible
        else:
            self._visible = visible
        return self

    def visible_from(self, breakpoint_name: str) -> Self:
        """
        Show column starting from breakpoint (hidden on smaller screens).

        Args:
            breakpoint_name: 'sm', 'md', 'lg', 'xl', '2xl'
        """
        self._visibility_classes.append("hidden")  # type: ignore[attr-defined]
        self._visibility_classes.append(f"{breakpoint_name}:table-cell")  # type: ignore[attr-defined]
        return self

    def hidden_from(self, breakpoint_name: str) -> Self:
        """
        Hide column starting from breakpoint (visible on smaller screens).

        Args:
            breakpoint_name: 'sm', 'md', 'lg', 'xl', '2xl'
        """
        self._visibility_classes.append(f"{breakpoint_name}:hidden")  # type: ignore[attr-defined]
        return self

    def hidden_on_mobile(self) -> Self:
        """Shorthand for hidden on mobile, visible on desktop (md breakpoint)."""
        return self.visible_from("md")

    def is_visible(
        self,
        user: Any = None,
        resource_name: str | None = None,
        record: dict | Any | None = None,
        permission_service: Any = None,
    ) -> bool:
        """Check if column should be visible."""
        # 1. Check callback if set
        if self._visible_callback:  # type: ignore[truthy-function]
            return cast("bool", self._visible_callback(record))

        # 2. Check PermissionService if user, resource_name, and service are provided
        if user and resource_name and permission_service is not None:
            # Ensure we are not accidentally treating record as user
            if (
                hasattr(user, "roles") or hasattr(user, "user_id")
            ) and not permission_service.can_view_field(user, resource_name, self.name):
                return False

        return self._visible
