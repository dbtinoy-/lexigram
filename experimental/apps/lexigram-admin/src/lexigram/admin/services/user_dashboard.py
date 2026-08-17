"""Per-user custom dashboard builder.

Wraps :class:`~lexigram.admin.services.dashboard.DashboardBuilder` with
per-user keying so each user can have their own personalised dashboard layout.

Features:
* Per-user dashboard persistence (``user_id`` → :class:`DashboardConfig`)
* Add / remove / move / resize widgets per-user
* Reset to default (clears customisation, falls back to global config)
* Export / import layout as JSON (for copy/share)
* ``WidgetPlacement`` grid coordinates for drag-and-drop position tracking

Usage::

    from lexigram.admin.services.user_dashboard import UserDashboardService

    svc = UserDashboardService(builder)

    layout = await svc.get_or_create("user-123")
    await svc.add_widget("user-123", "stat_card", {"title": "Revenue"}, col=0, row=0)
    await svc.move_widget("user-123", widget_id="w1", col=2, row=0)
    await svc.reset("user-123")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from lexigram.logging import get_logger

logger = get_logger(__name__)


@dataclass
class WidgetPlacement:
    """Grid position for a widget in the dashboard layout.

    Attributes:
        widget_id: References a :class:`~lexigram.admin.services.dashboard.WidgetConfig` id.
        col: 0-based column index in the grid.
        row: 0-based row index.
        col_span: Number of columns the widget occupies (default 1).
        row_span: Number of rows the widget occupies (default 1).
    """

    widget_id: str
    col: int = 0
    row: int = 0
    col_span: int = 1
    row_span: int = 1

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a JSON-safe dict."""
        return {
            "widget_id": self.widget_id,
            "col": self.col,
            "row": self.row,
            "col_span": self.col_span,
            "row_span": self.row_span,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WidgetPlacement:
        """Deserialise from a dict."""
        return cls(
            widget_id=data["widget_id"],
            col=data.get("col", 0),
            row=data.get("row", 0),
            col_span=data.get("col_span", 1),
            row_span=data.get("row_span", 1),
        )


@dataclass
class UserDashboardLayout:
    """A user's personalised dashboard layout.

    Attributes:
        user_id: The owner of this layout.
        dashboard_id: The base dashboard being personalised.
        placements: Ordered list of widget placements.
        hidden_widgets: Widget IDs the user has hidden.
        cols: Total number of grid columns (default 12 — Bootstrap-style).
    """

    user_id: str
    dashboard_id: str = "default"
    placements: list[WidgetPlacement] = field(default_factory=list)
    hidden_widgets: list[str] = field(default_factory=list)
    cols: int = 12

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a JSON-safe dict."""
        return {
            "user_id": self.user_id,
            "dashboard_id": self.dashboard_id,
            "placements": [p.to_dict() for p in self.placements],
            "hidden_widgets": list(self.hidden_widgets),
            "cols": self.cols,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UserDashboardLayout:
        """Deserialise from a dict."""
        return cls(
            user_id=data["user_id"],
            dashboard_id=data.get("dashboard_id", "default"),
            placements=[
                WidgetPlacement.from_dict(p) for p in data.get("placements", [])
            ],
            hidden_widgets=list(data.get("hidden_widgets", [])),
            cols=data.get("cols", 12),
        )


class UserDashboardService:
    """Manages per-user personalised dashboard layouts.

    Args:
        builder: The shared :class:`~lexigram.admin.services.dashboard.DashboardBuilder`
            that holds widget registrations and base configs.
        default_dashboard_id: The dashboard ID to clone when a user has no
            custom layout yet (default ``"default"``).
    """

    def __init__(
        self, builder: Any = None, default_dashboard_id: str = "default"
    ) -> None:
        self._builder = builder
        self._default_id = default_dashboard_id
        self._layouts: dict[str, UserDashboardLayout] = {}

    # ------------------------------------------------------------------
    # Layout retrieval / creation
    # ------------------------------------------------------------------

    async def get_or_create(self, user_id: str) -> UserDashboardLayout:
        """Return the user's layout, creating a default one if none exists.

        Args:
            user_id: User identifier.

        Returns:
            :class:`UserDashboardLayout` for the user.
        """
        if user_id not in self._layouts:
            layout = UserDashboardLayout(user_id=user_id, dashboard_id=self._default_id)
            # Copy placements from base dashboard if available
            if self._builder:
                base = await self._builder.get_dashboard(self._default_id)
                if base:
                    for i, widget in enumerate(base.widgets):
                        layout.placements.append(
                            WidgetPlacement(
                                widget_id=widget.id,
                                col=0,
                                row=i,
                            )
                        )
            self._layouts[user_id] = layout
        return self._layouts[user_id]

    def get_layout(self, user_id: str) -> UserDashboardLayout | None:
        """Return the user's layout if it exists, ``None`` otherwise.

        Args:
            user_id: User identifier.
        """
        return self._layouts.get(user_id)

    # ------------------------------------------------------------------
    # Widget management
    # ------------------------------------------------------------------

    async def add_widget(
        self,
        user_id: str,
        widget_type: str,
        config: dict[str, Any] | None = None,
        *,
        col: int = 0,
        row: int = 0,
        col_span: int = 1,
        row_span: int = 1,
        widget_id: str | None = None,
    ) -> WidgetPlacement:
        """Add a widget to the user's layout at the given grid position.

        Args:
            user_id: User identifier.
            widget_type: Widget type slug (e.g. ``"stat_card"``).
            config: Widget configuration passed to the renderer.
            col: Grid column index.
            row: Grid row index.
            col_span: Column span.
            row_span: Row span.
            widget_id: Optional explicit widget ID.  Auto-generated if omitted.

        Returns:
            The created :class:`WidgetPlacement`.
        """
        layout = await self.get_or_create(user_id)

        # Add widget to base dashboard if builder is available
        if self._builder:
            await self._builder.add_widget(
                layout.dashboard_id,
                widget_type,
                config or {},
                widget_id=widget_id,
            )
            # Use the last widget id from the base dashboard
            base = await self._builder.get_dashboard(layout.dashboard_id)
            if base and base.widgets:
                widget_id = base.widgets[-1].id

        if not widget_id:
            import uuid

            widget_id = str(uuid.uuid4())[:8]

        placement = WidgetPlacement(
            widget_id=widget_id,
            col=col,
            row=row,
            col_span=col_span,
            row_span=row_span,
        )
        layout.placements.append(placement)
        logger.debug(
            "User %s added widget %s at col=%d row=%d", user_id, widget_id, col, row
        )
        return placement

    async def remove_widget(self, user_id: str, widget_id: str) -> bool:
        """Remove a widget from the user's layout.

        Args:
            user_id: User identifier.
            widget_id: Widget to remove.

        Returns:
            ``True`` if removed, ``False`` if not found.
        """
        layout = self._layouts.get(user_id)
        if layout is None:
            return False
        before = len(layout.placements)
        layout.placements = [p for p in layout.placements if p.widget_id != widget_id]
        return len(layout.placements) < before

    async def move_widget(
        self,
        user_id: str,
        widget_id: str,
        *,
        col: int,
        row: int,
    ) -> bool:
        """Update the grid position of a widget.

        Args:
            user_id: User identifier.
            widget_id: Widget to move.
            col: New column index.
            row: New row index.

        Returns:
            ``True`` if moved, ``False`` if widget not found.
        """
        layout = self._layouts.get(user_id)
        if layout is None:
            return False
        for p in layout.placements:
            if p.widget_id == widget_id:
                p.col = col
                p.row = row
                return True
        return False

    async def resize_widget(
        self,
        user_id: str,
        widget_id: str,
        *,
        col_span: int,
        row_span: int,
    ) -> bool:
        """Update the span of a widget.

        Args:
            user_id: User identifier.
            widget_id: Widget to resize.
            col_span: New column span.
            row_span: New row span.

        Returns:
            ``True`` if resized, ``False`` if widget not found.
        """
        layout = self._layouts.get(user_id)
        if layout is None:
            return False
        for p in layout.placements:
            if p.widget_id == widget_id:
                p.col_span = col_span
                p.row_span = row_span
                return True
        return False

    async def hide_widget(self, user_id: str, widget_id: str) -> None:
        """Mark a widget as hidden for the user.

        Args:
            user_id: User identifier.
            widget_id: Widget to hide.
        """
        layout = await self.get_or_create(user_id)
        if widget_id not in layout.hidden_widgets:
            layout.hidden_widgets.append(widget_id)

    async def show_widget(self, user_id: str, widget_id: str) -> None:
        """Un-hide a previously hidden widget.

        Args:
            user_id: User identifier.
            widget_id: Widget to show.
        """
        layout = self._layouts.get(user_id)
        if layout:
            layout.hidden_widgets = [w for w in layout.hidden_widgets if w != widget_id]

    # ------------------------------------------------------------------
    # Reset / export / import
    # ------------------------------------------------------------------

    async def reset(self, user_id: str) -> None:
        """Reset a user's layout to the default (discards customisation).

        Args:
            user_id: User identifier.
        """
        self._layouts.pop(user_id, None)
        logger.info("Dashboard layout reset for user %s", user_id)

    def export_layout(self, user_id: str) -> dict[str, Any] | None:
        """Export a user's layout as a JSON-safe dict.

        Args:
            user_id: User identifier.

        Returns:
            Layout dict or ``None`` if user has no layout.
        """
        layout = self._layouts.get(user_id)
        return layout.to_dict() if layout else None

    def import_layout(self, data: dict[str, Any]) -> UserDashboardLayout:
        """Import a layout from a dict (e.g. previously exported).

        Overwrites any existing layout for the user.

        Args:
            data: Dict produced by :meth:`export_layout`.

        Returns:
            The imported :class:`UserDashboardLayout`.
        """
        layout = UserDashboardLayout.from_dict(data)
        self._layouts[layout.user_id] = layout
        return layout


__all__ = [
    "UserDashboardLayout",
    "UserDashboardService",
    "WidgetPlacement",
]
