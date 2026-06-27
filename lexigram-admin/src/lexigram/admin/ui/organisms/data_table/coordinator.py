"""Data table coordinator component."""

from __future__ import annotations

from typing import Any

from lexigram.admin.config import TableConfiguration
from lexigram.admin.ui.organisms.data_table.actions import ActionManager
from lexigram.admin.ui.organisms.data_table.rendering import DataTableRenderer
from lexigram.ui import Component, TableState


class DataTable(Component):
    """
    Main DataTable Coordinator.
    Handles configuration, state management, and dispatches rendering to specific views.
    """

    def __init__(
        self,
        columns: list | None = None,
        data: list[dict] | None = None,
        state: TableState | None = None,
        config: TableConfiguration | None = None,
        # Legacy params
        page: int = 1,
        per_page: int = 20,
        total: int | None = None,
        filters: dict | None = None,
        resource_prefix: str | None = None,
        sort_by: str | None = None,
        sort_order: str = "asc",
        actions: list | None = None,
        header_actions: list | None = None,
        bulk_actions: list | None = None,
        filter_options: dict | None = None,
        layout_type: str | None = None,
        data_view: str | None = None,
        next_cursor: str | None = None,
        summary: dict[str, Any] | None = None,
        **props,
    ) -> None:
        super().__init__(**props)

        # Resolve Configuration
        if config:
            self.config = config
        else:
            self.config = TableConfiguration(
                columns=columns or [],
                actions=actions or [],
                header_actions=header_actions or [],
                bulk_actions=bulk_actions or [],
                filter_options=filter_options,
                resource_prefix=resource_prefix,
                resource_name=props.get("resource_name"),
                default_view=data_view or "tabular",
                default_layout=layout_type or "stack",
                default_sort_by=sort_by,
                default_sort_order=sort_order,
            )

        # Resolve State
        if state:
            self.state = state
        else:
            self.state = TableState(
                search=filters.get("search", "") if filters else "",
                sort_by=sort_by,
                sort_order=sort_order,
                page=page,
                per_page=per_page,
                filters=filters or {},
                view=data_view or self.config.default_view,
                layout=layout_type or self.config.default_layout,
            )

        self.data = data or []
        self.total = total
        self.user = props.get("user")
        self.loading = props.get("loading", False)
        self.error = props.get("error")
        self.next_cursor = next_cursor
        self.summary = summary
        self.props = props

        # Permission state: no permission service is bound at construction
        # time in the framework; async callers may hoist checks via
        # PermissionManager and inject the resulting dict here.
        self.permissions = (
            props.get("permissions")
            or {
                "can_view": True,
                "can_create": True,
                "can_update": True,
                "can_delete": True,
            }
        )

        # Configure actions
        self.action_manager = ActionManager(self.config, self.permissions)
        self.action_manager.configure_actions()

        # Show delete based on permissions
        self.show_delete = (
            props.get("show_delete", True) and self.permissions["can_delete"]
        )

    def render(self) -> Any:
        """Render the data table using the modular renderer."""
        renderer = DataTableRenderer(
            data=self.data,
            config=self.config,
            state=self.state,
            total=self.total,
            user=self.user,
            loading=self.loading,
            error=self.error,
            next_cursor=self.next_cursor,
            summary=self.summary,
            props=self.props,
        )
        return renderer.render()


__all__ = ["DataTable"]
