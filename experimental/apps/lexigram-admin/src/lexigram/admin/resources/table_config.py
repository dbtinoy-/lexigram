"""Table, form-display, and layout configuration helpers for Admin Resources.

Resolves the effective table configuration (columns, actions, filters,
sorting, empty-state copy) from the optional fluent ``config`` object with
fallback to class attributes. Composed into
:class:`~lexigram.admin.resources.base.Resource` via inheritance so
``get_table_config()`` and friends remain part of every resource's public
surface.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.admin.resources.config import TableConfiguration

if TYPE_CHECKING:
    from lexigram.admin.actions.base import HeaderAction
    from lexigram.admin.layout.layout_manager import LayoutManager
    from lexigram.admin.ui.filters.base import Filter
    from lexigram.ui.actions import Action, BulkAction
    from lexigram.ui.columns import Column


class TableConfigMixin:
    """Configuration resolvers for tables, form display, and layouts.

    Requires the composing class to provide the declarative class
    attributes (defined by
    :class:`~lexigram.admin.resources.base.Resource`).
    """

    config: Any
    label: str | None
    page_size: int
    default_sort: str | None
    action_layout: str
    columns: list[Column]
    actions: list[Action]
    header_actions: list[HeaderAction]
    bulk_actions: list[BulkAction]
    filters: list[Filter]
    group_by: str | None
    empty_state_title: str | None
    empty_state_message: str | None
    empty_state_icon: str | None
    form_display_mode: str

    @classmethod
    def get_table_config(cls) -> TableConfiguration:
        """Get the table configuration for this resource.

        Returns:
            TableConfiguration with columns, actions, filters
        """
        cfg = cls.config

        # Resolve configuration with priority: Config Object > Class Attribute
        per_page = (
            cls._get_config_value(cfg, "per_page", cls.page_size)
            if cfg
            else cls.page_size
        )
        default_sort = (
            cls._get_config_value(
                cfg,
                "default_sort_field",
                cls.default_sort,
            )
            if cfg
            else cls.default_sort
        )
        default_sort_order = (
            cls._get_config_value(cfg, "default_sort_order", "asc") if cfg else "asc"
        )
        action_layout = (
            cls._get_config_value(cfg, "action_layout", cls.action_layout)
            if cfg
            else cls.action_layout
        )

        resource_name = cls.label or cls.__name__.replace("Resource", "")
        if cfg and cfg.display_name:
            resource_name = cfg.display_name

        columns = list(
            cls._get_config_value(cfg, "columns", cls.columns) if cfg else cls.columns
        )
        actions = list(
            cls._get_config_value(cfg, "actions", cls.actions) if cfg else cls.actions
        )
        filters = list(
            cls._get_config_value(cfg, "filters_list", cls.filters)
            if cfg
            else cls.filters
        )

        # Check class attribute `layout_type` as fallback for legacy resources
        layout_fallback = getattr(cls, "layout_type", "stack")
        default_layout = (
            cls._get_config_value(cfg, "layout", layout_fallback)
            if cfg
            else layout_fallback
        )
        # Check class attribute `data_view` as fallback for legacy resources
        view_fallback = getattr(cls, "data_view", "tabular")
        default_view = (
            cls._get_config_value(cfg, "view", view_fallback) if cfg else view_fallback
        )

        empty_state_title = (
            cls._get_config_value(cfg, "empty_state_title", cls.empty_state_title)
            if cfg
            else cls.empty_state_title
        )
        empty_state_message = (
            cls._get_config_value(cfg, "empty_state_message", cls.empty_state_message)
            if cfg
            else cls.empty_state_message
        )
        empty_state_icon = (
            cls._get_config_value(cfg, "empty_state_icon", cls.empty_state_icon)
            if cfg
            else cls.empty_state_icon
        )
        group_by = (
            cls._get_config_value(cfg, "group_by", cls.group_by)
            if cfg
            else cls.group_by
        )

        return TableConfiguration(
            columns=columns,
            actions=actions,
            header_actions=list(cls.header_actions),
            bulk_actions=list(cls.bulk_actions),
            filter_options=filters,
            per_page=per_page,
            default_sort_by=default_sort,
            default_sort_order=default_sort_order,
            resource_name=resource_name,
            action_layout=action_layout,
            default_layout=default_layout,
            default_view=default_view,
            empty_state_title=empty_state_title,
            empty_state_message=empty_state_message,
            empty_state_icon=empty_state_icon,
            group_by=group_by,
        )

    @classmethod
    def get_form_display_mode(cls) -> str:
        """Return the form display mode for create/edit views.

        Returns:
            Display mode: "page", "modal", or "slider"
        """
        cfg = cls.config
        return (
            cls._get_config_value(cfg, "form_display_mode", cls.form_display_mode)
            if cfg
            else cls.form_display_mode
        )

    @classmethod
    def get_layout_manager(cls) -> LayoutManager:
        """Get layout manager with configured views.

        Returns:
            LayoutManager instance
        """
        import contextlib

        from lexigram.admin.layout import LayoutManager
        from lexigram.admin.resources.layouts import apply_layout_config

        manager = LayoutManager()
        cfg = cls.config

        if cfg and cfg.views_list:
            for view in cfg.views_list:
                if hasattr(view, "to_config"):
                    layout_config = view.to_config()
                    apply_layout_config(manager, layout_config)

            # Set default view
            if cfg.view:
                with contextlib.suppress(ValueError):
                    manager.set_default(cfg.view)

        return manager

    @staticmethod
    def _get_config_value(cfg: Any, attr: str, default: Any) -> Any:
        """Get configuration value with fallback to default or private attribute.

        Args:
            cfg: Configuration object
            attr: Attribute name
            default: Default value if not found

        Returns:
            Configuration value or default
        """
        if cfg is None:
            return default

        # Try public attribute/property
        val = getattr(cfg, attr, None)

        # If it's the fluent method (callable) or missing, try the private attribute
        if val is None or callable(val):
            val = getattr(cfg, f"_{attr}", None)

        return val if val is not None else default


__all__ = ["TableConfigMixin"]
