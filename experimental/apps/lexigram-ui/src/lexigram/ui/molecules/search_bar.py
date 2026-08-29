"""SearchBar molecule component - combines search input with icon and clear button."""

from __future__ import annotations

from typing import Any

from lexigram.ui import Component, TextInput, Zones, el, get_icon


class SearchBar(Component):
    """Reusable search bar with icon and optional clear button."""

    def __init__(
        self,
        name: str = "search",
        value: str = "",
        placeholder: str = "Search...",
        show_icon: bool = True,
        show_clear: bool = False,
        aria_label: str = "Search",
        **props: Any,
    ) -> None:
        """
        Initialize search bar.

        Args:
            name: Input name attribute
            value: Current search value
            placeholder: Placeholder text
            show_icon: Whether to show search icon
            show_clear: Whether to show clear button
            aria_label: Accessible name for the search input (placeholders
                are not reliable labels for assistive technology).
            **props: Additional props (HTMX attributes, etc.)
        """
        super().__init__(
            name=name,
            value=value,
            placeholder=placeholder,
            show_icon=show_icon,
            show_clear=show_clear,
            aria_label=aria_label,
            **props,
        )
        self.name = name
        self.value = value
        self.placeholder = placeholder
        self.show_icon = show_icon
        self.show_clear = show_clear
        self.aria_label = aria_label

    def render(self) -> Any:
        """Render search bar."""
        # Filter props to avoid duplicates with explicit args
        # TextInput args: name, value, placeholder, type, error, disabled, required
        excluded_props = [
            "name",
            "value",
            "placeholder",
            "type",
            "error",
            "disabled",
            "required",
            "aria_label",
        ]
        text_input_props = {
            k: v for k, v in self.props.items() if k not in excluded_props
        }

        # AlpineJS State wrapping
        from lexigram.serialization import dumps_str

        wrapper_props = {
            "x_data": f"{{ query: {dumps_str(self.value)} }}",
            "class_": "relative group",
            "role": "search",
        }

        # Inject x-model into input props
        text_input_props["x_model"] = "query"
        # Ensure we trigger updates on input
        text_input_props["@keydown.escape"] = (
            "query = ''; $nextTick(() => $el.dispatchEvent(new Event('input', {bubbles: true})))"
        )

        search_input = TextInput(
            name=self.name,
            value=self.value,
            placeholder=self.placeholder,
            autocomplete="off",
            id=f"{Zones.SEARCH.id}-input",
            hx_preserve="true",
            aria_label=self.aria_label,
            **text_input_props,
        )

        # Build Inner Content
        inner_content = []

        # Icon
        if self.show_icon:
            inner_content.append(
                el(
                    "div",
                    get_icon("search", size="h-5 w-5"),
                    class_="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-muted-foreground",
                ),
            )

        # Input (wrapped for padding if icon exists)
        input_html = search_input.render()
        if self.show_icon:
            input_html = el(
                "div",
                input_html,
                class_="[&>input]:pl-10 [&>input]:pr-10"
                if self.show_clear
                else "[&>input]:pl-10",
            )
        elif self.show_clear:
            input_html = el("div", input_html, class_="[&>input]:pr-10")

        inner_content.append(input_html)

        # Clear Button
        if self.show_clear:
            clear_btn = el(
                "button",
                get_icon("x", size="h-4 w-4", aria_hidden="true"),
                type="button",
                aria_label="Clear search",
                class_="absolute inset-y-0 right-0 pr-3 flex items-center text-muted-foreground hover:text-muted-foreground cursor-pointer",
                x_show="query.length > 0",
                # On click: clear query, and dispatch 'input' event on the INPUT element (sibling)
                # We need to find the input. Since we are inside a relative wrapper,
                # generic approach: $el.closest('div.relative').querySelector('input').dispatchEvent(...)
                # Simpler: rely on x-model updating the value, then manually trigger the HTMX on the input.
                # However, HTMX triggers on the input element.
                # Use x_on:click
                **{
                    "@click": "query = ''; $nextTick(() => { let input = $el.closest('.relative').querySelector('input'); input.dispatchEvent(new Event('input', {bubbles: true})); input.dispatchEvent(new Event('change', {bubbles: true})); })",
                },
            )
            inner_content.append(clear_btn)

        return el("div", *inner_content, **wrapper_props)
