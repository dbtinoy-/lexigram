from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from lexigram.admin.ui.organisms.table.views.tabular_header import render_table_header
from lexigram.admin.ui.organisms.table.views.tabular_rows import render_table_rows
from lexigram.admin.ui.organisms.table.views.tabular_summary import (
    effective_summary,
    render_table_footer,
)
from lexigram.ui import el

HEADER_HEIGHT = 50


class AbstractDataView(ABC):
    """Abstract Strategy for Data Visualization."""

    def __init__(
        self,
        data: list[dict],
        config: Any,
        state: Any,
        total: int = 0,
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

        # Apply column ordering if present in state
        if self.state.column_order:
            ordered_cols = []
            col_map = {col.name: col for col in self.config.columns}
            for name in self.state.column_order:
                if name in col_map:
                    ordered_cols.append(col_map.pop(name))
            # Append any remaining columns not in the order list
            ordered_cols.extend(col_map.values())
            self.config.columns = ordered_cols

    @abstractmethod
    def render(self) -> Any:
        pass


class TabularView(AbstractDataView):
    """Render data as a standard HTML Table."""

    def render(self) -> Any:
        thead = self.render_header()
        tbody = el(
            "tbody",
            *self.render_rows(),
            class_="bg-card divide-y divide-border",
        )
        tfoot = (
            self.render_summary(self.effective_summary())
            if self.effective_summary()
            else ""
        )

        density_class = getattr(
            self.config, "density_css_class", "table-density-normal"
        )

        table_el = el(
            "table",
            thead,
            tbody,
            tfoot,
            class_="min-w-full divide-y divide-border border-separate border-spacing-0",
            style="table-layout: auto; min-width: 100%; width: max-content;",
        )

        return el(
            "div",
            table_el,
            class_=f"overflow-x-auto overflow-y-auto shadow-sm ring-1 ring-border dark:ring-border rounded-lg bg-muted/50 {density_class}",
            style="max-height: min(70vh, calc(100vh - var(--admin-table-offset, 18rem))); min-height: 200px;",
        )

    def render_header(self) -> Any:
        return render_table_header(
            self.config,
            self.state,
            self.data,
            self.user,
            self.resource_name,
        )

    def render_rows(self) -> list[Any]:
        return render_table_rows(
            self.config,
            self.data,
            self.user,
            self.resource_name,
        )

    def effective_summary(self) -> dict[str, Any] | None:
        """Resolve footer summaries: explicit summary or per-column aggregates."""
        return effective_summary(self.data, self.config.columns, self.summary)

    def render_summary(self, summary: dict[str, Any] | None = None) -> Any:
        return render_table_footer(self.config, summary)
