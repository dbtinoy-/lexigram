from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.ui import Component, HTMXAttrs, Zones, el

if TYPE_CHECKING:
    from lexigram.ui.state import TableState


class LayoutSwitcher(Component):
    """Simple layout switcher (stack | sidebar) for DataTable.

    Renders compact options and uses HTMX to request the table fragment
    with the chosen layout_type query param.
    """

    def __init__(
        self,
        current: str = "stack",
        resource_prefix: str | None = None,
        state: TableState | None = None,
        **props: Any,
    ) -> None:
        super().__init__(**props)
        self.current = current or "stack"
        self.resource_prefix = resource_prefix or ""
        self.state = state

    def render(self) -> Any:
        from lexigram.ui import ActionButton

        # Helper to generate button props
        def get_props(type_name: str, icon_name: str, label_text: str) -> Any:
            is_active = self.current == type_name

            # Base props
            props = {
                "label": "",
                "icon": icon_name,
                "variant": "ghost",
                "size": "sm",
                "title": label_text,
                "aria_label": label_text,
                "aria-pressed": "true" if is_active else "false",
            }

            # Active state: visual indicator + disable interaction
            if is_active:
                # Add background color manually via class since 'variant' might not cover this specific "active toggle" look
                # We want it to look "pressed" or "selected"
                props["class_"] = (
                    "bg-muted text-primary-600 dark:text-primary-400 cursor-default pointer-events-none"
                )
                # Remove HTMX attributes to disable behavior
            else:
                # Generate HTMX attrs using the new factory pattern
                if self.state:
                    updated_state = self.state.with_layout(type_name)  # type: ignore[arg-type]
                    htmx_attrs = HTMXAttrs.for_full_refresh(
                        updated_state,
                        self.resource_prefix,
                        push_url=True,
                    )
                    # Convert hx-* to hx_* for element builder
                    for k, v in htmx_attrs.items():
                        props[k.replace("-", "_")] = v
                else:
                    # Fallback if no state provided
                    props.update(
                        {
                            "hx_get": f"{self.resource_prefix.rstrip('/')}/?layout_type={type_name}",
                            "hx_target": Zones.TABLE.selector,
                            "hx_swap": "outerHTML",
                            "hx_params": "none",
                            "hx_push_url": "true",
                        },
                    )

                props.update(
                    {
                        "hx_on": f"click:console.log('layout:{type_name}')",
                        "class_": "text-muted-foreground hover:text-foreground hover:bg-muted dark:text-muted-foreground dark:hover:text-foreground dark:hover:bg-card",
                    },
                )

            return props

        stack_props = get_props("stack", "panel-top", "Stack view")
        sidebar_props = get_props("sidebar", "panel-left", "Sidebar view")

        stack_btn = ActionButton(**stack_props)
        sidebar_btn = ActionButton(**sidebar_props)

        return el(
            "div",
            el(
                "div",
                stack_btn.render(),
                sidebar_btn.render(),
                class_="inline-flex items-center gap-1 bg-card rounded-md p-1 border border-border",
            ),
            # Hidden on small screens, visible on md+ (desktop only)
            class_="layout-switcher hidden md:inline-flex items-center gap-2 text-sm",
        )
