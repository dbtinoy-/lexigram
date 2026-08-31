"""Data table coordinator component."""

from __future__ import annotations

from typing import Any

from lexigram.admin.config import TableConfiguration
from lexigram.admin.resources.config import clone_table_configuration
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
        per_page: int | None = None,
        total: int | None = None,
        filters: dict | None = None,
        resource_prefix: str | None = None,
        sort_by: str | None = None,
        sort_order: str | None = None,
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

        # Resolve configuration into a request-local object. Resource table
        # configs are often class-level/shared; ActionManager and column
        # ordering are intentionally allowed to mutate only this copy.
        if config:
            self.config = clone_table_configuration(config)
            # ``resource_prefix`` is a legacy constructor argument and is
            # still commonly supplied by standalone table users. Do not let a
            # config without a route silently disable actions/HTMX controls.
            if resource_prefix is not None and not self.config.resource_prefix:
                self.config.resource_prefix = resource_prefix
            if props.get("resource_name") and not self.config.resource_name:
                self.config.resource_name = props["resource_name"]
        else:
            self.config = TableConfiguration(
                columns=list(columns or []),
                actions=list(actions or []),
                header_actions=list(header_actions or []),
                bulk_actions=list(bulk_actions or []),
                filter_options=filter_options,
                resource_prefix=resource_prefix,
                resource_name=props.get("resource_name"),
                default_view=data_view or "tabular",
                default_layout=layout_type or "stack",
                default_sort_by=sort_by,
                default_sort_order=sort_order or "asc",
                per_page=max(1, per_page if per_page is not None else 20),
            )

        # Resolve State. Config defaults are the source of truth when legacy
        # overrides are omitted, which keeps resource declarations effective
        # for both direct renders and request-driven renders.
        effective_sort_by = (
            sort_by if sort_by is not None else self.config.default_sort_by
        )
        effective_sort_order = (
            sort_order
            if sort_order in ("asc", "desc")
            else self.config.default_sort_order
        )
        effective_filters = dict(filters or {})
        legacy_search = effective_filters.pop("search", "")

        if state:
            self.state = state
        else:
            self.state = TableState(
                search=str(legacy_search or ""),
                sort_by=effective_sort_by,
                sort_order=effective_sort_order,
                page=max(1, page),
                per_page=max(
                    1,
                    per_page if per_page is not None else self.config.per_page,
                ),
                filters=effective_filters,
                view=data_view or self.config.default_view,
                layout=layout_type or self.config.default_layout,
                group_by=self.config.group_by,
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
        # PermissionManager and inject the resulting dict here. An explicitly
        # supplied partial/empty mapping fails closed instead of being treated
        # as an absent mapping.
        supplied_permissions = props.get("permissions")
        if supplied_permissions is None:
            self.permissions = {
                "can_view": True,
                "can_create": True,
                "can_update": True,
                "can_delete": True,
            }
        else:
            self.permissions = {
                permission: bool(supplied_permissions.get(permission, False))
                for permission in (
                    "can_view",
                    "can_create",
                    "can_update",
                    "can_delete",
                )
            }
        self.props["permissions"] = self.permissions

        # Configure actions on the request-local config. This must never alter
        # a Resource class's shared declaration.
        self.action_manager = ActionManager(self.config, self.permissions)
        self.action_manager.configure_actions()

        # Show delete based on permissions without assuming a complete mapping
        # was supplied by a custom permission adapter.
        self.show_delete = props.get("show_delete", True) and self.permissions.get(
            "can_delete", False
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
