"""View strategy handling for data table component."""

from __future__ import annotations

from typing import Any

from lexigram.admin.config import TableConfiguration
from lexigram.admin.ui.state import TableState


class ViewStrategy:
    """Base class for view strategies."""

    def __init__(
        self,
        data: list[dict],
        config: TableConfiguration,
        state: TableState,
        total: int | None,
        summary: dict[str, Any] | None = None,
        user: Any = None,
        resource_name: str | None = None,
    ):
        self.data = data
        self.config = config
        self.state = state
        self.total = total
        self.summary = summary
        self.user = user
        self.resource_name = resource_name

    def render(self) -> Any:
        """Render the view."""
        raise NotImplementedError


class ViewFactory:
    """Factory for creating view strategies."""

    @staticmethod
    def create_view(
        view_type: str,
        data: list[dict],
        config: TableConfiguration,
        state: TableState,
        total: int | None,
        summary: dict[str, Any] | None = None,
        user: Any = None,
        resource_name: str | None = None,
    ) -> ViewStrategy:
        """Create a view strategy instance."""
        total_count: int = total if total is not None else 0
        if view_type == "tabular":
            from lexigram.admin.ui.organisms.table.views.tabular import TabularView

            return TabularView(
                data, config, state, total_count, summary, user, resource_name
            )  # type: ignore[return-value]
        if view_type == "grid":
            from lexigram.admin.ui.organisms.table.views.grid import GridView

            return GridView(
                data, config, state, total_count, summary, user, resource_name
            )  # type: ignore[return-value]
        if view_type == "calendar":
            from lexigram.admin.ui.organisms.table.views.calendar import CalendarView

            return CalendarView(  # type: ignore[return-value]
                data,
                config,
                state,
                total_count,
                summary,
                user,
                resource_name,
            )
        if view_type == "stacked":
            from lexigram.admin.ui.organisms.table.views.stacked import StackedView

            return StackedView(
                data, config, state, total_count, summary, user, resource_name
            )  # type: ignore[return-value]
        # Default to tabular
        from lexigram.admin.ui.organisms.table.views.tabular import TabularView

        return TabularView(
            data, config, state, total_count, summary, user, resource_name
        )  # type: ignore[return-value]
