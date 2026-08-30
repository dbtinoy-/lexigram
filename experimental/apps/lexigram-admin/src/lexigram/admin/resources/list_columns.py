"""Column-spec and action extraction for admin list views.

Builds the DataTable's reusable UI columns from resource configuration (or
auto-generates them from fetched items) and resolves filter, row, header,
and bulk action specs. Composed by :class:`ListRenderer`.
"""

from __future__ import annotations

from typing import Any

from lexigram.ui import Column as OrgColumn
from lexigram.ui import TextColumn


class SchemaFieldColumn(TextColumn):
    """Adapt a declarative admin ``SchemaField`` to a UI table column.

    ``Resource.fields`` is the single declarative source for form, filter, and
    list metadata. Passing those fields through the old fallback converted
    every value to plain text, losing boolean/date/relation renderers and
    searchable/sortable flags. This adapter keeps the UI Column protocol while
    delegating cell formatting and visibility to the field schema.
    """

    def __init__(self, field_schema: Any) -> None:
        super().__init__(
            field_schema.name,
            label=getattr(field_schema, "label", None),
        )
        self.field_schema = field_schema
        self._sortable = bool(getattr(field_schema, "sortable", True))
        self._searchable = bool(getattr(field_schema, "searchable", False))
        self._filterable = bool(getattr(field_schema, "filterable", False))
        self._toggleable = True

    def is_visible(self, **kwargs: Any) -> bool:
        """Honor declarative list visibility, including dynamic UI kwargs."""
        return bool(getattr(self.field_schema, "visible_in_list", True))

    def render(self, value: Any, record: dict) -> Any:
        """Delegate formatting to the schema field renderer."""
        return self.field_schema.render_column(record, value)


def build_columns(source_columns: Any, items: Any) -> list[Any]:
    """Build column definitions for the data table."""
    from lexigram.admin.schema import SchemaField
    from lexigram.admin.ui.filters.base import Filter

    columns: list[Any] = []
    # Auto-generate columns if missing (post-fetch)
    if not source_columns and items:
        first_item = items[0]
        item_dict = (
            first_item.model_dump()
            if hasattr(first_item, "model_dump")
            else (
                dict(first_item)
                if not isinstance(first_item, (str, int, float))
                else {"id": first_item}
            )
        )
        for key in list(item_dict.keys())[:6]:
            columns.append(
                TextColumn(name=key, label=key.replace("_", " ").title()),
            )
    else:
        # Convert or preserve columns
        for col in source_columns:
            if isinstance(col, Filter):
                continue
            if isinstance(col, SchemaField):
                columns.append(SchemaFieldColumn(col))
            elif hasattr(col, "render") or isinstance(col, OrgColumn):
                # Already a UI component/column
                columns.append(col)
            else:
                # Fallback for simple objects
                new_col = TextColumn(
                    name=getattr(col, "name", str(col)),
                    label=getattr(
                        col,
                        "label",
                        getattr(col, "name", str(col)).replace("_", " ").title(),
                    ),
                ).sortable(True)
                columns.append(new_col)

    return columns


def get_filter_options(table_config: Any, resource: Any) -> Any:
    """Get filter options from resource configuration."""
    filter_options = []
    if table_config and table_config.filter_options:
        filter_options = table_config.filter_options
    elif resource and hasattr(resource, "filter_options"):
        filter_options = (
            resource.filter_options
            if not callable(resource.filter_options)
            else resource.filter_options()
        )
    elif resource and hasattr(resource, "filters"):
        filter_options = (
            resource.filters if not callable(resource.filters) else resource.filters()
        )
    return filter_options


def get_row_actions(table_config: Any, resource: Any, resource_prefix: str) -> Any:
    """Get row actions from resource configuration."""
    row_actions = []
    if table_config and table_config.actions:
        row_actions = table_config.actions
    elif resource and hasattr(resource, "actions"):
        actions = (
            resource.actions if not callable(resource.actions) else resource.actions()
        )
        row_actions = list(actions)

    # Inject default URLs for standard legacy actions without mutating a
    # Resource's shared action instances. New admin actions resolve URLs from
    # ActionContext at render time and need no injection.
    from copy import copy

    from lexigram.ui.actions.standard import EditAction, ViewAction

    resolved_actions = []
    for action in row_actions:
        resolved = action
        if (
            isinstance(action, (EditAction, ViewAction))
            and not action.get_url()
            and not action.get_hx_get()
        ):
            resolved = copy(action)
            # Default logic: {prefix}/{id}/edit or {prefix}/{id}
            postfix = "/edit" if isinstance(action, EditAction) else ""

            # Use hx_get for partial updates (SlideOver/Modal)
            resolved.hx(get=f"{resource_prefix.rstrip('/')}/{{id}}{postfix}")
        resolved_actions.append(resolved)

    return resolved_actions


def get_header_actions(table_config: Any, resource: Any) -> Any:
    """Get header actions from resource configuration."""
    header_actions = []
    if (
        table_config
        and hasattr(table_config, "header_actions")
        and table_config.header_actions
    ):
        header_actions = table_config.header_actions
    elif resource and hasattr(resource, "header_actions"):
        header_actions = (
            resource.header_actions
            if not callable(resource.header_actions)
            else resource.header_actions()
        )
    return header_actions


def get_bulk_actions(table_config: Any, resource: Any) -> Any:
    """Get bulk actions from resource configuration."""
    bulk_actions_list = []
    source_bulk = []
    if table_config and table_config.bulk_actions:
        source_bulk = table_config.bulk_actions
    elif resource and hasattr(resource, "bulk_actions"):
        source_bulk = (
            resource.bulk_actions
            if not callable(resource.bulk_actions)
            else resource.bulk_actions()
        )

    # Keep both the legacy lexigram-ui action API and the canonical admin
    # action API. Dropping admin BulkAction instances here caused custom
    # resource declarations to disappear before the DataTable could render
    # them (and silently replaced them with the default delete action).
    from lexigram.admin.actions.base import BulkAction as AdminBulkAction
    from lexigram.ui.actions.standard import BulkAction as OrgBulkAction
    from lexigram.ui.actions.standard import DeleteBulkAction

    for ba in source_bulk:
        if isinstance(ba, (OrgBulkAction, AdminBulkAction)):
            bulk_actions_list.append(ba)
        elif ba == "delete_selected":
            bulk_actions_list.append(DeleteBulkAction(label="Delete Selected"))
        elif isinstance(ba, str):
            # Generic bulk action from string
            bulk_actions_list.append(
                OrgBulkAction(label=ba.replace("_", " ").title(), name=ba),
            )

    return bulk_actions_list


__all__ = [
    "SchemaFieldColumn",
    "build_columns",
    "get_bulk_actions",
    "get_filter_options",
    "get_header_actions",
    "get_row_actions",
]
