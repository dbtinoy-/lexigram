"""Stacked/sidebar filter drawer — slide-over panel with all filters.

Provides a ``FilterDrawer`` component that:
- Opens as a slide-over panel from the right on click of a "Filters" button
- Stacks all filter controls vertically for readability
- Shows an active-filter count badge on the trigger button
- Submits via HTMX on "Apply" and resets on "Clear"
"""

from __future__ import annotations

from typing import Any

from lexigram.ui import Component, Zones, el


class FilterDrawer(Component):
    """Slide-over filter panel with stacked filter controls.

    Renders a "Filters" trigger button whose badge shows the number of active
    filters, and a slide-over panel that contains the full filter form.  The
    panel is driven by Alpine.js (``filterDrawerOpen`` state) so it requires
    no page reload to open/close.

    Args:
        filters: Same format as ``FilterBar.filters`` — dict of
            ``{field_name: {"type": ..., "options": [...], ...}}``.
        current_values: Current active filter values.
        resource_prefix: Resource URL prefix for HTMX ``hx-get`` attributes.
        state: Optional ``TableState`` for building HTMX attrs on apply.
    """

    def __init__(
        self,
        filters: list[Any] | dict[str, Any] | None = None,
        current_values: dict[str, Any] | None = None,
        resource_prefix: str | None = None,
        state: Any | None = None,
        **props: Any,
    ) -> None:
        super().__init__(**props)
        self.filters = filters or []
        self.current_values = current_values or {}
        self.resource_prefix = resource_prefix
        self.state = state

    # ------------------------------------------------------------------
    # Public render
    # ------------------------------------------------------------------

    def render(self) -> Any:
        active_count = self._active_filter_count()
        trigger = self._render_trigger(active_count)
        panel = self._render_panel()
        backdrop = self._render_backdrop()

        # NOTE: Requires the Alpine.js Persist plugin (@alpinejs/persist).
        # Include it before Alpine core:
        #   <script src="https://cdn.jsdelivr.net/npm/@alpinejs/persist@3.x.x/dist/cdn.min.js"></script>
        # The $persist() call keeps filterDrawerOpen in localStorage so the
        # drawer state survives page navigations (e.g. HTMX soft navigations).
        return el(
            "div",
            trigger,
            backdrop,
            panel,
            **{
                "x-data": "{ filterDrawerOpen: $persist(false).as('lexigram_filter_drawer_open') }",
                "class": "relative",
            },
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _active_filter_count(self) -> int:
        """Return the number of filters that have a non-empty value."""
        return sum(
            1 for v in self.current_values.values() if v not in (None, "", [], {})
        )

    def _render_trigger(self, active_count: int) -> Any:
        """Render the "Filters" button with optional count badge."""
        badge = ""
        if active_count > 0:
            badge = el(
                "span",
                str(active_count),
                class_=(
                    "inline-flex items-center justify-center w-5 h-5 ml-1 "
                    "text-xs font-bold text-primary-foreground bg-primary rounded-full"
                ),
            )

        return el(
            "button",
            el(
                "svg",
                el(
                    "path",
                    **{
                        "stroke-linecap": "round",
                        "stroke-linejoin": "round",
                        "stroke-width": "2",
                        "d": "M3 4a1 1 0 011-1h16a1 1 0 011 1v2a1 1 0 01-.293.707L13 13.414V19a1 1 0 01-.553.894l-4 2A1 1 0 017 21v-7.586L3.293 6.707A1 1 0 013 6V4z",
                    },
                ),
                xmlns="http://www.w3.org/2000/svg",
                fill="none",
                viewBox="0 0 24 24",
                stroke="currentColor",
                class_="w-4 h-4 mr-1.5",
            ),
            "Filters",
            badge,
            type="button",
            class_=(
                "inline-flex items-center px-3 py-2 text-sm font-medium rounded-lg "
                "border border-border "
                "bg-card "
                "text-foreground "
                "hover:bg-muted dark:hover:bg-muted "
                "focus:outline-none focus:ring-2 focus:ring-ring "
                "transition-colors"
            ),
            **{"@click": "filterDrawerOpen = true"},
        )

    def _render_backdrop(self) -> Any:
        """Semi-transparent backdrop to close drawer on outside click."""
        return el(
            "div",
            class_="fixed inset-0 bg-black/30 z-40",
            **{
                "x-show": "filterDrawerOpen",
                "x-transition:enter": "transition ease-out duration-200",
                "x-transition:enter-start": "opacity-0",
                "x-transition:enter-end": "opacity-100",
                "x-transition:leave": "transition ease-in duration-150",
                "x-transition:leave-start": "opacity-100",
                "x-transition:leave-end": "opacity-0",
                "x-cloak": "",
                "@click": "filterDrawerOpen = false",
            },
        )

    def _render_panel(self) -> Any:
        """Render the slide-over panel body with filter controls."""
        filter_controls = self._build_filter_controls()
        apply_url = self.resource_prefix.rstrip("/") if self.resource_prefix else "#"

        res_prefix = (self.resource_prefix or "").strip("/").replace("/", "_")
        if not res_prefix:
            res_prefix = "global"

        apply_attrs: dict[str, Any] = {
            "hx-get": apply_url,
            "hx-target": Zones.DATA.selector,
            "hx-swap": Zones.DATA.swap_mode.value,
            "hx-select": Zones.DATA.selector,
            "hx-select-oob": Zones.data_refresh_oob_select(),
            "hx-push-url": "true",
            "hx-include": f"{Zones.DATA.selector} [data-state='true'], [data-filter-field]",
            # Close the drawer and persist current filter values to localStorage
            # so they can be restored on next page load (read by x-init on each
            # filter input via x-model and $persist).
            "@click": (
                "filterDrawerOpen = false; "
                "document.querySelectorAll('[data-filter-field]').forEach(function(el) { "
                f"  var key = 'lexigram_filter_{res_prefix}_' + (el.name || el.id || ''); "
                f"  if (key !== 'lexigram_filter_{res_prefix}_') {{ localStorage.setItem(key, el.value); }} "
                "});"
            ),
        }

        reset_href = apply_url
        if self.resource_prefix:
            reset_href = apply_url  # clear all → GET without filter params

        return el(
            "div",
            # Header
            el(
                "div",
                el(
                    "h2",
                    "Filters",
                    class_=("text-lg font-semibold text-foreground"),
                ),
                el(
                    "button",
                    el(
                        "svg",
                        el(
                            "path",
                            **{
                                "stroke-linecap": "round",
                                "stroke-linejoin": "round",
                                "stroke-width": "2",
                                "d": "M6 18L18 6M6 6l12 12",
                            },
                        ),
                        xmlns="http://www.w3.org/2000/svg",
                        fill="none",
                        viewBox="0 0 24 24",
                        stroke="currentColor",
                        class_="w-5 h-5",
                    ),
                    type="button",
                    class_=(
                        "p-1 text-muted-foreground hover:text-muted-foreground "
                        "dark:hover:text-foreground rounded transition-colors"
                    ),
                    **{"@click": "filterDrawerOpen = false"},
                ),
                class_="flex items-center justify-between p-4 border-b border-border",
            ),
            # Filter controls
            el(
                "div",
                *filter_controls,
                class_="flex-1 overflow-y-auto p-4 space-y-4",
            ),
            # Footer actions
            el(
                "div",
                el(
                    "a",
                    "Reset all",
                    href=reset_href,
                    class_=(
                        "px-4 py-2 text-sm font-medium text-foreground "
                        "border border-border rounded-lg "
                        "hover:bg-muted dark:hover:bg-muted transition-colors"
                    ),
                    **{
                        "hx-get": reset_href,
                        "hx-target": Zones.DATA.selector,
                        "hx-swap": Zones.DATA.swap_mode.value,
                        "hx-select": Zones.DATA.selector,
                        "hx-select-oob": Zones.data_refresh_oob_select(),
                        "hx-push-url": "true",
                        "@click": "filterDrawerOpen = false",
                    },
                ),
                el(
                    "button",
                    "Apply filters",
                    type="button",
                    class_=(
                        "px-4 py-2 text-sm font-medium text-white "
                        "bg-primary hover:bg-primary/90 rounded-lg "
                        "focus:outline-none focus:ring-2 focus:ring-ring "
                        "transition-colors"
                    ),
                    **apply_attrs,
                ),
                class_=(
                    "flex items-center justify-end gap-3 p-4 border-t border-border"
                ),
            ),
            # Panel wrapper
            class_=(
                "fixed top-0 right-0 bottom-0 z-50 flex flex-col "
                "w-80 max-w-full "
                "bg-card shadow-xl"
            ),
            **{
                "x-show": "filterDrawerOpen",
                "x-transition:enter": "transition ease-out duration-250",
                "x-transition:enter-start": "translate-x-full",
                "x-transition:enter-end": "translate-x-0",
                "x-transition:leave": "transition ease-in duration-200",
                "x-transition:leave-start": "translate-x-0",
                "x-transition:leave-end": "translate-x-full",
                "x-cloak": "",
                "@click.stop": "",
            },
        )

    def _build_filter_controls(self) -> list[Any]:
        """Build stacked filter controls for the panel."""
        controls: list[Any] = []

        if isinstance(self.filters, list):
            for f in self.filters:
                if not hasattr(f, "render"):
                    continue
                label = getattr(f, "label", getattr(f, "field_name", ""))
                current_val = self.current_values.get(
                    getattr(f, "field_name", ""), None
                )
                if hasattr(f, "set_state"):
                    f.set_state(self.state)
                rendered = f.render(
                    current_val,
                    url=self.resource_prefix.rstrip("/")
                    if self.resource_prefix
                    else None,
                )
                controls.append(
                    el(
                        "div",
                        el(
                            "label",
                            str(label),
                            class_="block text-sm font-medium text-foreground mb-1",
                        ),
                        el("div", rendered, **{"data-filter-field": ""}),
                        class_="",
                    )
                )
        elif isinstance(self.filters, dict):
            for field_name, opts in self.filters.items():
                current_val = self.current_values.get(field_name, "")
                label = (
                    opts.get("label", field_name.replace("_", " ").title())
                    if isinstance(opts, dict)
                    else field_name.replace("_", " ").title()
                )
                input_el = el(
                    "input",
                    type="text",
                    name=f"filter_{field_name}",
                    value=str(current_val) if current_val else "",
                    placeholder=f"Filter by {label.lower()}…",
                    class_=(
                        "block w-full rounded-md border border-border "
                        "bg-muted text-foreground "
                        "px-3 py-2 text-sm shadow-sm focus:outline-none "
                        "focus:ring-2 focus:ring-ring"
                    ),
                    **{"data-filter-field": ""},
                )
                controls.append(
                    el(
                        "div",
                        el(
                            "label",
                            label,
                            class_="block text-sm font-medium text-foreground mb-1",
                        ),
                        input_el,
                    )
                )

        return controls
