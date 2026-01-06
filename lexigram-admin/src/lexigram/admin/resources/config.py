"""Admin resource and table configuration types.

Provides :class:`TableConfiguration` (static DataTable config) and
:class:`ResourceConfig` (fluent builder for resource metadata).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from lexigram.domain import DomainModel
from lexigram.validation import ConfigDict, Field

__all__ = ["ResourceConfig", "TableConfiguration"]


@dataclass(init=False)
class TableConfiguration(DomainModel):
    """Static configuration for a DataTable."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    columns: list[Any] = Field(default_factory=list)
    actions: list[Any] = Field(default_factory=list)
    header_actions: list[Any] = Field(default_factory=list)
    bulk_actions: list[Any] = Field(default_factory=list)
    filter_options: Any | None = None
    default_view: str = "tabular"
    default_layout: str = "stack"
    action_layout: Literal["horizontal", "stack"] = "horizontal"
    default_sort_by: str | None = None
    default_sort_order: str = "asc"
    per_page: int = 20
    enable_search: bool = True
    search_fields: list[str] | None = None
    reorderable_columns: bool = False
    group_by: str | None = None
    resource_name: str | None = None
    resource_prefix: str | None = None
    expandable_relationship: str | None = None
    density: str = "normal"

    @property
    def filters(self) -> Any | None:
        """Alias for ``filter_options`` used by the toolbar renderer."""
        return self.filter_options

    @property
    def density_css_class(self) -> str:
        """CSS class for current density setting."""
        return f"table-density-{self.density}"

    @property
    def density_row_height(self) -> str:
        """Row height in px for current density."""
        heights = {"compact": "32px", "normal": "48px", "comfortable": "64px"}
        return heights.get(self.density, "48px")


class ResourceConfig:
    """Fluent configuration builder for Resource metadata."""

    def __init__(self) -> None:
        self._layout: str = "sidebar"
        self._view: str = "tabular"
        self._per_page: int = 20
        self._default_sort_field: str | None = None
        self._default_sort_order: str = "asc"
        self._display_name: str | None = None
        self._description: str | None = None
        self._icon: str = "box"
        self._expandable: bool = False
        self._record_title_func: Any = None
        self._columns: list[Any] = []
        self._actions: list[Any] = []
        self._filters_list: list[Any] = []
        self._views_list: list[Any] = []
        self._action_layout: str = "horizontal"
        self._form_display_mode: str = "modal"
        self._name: str | None = None
        self._group: str | None = None
        self._group_label: str | None = None
        self._group_icon: str | None = None
        self._group_order: int | None = None

    @staticmethod
    def builder() -> ResourceConfig:
        """Return a new :class:`ResourceConfig` builder instance."""
        return ResourceConfig()

    def layout(self, layout: Literal["sidebar", "stack"]) -> ResourceConfig:
        """Set the resource layout."""
        self._layout = layout
        return self

    def name(self, name: str) -> ResourceConfig:
        """Set the resource registration name."""
        self._name = name
        return self

    def group(
        self,
        group: str,
        *,
        label: str | None = None,
        icon: str | None = None,
        order: int | None = None,
    ) -> ResourceConfig:
        """Set the navigation group this resource belongs to.

        Args:
            group: Navigation group key.
            label: Group display label (used when auto-creating the group).
            icon: Group icon (used when auto-creating the group).
            order: Group sort order (used when auto-creating the group).
        """
        self._group = group
        if label is not None:
            self._group_label = label
        if icon is not None:
            self._group_icon = icon
        if order is not None:
            self._group_order = order
        return self

    def view(self, view: Literal["tabular", "grid", "kanban"] | Any) -> ResourceConfig:
        """Set the default view."""
        self._view = str(view) if hasattr(view, "__str__") else "tabular"
        return self

    def views(self, views: list[Any]) -> ResourceConfig:
        """Add multiple view definitions."""
        self._views_list.extend(views)
        return self

    def per_page(self, count: int) -> ResourceConfig:
        """Set items per page."""
        self._per_page = max(1, count)
        return self

    def sort(self, field: str, order: Literal["asc", "desc"] = "asc") -> ResourceConfig:
        """Set the default sort field and order."""
        self._default_sort_field = field
        self._default_sort_order = order if order in ("asc", "desc") else "asc"
        return self

    def label(self, label: str) -> ResourceConfig:
        """Set the display label."""
        self._display_name = label
        return self

    def resource_name(self, name: str) -> ResourceConfig:
        """Set the resource name (alias for label)."""
        self._display_name = name
        return self

    def icon(self, icon: str) -> ResourceConfig:
        """Set the icon name."""
        self._icon = icon
        return self

    def description(self, description: str) -> ResourceConfig:
        """Set the resource description."""
        self._description = description
        return self

    def record_title(self, func: Any) -> ResourceConfig:
        """Set the record title function."""
        self._record_title_func = func
        return self

    def column(self, col: Any) -> ResourceConfig:
        """Add a single column definition."""
        self._columns.append(col)
        return self

    def columns(self, cols: list[Any]) -> ResourceConfig:
        """Add multiple column definitions."""
        self._columns.extend(cols)
        return self

    def action(self, action: Any) -> ResourceConfig:
        """Add a single action."""
        self._actions.append(action)
        return self

    def actions(self, actions: list[Any]) -> ResourceConfig:
        """Add multiple actions."""
        self._actions.extend(actions)
        return self

    def filter(self, filter_obj: Any) -> ResourceConfig:
        """Add a single filter."""
        self._filters_list.append(filter_obj)
        return self

    def filters(self, filters: list[Any]) -> ResourceConfig:
        """Add multiple filters."""
        self._filters_list.extend(filters)
        return self

    def action_layout(self, layout: Literal["horizontal", "stack"]) -> ResourceConfig:
        """Set the action layout direction."""
        self._action_layout = layout
        return self

    def form_display_mode(
        self, mode: Literal["page", "modal", "slider"]
    ) -> ResourceConfig:
        """Set how forms are displayed."""
        if mode in ("page", "modal", "slider"):
            self._form_display_mode = mode
        return self

    @property
    def display_name(self) -> str | None:
        """Return the configured display name."""
        return self._display_name

    @property
    def default_sort_field(self) -> str | None:
        """Return the configured sort field."""
        return self._default_sort_field

    @property
    def default_sort_order(self) -> str:
        """Return the configured sort order."""
        return self._default_sort_order

    @property
    def filters_list(self) -> list[Any]:
        """Return the configured filters."""
        return self._filters_list

    @property
    def views_list(self) -> list[Any]:
        """Return the configured views."""
        return self._views_list
