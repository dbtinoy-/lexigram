"""State rendering for data table component (skeleton, error states)."""

from __future__ import annotations

from typing import Any

from lexigram.admin.config import TableConfiguration
from lexigram.ui import ActionButton, EmptyState, ErrorState, Skeleton, TableState, el


class StateRenderer:
    """Renders different states for data table (loading, error, empty)."""

    def __init__(self, config: TableConfiguration, state: TableState):
        self.config = config
        self.state = state

    def render_skeleton(self) -> Any:
        """Render loading skeleton."""
        skeleton_rows = []
        for _i in range(min(5, self.state.per_page)):
            cells = []
            if self.config.resource_prefix:
                cells.append(
                    el(
                        "td",
                        Skeleton(variant="rectangular", width="16px", height="16px"),
                        class_="px-3 sm:px-6 py-4",
                    ),
                )
            for _ in self.config.columns:
                cells.append(
                    el(
                        "td",
                        Skeleton(variant="text", width="80%"),
                        class_="px-3 sm:px-6 py-4",
                    ),
                )
            if self.config.resource_prefix:
                cells.append(
                    el(
                        "td",
                        Skeleton(variant="text", width="60px"),
                        class_="px-3 sm:px-6 py-4",
                    ),
                )
            skeleton_rows.append(
                el(
                    "tr",
                    *cells,
                    class_="border-b border-border",
                ),
            )
        return el(
            "div",
            el(
                "table",
                el("tbody", *skeleton_rows, class_="bg-card"),
                class_="w-full",
                aria_label="Loading data",
            ),
            aria_busy="true",
            class_="overflow-x-auto",
        )

    def render_error(self, error: Any) -> Any:
        """Render error state."""
        return ErrorState(
            title="Failed to load data",
            message=str(error),
            action=ActionButton(
                label="Retry",
                color="primary",
                onclick="window.location.reload()",
            ).render(),
        )

    def render_empty(self) -> Any:
        """Render empty state."""
        return EmptyState(
            title="No results found",
            message="Try adjusting your filters or search terms.",
            icon="🔍",
        )
