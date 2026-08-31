"""Column visibility switcher for DataTable.

Renders a dropdown listing the table columns with a visibility toggle
per column. Toggling a column emits an HTMX full-table refresh carrying
the updated ``hide_cols`` query param through the :class:`TableState`,
so the choice is per-user, URL-addressable and shareable.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.ui import Component, HTMXAttrs, Zones, el

if TYPE_CHECKING:
    from lexigram.ui.state import TableState


def _column_label(column: Any) -> str:
    """Resolve a display label from a column object or plain string."""
    label = getattr(column, "label", None)
    if label:
        return str(label)
    name = getattr(column, "name", column)
    return str(name).replace("_", " ").title()


class ColumnVisibilitySwitcher(Component):
    """Column visibility dropdown for DataTable.

    Each column renders as a row with a check indicator; visible columns
    show a check icon, hidden columns an empty box. Rows are links that
    toggle the column through ``TableState.toggle_column`` and request a
    full table refresh, keeping all other table state (search, filters,
    sort, pagination) intact.

    Args:
        columns: Iterable of columns (objects exposing ``name``/``label``
            or plain strings).
        current_hidden: Column names currently hidden.
        resource_prefix: Resource URL prefix for HTMX requests.
        state: Optional :class:`TableState` used to build the updated
            state (and therefore the request URL).
        **props: Additional element properties.
    """

    def __init__(
        self,
        columns: list[Any] | None = None,
        current_hidden: list[str] | None = None,
        resource_prefix: str | None = None,
        state: TableState | None = None,
        **props: Any,
    ) -> None:
        super().__init__(**props)
        self.columns = list(columns or [])
        self.current_hidden = set(current_hidden or [])
        self.resource_prefix = resource_prefix or ""
        self.state = state

    def render(self) -> Any:
        from lexigram.ui import get_icon

        items = []
        for column in self.columns:
            name = getattr(column, "name", None)
            if not name:
                name = str(column)
            label = _column_label(column)
            is_hidden = name in self.current_hidden

            attrs: dict[str, Any] = {
                "class": (
                    "block px-3 py-2 text-sm text-foreground hover:bg-muted "
                    "dark:text-foreground dark:hover:bg-muted flex items-center gap-2"
                ),
                "role": "menuitemcheckbox",
                "aria-checked": "false" if is_hidden else "true",
                "title": f"{'Show' if is_hidden else 'Hide'} {label}",
            }

            if self.state:
                updated_state = self.state.toggle_column(name)
                htmx_attrs = HTMXAttrs.for_full_refresh(
                    updated_state,
                    self.resource_prefix,
                    push_url=True,
                )
                for key, val in htmx_attrs.items():
                    attrs[key.replace("-", "_")] = val
            else:
                attrs.update(
                    {
                        "hx_get": (
                            f"{self.resource_prefix.rstrip('/')}/?hide_cols={name}"
                        ),
                        "hx_target": Zones.TABLE.selector,
                        "hx_swap": "outerHTML",
                        "hx_params": "none",
                        "hx_push_url": "true",
                    },
                )

            indicator = (
                get_icon("check", size="h-4 w-4 text-primary-500")
                if not is_hidden
                else el(
                    "span",
                    class_="h-4 w-4 inline-block border border-border rounded-sm",
                )
            )

            items.append(el("a", indicator, label, **attrs))

        # Build a compact trigger inside the summary so clicks toggle
        # <details> reliably, with the current hidden-column count.
        hidden_count = len(self.current_hidden)
        trigger_label = "Columns"
        if hidden_count:
            trigger_label += f" ({hidden_count} hidden)"

        trigger_el = el(
            "span",
            get_icon(
                "columns-3",
                size="h-4 w-4 text-muted-foreground dark:text-foreground",
            ),
            el("span", trigger_label, class_="hidden lg:inline ml-1.5 text-xs"),
            class_=(
                "inline-flex items-center justify-center p-1 rounded-md "
                "hover:bg-muted dark:hover:bg-card transition-colors h-8 w-8 gap-0.5"
            ),
            role="button",
            tabindex="0",
            aria_label="Toggle column visibility",
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
                        "origin-top-left max-h-80 overflow-y-auto"
                    ),
                ),
                class_="relative inline-block",
            ),
            # Hidden marker for server-side presence detection
            el("span", "", class_="hidden column-visibility-switcher-marker"),
            class_="column-visibility-switcher inline-block text-sm",
        )


__all__ = ["ColumnVisibilitySwitcher"]
