"""View strategy handling for data table component."""

from __future__ import annotations

from typing import Any

from lexigram.admin.config import TableConfiguration
from lexigram.primitives.registry import StrategyRegistry
from lexigram.ui import TableState


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
        next_cursor: str | None = None,
    ):
        self.data = data
        self.config = config
        self.state = state
        self.total = total
        self.summary = summary
        self.user = user
        self.resource_name = resource_name
        self.next_cursor = next_cursor

    def render(self) -> Any:
        """Render the view."""
        raise NotImplementedError


class ViewStrategyRegistry(StrategyRegistry):
    """Registry of data-table view strategies, keyed by view name.

    Built-in strategies (``tabular``, ``grid``, ``calendar``, ``stacked``)
    are declared in :meth:`default_strategies`; applications can register
    additional views (or override a built-in) at build time::

        admin.views.register("kanban", KanbanView)

    Unknown view names resolve to ``tabular`` via :meth:`create_view`, so a
    stale ``data_view`` state value never renders a blank table.
    """

    def __init__(self) -> None:
        """Initialize the view strategy registry."""
        super().__init__(name="admin.data_table.views", allow_overwrite=True)

    @classmethod
    def default_strategies(cls) -> dict[str, type]:
        """Declare the complete built-in view strategy set."""
        # Local imports: the concrete views live under organisms.table.views
        # and importing them at module load would create a cycle with the
        # abstract data view base they share.
        from lexigram.admin.ui.organisms.table.views.calendar import CalendarView
        from lexigram.admin.ui.organisms.table.views.grid import GridView
        from lexigram.admin.ui.organisms.table.views.stacked import StackedView
        from lexigram.admin.ui.organisms.table.views.tabular import TabularView

        return {
            "tabular": TabularView,
            "grid": GridView,
            "calendar": CalendarView,
            "stacked": StackedView,
        }

    def create_view(
        self,
        view_type: str,
        data: list[dict],
        config: TableConfiguration,
        state: TableState,
        total: int | None,
        summary: dict[str, Any] | None = None,
        user: Any = None,
        resource_name: str | None = None,
        next_cursor: str | None = None,
    ) -> ViewStrategy:
        """Instantiate the strategy for *view_type*, falling back to tabular.

        Args:
            view_type: Strategy key (e.g. ``"tabular"``, ``"calendar"``).
            data: Rows to render.
            config: Table configuration.
            state: Table state (view, filters, pagination).
            total: Total record count.
            summary: Optional summary payload for footers.
            user: Authenticated user (for permission-aware actions).
            resource_name: Resource name (for permission-aware actions).
            next_cursor: Cursor used by infinite-scroll views.

        Returns:
            A view strategy instance. Unknown *view_type* values fall back
            to the ``tabular`` strategy so stale state never breaks render.
        """
        key = view_type if self.has(view_type) else "tabular"
        total_count: int = total if total is not None else 0
        return self.instantiate(
            key,
            data=data,
            config=config,
            state=state,
            total=total_count,
            summary=summary,
            user=user,
            resource_name=resource_name,
            next_cursor=next_cursor,
        )


#: Default registry instance used by the data table renderer.
view_strategy_registry: ViewStrategyRegistry = ViewStrategyRegistry.with_defaults()


__all__ = [
    "ViewStrategy",
    "ViewStrategyRegistry",
    "view_strategy_registry",
]
