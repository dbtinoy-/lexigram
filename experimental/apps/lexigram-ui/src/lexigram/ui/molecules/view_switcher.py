from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.ui import Component, HTMXAttrs, Zones, el

if TYPE_CHECKING:
    from lexigram.ui.state import TableState


class ViewSwitcher(Component):
    """Simple view switcher dropdown for DataTable.

    Renders a compact dropdown listing available views and emits HTMX
    requests to the resource with `data_view` query param.
    """

    def __init__(
        self,
        current: str = "tabular",
        resource_prefix: str | None = None,
        options: list | None = None,
        state: TableState | None = None,
        **props: Any,
    ) -> None:
        super().__init__(**props)
        self.current = current or "tabular"
        self.resource_prefix = resource_prefix or ""
        self.options = options or [
            ("tabular", "Tabular"),
            ("grid", "Grid"),
            ("calendar", "Calendar"),
            ("stacked", "Stacked"),
        ]
        # Optional TableState instance for generating HTMX attrs
        self.state = state

    def render(self) -> Any:
        from lexigram.ui import get_icon

        # Icon mapping
        icon_map = {
            "tabular": "table",
            "grid": "grid",
            "calendar": "calendar",
            "stacked": "list",
        }

        # Button with dropdown list; for simplicity, use inline links with HTMX attributes
        items = []
        for value, label in self.options:
            attrs = {
                # Use HTMXAttrs for consistent attribute generation
                "class": "block px-3 py-2 text-sm text-foreground hover:bg-muted dark:text-foreground dark:hover:bg-muted flex items-center gap-2",
                "hx_on": f"click:console.log('view:{value}')",
                # Simple serialized JS to update the trigger icon on click
                "onclick": "let svg = this.querySelector('svg').cloneNode(true); svg.setAttribute('class', 'h-4 w-4 text-muted-foreground dark:text-foreground'); this.closest('details').querySelector('summary span').innerHTML = ''; this.closest('details').querySelector('summary span').appendChild(svg); this.closest('details').open = false;",
            }

            # Generate HTMX attrs using the new factory
            if self.state:
                updated_state = self.state.with_view(value)
                htmx_attrs = HTMXAttrs.for_full_refresh(
                    updated_state,
                    self.resource_prefix,
                    push_url=True,
                )
                # Convert hx-* to hx_* for element builder
                for k, v in htmx_attrs.items():
                    attrs[k.replace("-", "_")] = v
            else:
                # Fallback if no state provided
                attrs.update(
                    {
                        "hx_get": f"{self.resource_prefix.rstrip('/')}/?data_view={value}",
                        "hx_target": Zones.TABLE.selector,
                        "hx_swap": "outerHTML",
                        "hx_params": "none",
                        "hx_push_url": "false",
                    },
                )

            icon_name = icon_map.get(value, "table")
            icon_el = get_icon(
                icon_name,
                size="h-4 w-4 text-muted-foreground group-hover:text-muted-foreground",
            )

            if value == self.current:
                # Mark selected: Visual indicator + disable interaction
                attrs["aria-current"] = "true"
                attrs["class"] = (
                    "block px-3 py-2 text-sm font-medium bg-muted text-foreground cursor-default pointer-events-none flex items-center gap-2"
                )

                # Active icon style
                icon_el = get_icon(icon_name, size="h-4 w-4 text-primary-500")

                # Remove navigation props
                attrs.pop("href", None)
                attrs.pop("hx_get", None)
                attrs.pop("hx_target", None)
                attrs.pop("hx_swap", None)
                attrs.pop("hx_include", None)
                attrs.pop("hx_push_url", None)
                attrs.pop("hx_boost", None)
                attrs.pop("hx_on", None)
                attrs.pop("onclick", None)  # No need to update on click if disabled

                label = f"{label}"

            items.append(el("a", icon_el, label, **attrs))

        # Use native <details>/<summary> for toggle behavior (works without JS)

        # Build a non-interactive trigger inside the summary so clicks toggle <details> reliably
        # Show active icon in trigger
        current_icon_name = icon_map.get(self.current, "table")
        trigger_icon = get_icon(
            current_icon_name,
            size="h-4 w-4 text-muted-foreground dark:text-foreground",
        )

        trigger_el = el(
            "span",
            trigger_icon,
            class_="inline-flex items-center justify-center p-1 rounded-md hover:bg-muted dark:hover:bg-card transition-colors h-8 w-8",
            role="button",
            tabindex="0",
            aria_label=f"Current view: {self.current.title()}",
            **{
                "aria-haspopup": "menu",
            },
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
                    # Changed from right-0 to left-0 because this component is usually on the left side of the toolbar
                    # This prevents it from expanding leftwards into the sidebar.
                    # Increased z-index to 100 to avoid being hidden by sidebar
                    class_="absolute left-0 mt-2 w-40 bg-card rounded-md shadow-lg ring-1 ring-border z-[100] py-1 focus:outline-none origin-top-left",
                ),
                class_="relative inline-block",
            ),
            # Hidden marker for server-side presence detection
            el("span", "", class_="hidden view-switcher-marker"),
            class_="view-switcher inline-block text-sm",
        )
