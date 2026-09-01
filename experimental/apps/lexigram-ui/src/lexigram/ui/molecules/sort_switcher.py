"""Sort dropdown switcher for DataTable views without column headers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.ui import Component, HTMXAttrs, Zones, el

if TYPE_CHECKING:
    from lexigram.ui.state import TableState


def _column_name(column: Any) -> str | None:
    """Return a column's field name, or ``None`` if it cannot be addressed."""
    name = getattr(column, "name", None)
    if name:
        return str(name)
    return None


def _column_label(column: Any) -> str:
    """Resolve a display label from a column object."""
    label = getattr(column, "label", None)
    if label:
        return str(label)
    name = _column_name(column)
    if name:
        return name.replace("_", " ").title()
    return str(column)


def _is_sortable(column: Any) -> bool:
    """Return whether *column* participates in table sorting."""
    is_sortable = getattr(column, "is_sortable", None)
    if isinstance(is_sortable, bool):
        return is_sortable
    if callable(is_sortable):
        try:
            return bool(is_sortable())
        except TypeError:
            return False
    if hasattr(column, "sortable"):
        return bool(column.sortable)
    return bool(getattr(column, "_sortable", False))


class SortSwitcher(Component):
    """Sort dropdown for DataTable views that have no column headers.

    Tabular views sort from the ``<th>`` buttons. Grid and stacked views
    expose the same ``sort_by`` / ``sort_order`` state through this
    compact dropdown so sorter, search, and filters stay wired regardless
    of ``data_view``.

    Args:
        current: Currently sorted column name.
        current_order: ``\"asc\"`` or ``\"desc\"``.
        resource_prefix: Resource URL prefix for HTMX requests.
        columns: Table columns; only sortable ones are listed.
        state: Optional :class:`TableState` used to bake the request URL.
        **props: Additional element properties.
    """

    def __init__(
        self,
        current: str | None = None,
        current_order: str = "asc",
        resource_prefix: str | None = None,
        columns: list[Any] | None = None,
        state: TableState | None = None,
        **props: Any,
    ) -> None:
        super().__init__(**props)
        self.current = current or None
        self.current_order = (
            current_order if current_order in ("asc", "desc") else "asc"
        )
        self.resource_prefix = resource_prefix or ""
        self.columns = [col for col in (columns or []) if _is_sortable(col)]
        self.state = state

    def render(self) -> Any:
        if not self.columns:
            return ""

        items = [self._clear_item(), *[self._column_item(col) for col in self.columns]]
        trigger_label = self._trigger_label()

        trigger_el = el(
            "span",
            trigger_label,
            class_=(
                "inline-flex items-center justify-center px-2 py-1 rounded-md "
                "hover:bg-muted dark:hover:bg-card transition-colors text-sm h-8"
            ),
            role="button",
            tabindex="0",
            aria_label=trigger_label,
            **{"aria-haspopup": "menu"},
        )

        return el(
            "div",
            el(
                "details",
                el("summary", trigger_el, class_="list-none cursor-pointer"),
                el(
                    "div",
                    *items,
                    class_=(
                        "absolute left-0 mt-2 w-48 bg-card rounded-md shadow-lg "
                        "ring-1 ring-border z-[100] py-1 focus:outline-none "
                        "origin-top-left"
                    ),
                ),
                class_="relative inline-block",
            ),
            el("span", "", class_="hidden sort-switcher-marker"),
            class_="sort-switcher inline-block text-sm",
        )

    def _trigger_label(self) -> str:
        if not self.current:
            return "Sort"
        for column in self.columns:
            if _column_name(column) == self.current:
                arrow = "↑" if self.current_order == "asc" else "↓"
                return f"Sort: {_column_label(column)} {arrow}"
        return "Sort"

    def _clear_item(self) -> Any:
        attrs = self._item_attrs(column_name=None, selected=self.current is None)
        return el("a", "No sorting", **attrs)

    def _column_item(self, column: Any) -> Any:
        name = _column_name(column)
        selected = name == self.current
        label = _column_label(column)
        if selected:
            arrow = "↑" if self.current_order == "asc" else "↓"
            label = f"{label} {arrow}"
        attrs = self._item_attrs(column_name=name, selected=selected)
        return el("a", label, **attrs)

    def _item_attrs(self, column_name: str | None, *, selected: bool) -> dict[str, Any]:
        attrs: dict[str, Any] = {
            "class": (
                "block px-3 py-2 text-sm text-foreground hover:bg-muted "
                "dark:text-foreground dark:hover:bg-muted flex items-center gap-2"
            ),
        }
        if self.state:
            if column_name is None:
                updated_state = self.state.clear_sort()
            else:
                updated_state = self.state.with_sort(column_name)
            htmx_attrs = HTMXAttrs.for_data_refresh(
                updated_state,
                self.resource_prefix,
                push_url=True,
            )
            for key, val in htmx_attrs.items():
                attrs[key.replace("-", "_")] = val
        else:
            prefix = self.resource_prefix.rstrip("/")
            if column_name is None:
                query = ""
            else:
                next_order = (
                    "desc" if selected and self.current_order == "asc" else "asc"
                )
                query = f"?sort_by={column_name}&sort_order={next_order}"
            attrs.update(
                {
                    "hx_get": f"{prefix}/{query}",
                    "hx_target": Zones.DATA.selector,
                    "hx_swap": "outerHTML",
                    "hx_select": Zones.DATA.selector,
                    "hx_select_oob": Zones.data_refresh_oob_select(),
                    "hx_params": "none",
                    "hx_push_url": "true",
                },
            )

        if selected:
            attrs["aria-current"] = "true"
            attrs["class"] = (
                "block px-3 py-2 text-sm font-medium bg-muted text-foreground "
                "cursor-default pointer-events-none flex items-center gap-2"
            )
            for key in (
                "href",
                "hx_get",
                "hx_target",
                "hx_swap",
                "hx_select",
                "hx_select_oob",
                "hx_include",
                "hx_push_url",
                "hx_params",
                "hx_boost",
            ):
                attrs.pop(key, None)
        return attrs


__all__ = ["SortSwitcher"]
