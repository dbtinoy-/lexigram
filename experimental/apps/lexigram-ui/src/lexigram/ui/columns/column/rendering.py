"""
Column rendering methods for HTML generation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.ui import HTMXAttrs, Zones, el

if TYPE_CHECKING:
    from lexigram.ui.state import TableState


class ColumnRenderingMixin:
    """Mixin class containing rendering methods."""

    # Attributes expected to be provided by Column base class
    name: str
    label: str
    _masker: Any
    _limit: int | None
    _alignment: str
    _visibility_classes: list[str]
    _wrap: bool
    _copyable: bool
    _sortable: bool

    def is_visible(self, **kwargs: Any) -> bool:
        """Check if column is visible — implemented by ColumnVisibilityMixin."""
        return True

    def get_value(self, record: dict) -> Any:
        """Extract value from record — implemented by Column."""

    def format_value(self, value: Any) -> Any:
        """Format value — implemented by Column."""
        return value

    def render(self, value: Any, record: dict) -> Any:
        """Render cell value — implemented by Column."""

    def render_cell(
        self,
        record: dict,
        user: Any = None,
        resource_name: str | None = None,
    ) -> Any:
        """
        Render complete table cell with wrapper.

        Args:
            record: The full record dict
            user: Current user for permission checks
            resource_name: Current resource name for permission checks

        Returns:
            htpy element for <td>
        """
        if not self.is_visible(user=user, resource_name=resource_name, record=record):
            return ""

        value = self.get_value(record)
        formatted_value = self.format_value(value)

        # Apply masking if defined
        if self._masker and formatted_value is not None:
            formatted_value = self._masker(formatted_value)

        # Apply limit if set
        if (
            self._limit
            and isinstance(formatted_value, str)
            and len(formatted_value) > self._limit
        ):
            formatted_value = formatted_value[: self._limit] + "..."

        # Render the value
        content = self.render(formatted_value, record)

        # Build CSS classes
        classes = [f"text-{self._alignment}", "px-6", "py-4"]
        classes.extend(self._visibility_classes)
        if self._wrap:
            classes.append("whitespace-normal")
        else:
            classes.append("whitespace-nowrap")

        # Add copyable functionality
        if self._copyable:
            classes.append("cursor-pointer hover:bg-muted dark:hover:bg-card")
            escaped_value = str(value).replace("'", "\\'")
            hx_on_click = f"navigator.clipboard.writeText('{escaped_value}')"
            return el(
                "td",
                content,
                class_="".join(classes),
                hx_on_click=hx_on_click,
                title="Click to copy",
                aria_label=f"Copy {value}",
            )

        return el("td", content, class_="".join(classes), **{"data-label": self.label})

    def render_header(
        self,
        current_sort: str | None = None,
        sort_order: str = "asc",
        state: TableState | None = None,
        resource_prefix: str = "",
    ) -> Any:
        """
        Render table header cell.

        Args:
            current_sort: Currently sorted column name
            sort_order: Current sort order ("asc" or "desc")
            state: Optional TableState for generating HTMX URLs
            resource_prefix: Base URL for the resource (e.g., "/admin/users")

        Returns:
            htpy element for <th>
        """
        from lexigram.ui import get_icon

        classes = [
            f"text-{self._alignment}",
            "px-6",
            "py-3",
            "text-xs",
            "font-semibold",
            "text-foreground",
            "dark:text-foreground",
            "uppercase",
            "tracking-wider",
        ]
        classes.extend(self._visibility_classes)

        # Base props for the th element
        th_props: dict[str, Any] = {
            "scope": "col",
        }

        # Build header content
        is_current = current_sort == self.name

        if self._sortable:
            classes.append("cursor-pointer")
            classes.append("hover:bg-muted")
            classes.append("dark:hover:bg-muted")
            classes.append("select-none")  # Prevent text selection on click
            classes.append("transition-colors")

            # Determine next sort order
            next_order = "desc" if (is_current and sort_order == "asc") else "asc"

            # Build HTMX attrs directly on the th element (entire header clickable)
            if state and resource_prefix:
                # Use immutable mutation to get new state with sort
                new_state = state.with_sort(self.name)
                htmx_attrs = HTMXAttrs.for_data_refresh(
                    new_state,
                    resource_prefix,
                    push_url=True,
                )
                # Convert hx-* to hx_* for element builder
                for k, v in htmx_attrs.items():
                    th_props[k.replace("-", "_")] = v
            else:
                # Fallback: manual construction
                sort_params = f"sort_by={self.name}&sort_order={next_order}"
                th_props.update(
                    {
                        "hx_get": f"?{sort_params}",
                        "hx_target": Zones.DATA.selector,
                        "hx_swap": Zones.DATA.swap_mode.value,
                        "hx_select": Zones.DATA.selector,
                        "hx_params": "none",
                        "hx_push_url": "true",
                    },
                )

            # Build sort icon
            if is_current:
                icon_name = "chevron-up" if sort_order == "asc" else "chevron-down"
                icon_classes = "h-4 w-4 text-primary-600 dark:text-primary-400"
            else:
                # Subtle indicator for sortable but not currently sorted
                icon_name = "chevrons-up-down"
                icon_classes = "h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity"

            sort_icon = get_icon(icon_name, size=icon_classes)

            # Content with label + icon
            content = el(
                "span",
                self.label,
                sort_icon,
                class_="inline-flex items-center gap-1.5",
            )
        else:
            # Non-sortable column - just the label
            content = el("span", self.label)

        resize_handle = el(
            "div",
            role="separator",
            tabindex="0",
            aria_orientation="vertical",
            aria_label=f"Resize {self.label} column",
            class_="absolute right-0 top-0 bottom-0 w-2 cursor-col-resize hover:bg-primary-300 dark:hover:bg-primary-700 transition-colors opacity-0 hover:opacity-100 group-hover:opacity-100",
            **{
                "@mousedown.stop.prevent": "startResize",
                "@keydown.left.prevent": "if ($el.parentElement) { let th = $el.parentElement; let w = Math.max(50, th.offsetWidth - 10); th.style.width = w + 'px'; th.style.minWidth = w + 'px' }",
                "@keydown.right.prevent": "if ($el.parentElement) { let th = $el.parentElement; let w = th.offsetWidth + 10; th.style.width = w + 'px'; th.style.minWidth = w + 'px' }",
            },
        )

        # Content wrapper
        wrapper = el(
            "div",
            content,
            resize_handle,
            class_="flex items-center justify-between w-full h-full",
        )

        # Add relative for resize handle positioning, group for hover states
        # Sticky positioning for fixed headers
        classes.append("relative group sticky top-0 z-20 bg-muted dark:bg-background")
        th_props["class_"] = " ".join(classes)
        th_props["x-data"] = "resizableColumn"

        return el("th", wrapper, **th_props)
