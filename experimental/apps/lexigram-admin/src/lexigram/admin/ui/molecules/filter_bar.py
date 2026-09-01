"""Filter bar component using existing UI components."""

from __future__ import annotations

from typing import Any

from lexigram.ui import Component, Zones, el


class FilterBar(Component):
    """Filter bar with various input types using existing UI components."""

    def __init__(
        self,
        filters: dict[str, dict[str, Any]] | None = None,
        current_values: dict[str, Any] | None = None,
        resource_prefix: str | None = None,
        display: str = "auto",
        state: Any | None = None,
        **props: Any,
    ) -> None:
        """Initialize filter bar.

        Add `display` param: 'auto'|'vertical'|'horizontal'.

        Args:
            filters: Dict of {field_name: {"type": "select|text|checkbox|date", "options": [...], ...}}
                     or a list of Filter objects
            current_values: Dict of {field_name: current_value}
            resource_prefix: Resource URL prefix for HTMX requests
            state: Optional `TableState` instance to allow filters to include table HTMX attrs
        """
        super().__init__(**props)
        self.filters = filters or {}
        self.current_values = current_values or {}
        self.resource_prefix = resource_prefix
        # Display mode: auto, vertical, horizontal
        self.display = props.get("display", display)
        # Store optional TableState for child filters to use
        self.state = state

    def _detect_filter_type(self, field_name: str, options: Any) -> str:
        """Auto-detect filter type based on field name and options."""
        # Check field name patterns
        if "date" in field_name.lower() or "time" in field_name.lower():
            return "date"
        if "is_" in field_name.lower() or field_name.lower() in [
            "active",
            "enabled",
            "published",
        ]:
            return "checkbox"

        # Check options
        if isinstance(options, list):
            if len(options) == 2 and {str(o).lower() for o in options} <= {
                "true",
                "false",
                "yes",
                "no",
                "1",
                "0",
            }:
                return "checkbox"
            if len(options) <= 10:
                return "select"

        return "text"

    def render(self) -> Any:
        if not self.filters:
            return ""

        filter_controls = []

        # If filters is a list, assume they are Filter objects
        if isinstance(self.filters, list):
            f: Any
            for f in self.filters:
                # Check visibility if context available
                if hasattr(f, "is_visible") and not f.is_visible():
                    continue

                # Get current value for this filter
                current_val = self.current_values.get(f.name, f.get_default())

                # Set state so filters can generate canonical baked hx-vals
                if self.state and hasattr(f, "set_state"):
                    self.state.set_resource_prefix(self.resource_prefix)
                    f.set_state(self.state)

                # Schema fields (from lexigram.admin.schema) use render_filter.
                # Their field-level renderer does not know the table URL, so
                # attach the same live-table HTMX contract used by UI Filter
                # objects here. Put the listener on the field wrapper: this
                # works for schema controls whose input is nested under a
                # labelled component (select, multi-select, etc.).
                if hasattr(f, "render_filter"):
                    rendered = f.render_filter(current_val)
                    if rendered is not None:
                        if self.resource_prefix and hasattr(rendered, "attrs"):
                            base_url = self.resource_prefix.rstrip("/") + "/"
                            rendered.attrs.update(
                                {
                                    "hx-get": base_url,
                                    "hx-trigger": "change",
                                    "hx-target": Zones.DATA.selector,
                                    "hx-swap": Zones.DATA.swap_mode.value,
                                    "hx-select": Zones.DATA.selector,
                                    "hx-select-oob": Zones.data_refresh_oob_select(),
                                    "hx-push-url": "true",
                                    "hx-include": (
                                        f"{Zones.DATA.selector} [data-state='true'], "
                                        f"#{Zones.SEARCH.id}, #{Zones.FILTERS.id}"
                                    ),
                                    "hx-params": "*",
                                }
                            )
                        filter_controls.append(rendered)
                # Form fields use bind/render pattern
                elif hasattr(f, "bind"):
                    bound_f = f.bind(current_val)
                    if self.state and hasattr(bound_f, "set_state"):
                        bound_f.set_state(self.state)
                    filter_controls.append(bound_f.render())
                # Filter objects (from ui/filters/) use render() with value
                elif hasattr(f, "render"):
                    if self.state and hasattr(f, "set_state"):
                        f.set_state(self.state)
                    filter_controls.append(
                        f.render(
                            current_val,
                            url=self.resource_prefix.rstrip("/")
                            if self.resource_prefix
                            else None,
                        ),
                    )
                else:
                    filter_controls.append(
                        el("div", f"Filter {f.name} missing render method"),
                    )

            return self._wrap_container(filter_controls)

        # Dict of {field_name: {"type": ..., "options": [...], ...}} format
        from lexigram.admin.ui.filters.types import SelectFilter, ToggleFilter
        from lexigram.ui import TextInput

        # Set resource prefix on state once so all filters can build proper URLs
        if self.state and self.resource_prefix:
            self.state.set_resource_prefix(self.resource_prefix)

        for field_name, filter_config in self.filters.items():
            current_val = self.current_values.get(field_name, "")

            # Create a temporary filter object for rendering
            if isinstance(filter_config, dict):
                f_type = filter_config.get("type", "select")
                options = filter_config.get("options", [])
                if f_type == "checkbox":
                    f = ToggleFilter(
                        name=field_name,
                        label=filter_config.get("label"),
                    )
                elif f_type in {"text", "date", "number"}:
                    # The dict API promises simple text/date controls as well
                    # as selects. Use the shared input atom and preserve the
                    # canonical filter_ transport name.
                    filter_controls.append(
                        TextInput(
                            name=f"filter_{field_name}",
                            value=str(current_val or ""),
                            label=filter_config.get("label")
                            or field_name.replace("_", " ").title(),
                            placeholder=filter_config.get("placeholder"),
                            input_type=f_type,
                            hx_get=(
                                self.resource_prefix.rstrip("/") + "/"
                                if self.resource_prefix
                                else "/"
                            ),
                            hx_trigger="change",
                            hx_target=Zones.DATA.selector,
                            hx_swap=Zones.DATA.swap_mode.value,
                            hx_select=Zones.DATA.selector,
                            hx_push_url="true",
                            hx_include=(
                                f"{Zones.DATA.selector} [data-state='true'], "
                                f"#{Zones.SEARCH.id}, #{Zones.FILTERS.id}"
                            ),
                            hx_params="*",
                        ).render()
                    )
                    continue
                else:  # Default to select
                    f = SelectFilter(
                        name=field_name,
                        options=options,
                        label=filter_config.get("label"),
                    )
            else:
                continue

            # Attach state so filters can include canonical table inputs
            f.set_state(getattr(self, "state", None))

            filter_controls.append(
                f.render(
                    current_val,
                    url=self.resource_prefix.rstrip("/")
                    if self.resource_prefix
                    else None,
                ),
            )

        return self._wrap_container(filter_controls)

    def _active_filter_count(self) -> int:
        """Count filter values that are non-empty (active)."""
        return sum(1 for v in self.current_values.values() if v not in (None, "", []))

    def _wrap_container(self, filter_controls: list[Any]) -> str:
        """Helper to wrap controls in container."""
        if not filter_controls:
            return ""

        active_count = self._active_filter_count()

        # Determine container class based on display preference
        if self.display == "vertical":
            container_cls = "flex flex-col gap-2 w-full"
        else:
            # horizontal is default: responsive stack on mobile, wrap on desktop
            container_cls = "flex flex-col md:flex-row md:flex-wrap gap-2 items-stretch md:items-end"

        # Wrap each control so it is full-width on mobile and auto width on md+ (horizontal) screens
        wrapped_controls = [
            el("div", ctrl, class_="w-full md:w-auto") for ctrl in filter_controls
        ]

        # Filter icon (funnel) with active count badge
        filter_icon = el(
            "svg",
            el(
                "path",
                **{
                    "d": "M4 6h16M4 12h12M4 18h8",
                    "stroke-linecap": "round",
                    "stroke-linejoin": "round",
                    "stroke-width": "2",
                },
            ),
            xmlns="http://www.w3.org/2000/svg",
            fill="none",
            viewBox="0 0 24 24",
            stroke="currentColor",
            class_="w-5 h-5",
        )

        badge: Any = ""
        if active_count > 0:
            badge = el(
                "span",
                str(active_count),
                class_="absolute -top-1.5 -right-1.5 bg-primary text-primary-foreground text-xs font-bold rounded-full min-w-[16px] h-4 flex items-center justify-center px-1 leading-none",
            )

        toggle_btn = el(
            "button",
            el(
                "div",
                filter_icon,
                badge,
                class_="relative inline-flex items-center justify-center",
            ),
            type="button",
            class_="p-2 hover:bg-muted rounded-lg transition-colors text-muted-foreground hover:text-muted-foreground dark:hover:text-foreground",
            aria_label="Toggle filters",
            **{"@click": "showFilters = !showFilters"},
        )

        return el(
            "div",
            el(
                "div",
                el(
                    "div",
                    *wrapped_controls,
                    class_=f"{container_cls} flex-1",
                    **{"x-show": "showFilters"},
                ),
                el(
                    "div",
                    toggle_btn,
                    class_="flex-shrink-0 flex items-center h-10 md:hidden",
                ),
                class_="flex items-start gap-2",
            ),
            x_data="{ showFilters: window.innerWidth >= 768 }",
            class_="bg-card p-3 rounded-xl shadow-sm border border-border mb-1",
            **self.props,
        )
