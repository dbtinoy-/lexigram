"""Grouping dropdown switcher for DataTable."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.ui import Component, HTMXAttrs, Zones, el

if TYPE_CHECKING:
    from lexigram.ui.state import TableState


class GroupBySwitcher(Component):
    """Grouping dropdown switcher for DataTable.

    Renders a compact dropdown listing the table columns as grouping
    options (plus "No grouping") and emits HTMX requests carrying the
    ``group_by`` query param through the updated :class:`TableState`.
    """

    def __init__(
        self,
        current: str | None = None,
        resource_prefix: str | None = None,
        columns: list[Any] | None = None,
        state: TableState | None = None,
        **props: Any,
    ) -> None:
        super().__init__(**props)
        self.current = current or None
        self.resource_prefix = resource_prefix or ""
        self.columns = columns or []
        self.state = state

    def render(self) -> Any:
        options: list[tuple[str | None, str]] = [(None, "No grouping")]
        options.extend((col.name, col.label) for col in self.columns)

        items = []
        for value, label in options:
            attrs = {
                "class": "block px-3 py-2 text-sm text-foreground hover:bg-muted dark:text-foreground dark:hover:bg-muted flex items-center gap-2",
            }

            if self.state:
                updated_state = self.state.with_group_by(value)
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
                            f"{self.resource_prefix.rstrip('/')}/"
                            f"?group_by={value if value else ''}"
                        ),
                        "hx_target": Zones.TABLE.selector,
                        "hx_swap": "outerHTML",
                        "hx_params": "none",
                        "hx_push_url": "false",
                    },
                )

            if value == self.current:
                attrs["aria-current"] = "true"
                attrs["class"] = (
                    "block px-3 py-2 text-sm font-medium bg-muted text-foreground cursor-default pointer-events-none flex items-center gap-2"
                )
                attrs.pop("href", None)
                attrs.pop("hx_get", None)
                attrs.pop("hx_target", None)
                attrs.pop("hx_swap", None)
                attrs.pop("hx_include", None)
                attrs.pop("hx_push_url", None)
                attrs.pop("hx_boost", None)

            items.append(el("a", label, **attrs))

        current_label = "Group by"
        for value, label in options:
            if value == self.current:
                current_label = f"Group by: {label}"
                break

        trigger_el = el(
            "span",
            current_label,
            class_="inline-flex items-center justify-center px-2 py-1 rounded-md hover:bg-muted dark:hover:bg-card transition-colors text-sm h-8",
            role="button",
            tabindex="0",
            aria_label=current_label,
            **{"aria-haspopup": "menu"},
        )

        return el(
            "div",
            el(
                "details",
                el(
                    "summary",
                    trigger_el,
                    class_="list-none cursor-pointer",
                ),
                el(
                    "div",
                    *items,
                    class_="absolute left-0 mt-2 w-48 bg-card rounded-md shadow-lg ring-1 ring-border z-[100] py-1 focus:outline-none origin-top-left",
                ),
                class_="relative inline-block",
            ),
            el("span", "", class_="hidden group-by-switcher-marker"),
            class_="group-by-switcher inline-block text-sm",
        )
