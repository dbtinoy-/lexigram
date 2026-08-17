from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from lexigram.serialization import dumps_str
from lexigram.ui.core.base import Component, el, raw, render_to_string

if TYPE_CHECKING:
    from collections.abc import Callable


class Repeater(Component):
    """
    A component that allows users to add/remove sets of fields.
    Useful for JSON arrays or HasMany relations.
    """

    def __init__(
        self,
        name: str,
        schema: list[Component] | Callable[[], list[Component]],
        value: list[dict] | None = None,
        label: str | None = None,
        add_label: str = "Add Item",
        item_label: str = "Item",
        **props: Any,
    ) -> None:
        super().__init__(
            name=name,
            schema=schema,
            value=value,
            label=label,
            add_label=add_label,
            item_label=item_label,
            **props,
        )
        self.name = name
        self.schema = schema
        self.value = value or []
        self.label = label
        self.add_label = add_label
        self.item_label = item_label

    def render(self) -> Any:
        # Determine schema components
        components = self.schema() if callable(self.schema) else self.schema

        # Create a template by rendering components and replacing name/id with Alpine-friendly versions
        raw_template = ""
        for comp in components:
            raw_template += render_to_string(comp)

        # Replace name="field" with :name="`{self.name}[${index}][field]`"
        # We look for name="([^"]+)" and id="([^"]+)"
        template_html = re.sub(
            r'name="([^"]+)"',
            rf':name="`{self.name}[${{index}}][\1]`"',
            raw_template,
        )
        template_html = re.sub(
            r'id="([^"]+)"',
            rf':id="`{self.name}_${{index}}_\1`"',
            template_html,
        )
        # Also need to handle for="..." labels
        template_html = re.sub(
            r'for="([^"]+)"',
            rf':for="`{self.name}_${{index}}_\1`"',
            template_html,
        )

        initial_data = dumps_str(self.value)

        x_data = (
            f"{{ "
            f"items: {initial_data}, "
            f"addItem() {{ this.items.push({{}}); }}, "
            f"removeItem(index) {{ this.items.splice(index, 1); }}, "
            f"moveUp(index) {{ if(index > 0) [this.items[index-1], this.items[index]] = [this.items[index], this.items[index-1]]; }}, "
            f"moveDown(index) {{ if(index < this.items.length - 1) [this.items[index+1], this.items[index]] = [this.items[index], this.items[index+1]]; }}"
            f" }}"
        )

        # Header with Label and Add Button
        header = el(
            "div",
            el(
                "h4",
                self.label or "",
                class_="text-sm font-semibold text-foreground",
            )
            if self.label
            else "",
            el(
                "button",
                el(
                    "svg",
                    el(
                        "path",
                        d="M12 4v16m8-8H4",
                        stroke_linecap="round",
                        stroke_linejoin="round",
                        stroke_width="2",
                    ),
                    class_="w-4 h-4 mr-1",
                    fill="none",
                    viewBox="0 0 24 24",
                    stroke="currentColor",
                ),
                self.add_label,
                type="button",
                **{"@click": "addItem()"},
                class_="inline-flex items-center px-3 py-1.5 text-xs font-semibold text-primary bg-primary/5 rounded-lg hover:bg-primary/15 transition-all duration-200",
            ),
            class_="flex items-center justify-between mb-4",
        )

        # Repeater Item Card
        item_card = el(
            "div",
            # Item Header (Drag handle placeholder, Label, Actions)
            el(
                "div",
                el(
                    "span",
                    **{"x-text": f"`{self.item_label} #${{index + 1}}`"},
                    class_="text-xs font-bold text-muted-foreground uppercase tracking-wider",
                ),
                el(
                    "div",
                    # Move Up
                    el(
                        "button",
                        el(
                            "svg",
                            el(
                                "path",
                                d="M5 15l7-7 7 7",
                                stroke_linecap="round",
                                stroke_linejoin="round",
                                stroke_width="2",
                            ),
                            class_="w-3 h-3",
                            fill="none",
                            viewBox="0 0 24 24",
                            stroke="currentColor",
                            aria_hidden="true",
                        ),
                        type="button",
                        title="Move Up",
                        aria_label="Move Up",
                        **{"@click": "moveUp(index)", "x-show": "index > 0"},
                        class_="p-1 text-muted-foreground hover:text-primary transition-colors",
                    ),
                    # Move Down
                    el(
                        "button",
                        el(
                            "svg",
                            el(
                                "path",
                                d="M19 9l-7 7-7-7",
                                stroke_linecap="round",
                                stroke_linejoin="round",
                                stroke_width="2",
                            ),
                            class_="w-3 h-3",
                            fill="none",
                            viewBox="0 0 24 24",
                            stroke="currentColor",
                            aria_hidden="true",
                        ),
                        type="button",
                        title="Move Down",
                        aria_label="Move Down",
                        **{
                            "@click": "moveDown(index)",
                            "x-show": "index < items.length - 1",
                        },
                        class_="p-1 text-muted-foreground hover:text-primary transition-colors",
                    ),
                    # Remove
                    el(
                        "button",
                        el(
                            "svg",
                            el(
                                "path",
                                d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16",
                                stroke_linecap="round",
                                stroke_linejoin="round",
                                stroke_width="2",
                            ),
                            class_="w-4 h-4",
                            fill="none",
                            viewBox="0 0 24 24",
                            stroke="currentColor",
                            aria_hidden="true",
                        ),
                        type="button",
                        title="Remove",
                        aria_label="Remove",
                        **{"@click": "removeItem(index)"},
                        class_="ml-2 p-1 text-muted-foreground hover:text-destructive transition-colors",
                    ),
                    class_="flex items-center gap-1",
                ),
                class_="flex items-center justify-between px-4 py-2 bg-muted border-b border-border",
            ),
            # Item Content
            el(
                "div",
                raw(template_html),
                class_="p-4 grid grid-cols-1 gap-4 sm:grid-cols-2",
            ),
            class_="bg-card border border-border rounded-xl overflow-hidden mb-4 shadow-sm",
            **{"x-for": "(item, index) in items", ":key": "index"},
        )

        repeater_id = f"repeater_{self.name}"

        container = el(
            "div",
            header,
            el("template", item_card),
            el(
                "div",
                "No items added.",
                class_="text-center py-8 border-2 border-dashed border-border rounded-xl text-sm text-muted-foreground",
                **{"x-show": "items.length === 0"},
            ),
            class_="repeater-container",
            **{"x-data": x_data, "id": repeater_id},
        )

        return el("div", container, class_="mb-8")
