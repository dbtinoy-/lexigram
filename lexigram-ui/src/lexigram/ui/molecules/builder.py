from __future__ import annotations

from typing import Any

from lexigram import serialization as json
from lexigram.logging import get_logger
from lexigram.serialization import dumps_str
from lexigram.ui.core.base import Component, NoContext, el

logger = get_logger(__name__)


class Builder(Component):
    """
    A block-based content editor.
    Allows adding, removing, and reordering structured content blocks.

    Data is stored as a JSON array of objects:
    [
        {"type": "heading", "data": {"text": "Hello"}},
        {"type": "text", "data": {"body": "World"}}
    ]
    """

    def __init__(
        self,
        blocks: list[Any],  # List of Block objects from fields.py
        name: str,
        value: list[dict] | str | None = None,
        label: str | None = None,
        **props,
    ) -> None:
        super().__init__(blocks=blocks, name=name, label=label, **props)
        self.blocks = blocks
        self.name = name
        self.label = label

        # Handle JSON strings or dicts
        if isinstance(value, str) and value:
            from lexigram.serialization import loads_str

            try:
                self.value = loads_str(value)
            except (ValueError, TypeError, json.JSONDecodeError):
                self.value = []
        else:
            self.value = value or []

    def render(self) -> Any:
        # Pre-render block definitions to pass them to Alpine
        block_defs = []
        for b in self.blocks:
            # We need to render the fields for each block template
            # This is tricky because we want to render them such that Alpine can use them as templates
            block_defs.append(
                {"type": b.name, "label": b.label, "icon": b.icon or "cube"},
            )

        # Alpine state:
        # items: [{id: 1, type: 'heading', data: {...}, collapsed: false}]
        # nextId: integer

        # Convert existing values to items with unique IDs for Alpine
        initial_items = []
        for i, item in enumerate(self.value):
            initial_items.append(
                {
                    "id": i + 1,
                    "type": item.get("type"),
                    "data": item.get("data", {}),
                    "collapsed": False,
                },
            )

        x_data = {
            "items": initial_items,
            "nextId": len(initial_items) + 1,
            "addBlock(type)": "this.items.push({id: this.nextId++, type: type, data: {}, collapsed: false})",
            "removeBlock(id)": "this.items = this.items.filter(i => i.id !== id)",
            "moveBlock(id, direction)": """
                let idx = this.items.findIndex(i => i.id === id);
                if (direction === 'up' && idx > 0) {
                    [this.items[idx-1], this.items[idx]] = [this.items[idx], this.items[idx-1]];
                } else if (direction === 'down' && idx < this.items.length - 1) {
                    [this.items[idx+1], this.items[idx]] = [this.items[idx], this.items[idx+1]];
                }
            """,
        }

        # Main container
        return el(
            "div",
            # Hidden input for the final JSON data
            el(
                "input",
                type="hidden",
                name=self.name,
                # Use x_bind to keep the hidden input in sync with Alpine state
                # We need to map the items back to the data format [ {type, data} ]
                x_bind_value="JSON.stringify(items.map(i => ({type: i.type, data: i.data})))",
            ),
            # List of blocks
            el(
                "div",
                # Template for blocks
                el(
                    "template",
                    el(
                        "div",
                        # Block Header
                        el(
                            "div",
                            el(
                                "div",
                                # Drag handle / Icon
                                el(
                                    "span",
                                    el(
                                        "i",
                                        class_="fas fa-grip-vertical text-muted-foreground mr-2",
                                    ),
                                ),
                                el(
                                    "span",
                                    x_text="items.find(it => it.id == item.id)?.type.toUpperCase()",
                                    class_="font-bold text-xs tracking-wider text-muted-foreground",
                                ),
                                class_="flex items-center",
                            ),
                            el(
                                "div",
                                # Actions: Move Up, Move Down, Collapse, Delete
                                el(
                                    "button",
                                    el("i", class_="fas fa-chevron-up"),
                                    type="button",
                                    x_on_click="moveBlock(item.id, 'up')",
                                    class_="p-1 hover:bg-accent rounded",
                                ),
                                el(
                                    "button",
                                    el("i", class_="fas fa-chevron-down"),
                                    type="button",
                                    x_on_click="moveBlock(item.id, 'down')",
                                    class_="p-1 hover:bg-accent rounded",
                                ),
                                el(
                                    "button",
                                    el(
                                        "i",
                                        class_="fas fa-trash text-destructive",
                                    ),
                                    type="button",
                                    x_on_click="removeBlock(item.id)",
                                    class_="p-1 hover:bg-accent rounded ml-2",
                                ),
                                class_="flex items-center gap-1",
                            ),
                            class_="bg-muted border-b border-border px-4 py-2 flex items-center justify-between",
                        ),
                        # Block Body (Fields)
                        el(
                            "div",
                            # Render fields for each block type
                            *[self._render_block_fields(b) for b in self.blocks],
                            class_="p-4",
                        ),
                        class_="border border-border rounded-lg overflow-hidden bg-card mb-4",
                        x_show="true",  # Alpine handles the loop
                    ),
                    x_for="item in items",
                    key="item.id",
                ),
                class_="builder-items",
            ),
            # Add block buttons
            el(
                "div",
                el(
                    "div",
                    *[
                        el(
                            "button",
                            el("i", class_=f"fas fa-{b.icon or 'cube'} mr-2"),
                            b.label,
                            type="button",
                            x_on_click=f"addBlock('{b.name}')",
                            class_="inline-flex items-center px-4 py-2 border border-dashed border-border rounded-md shadow-sm text-sm font-medium text-foreground bg-card hover:bg-accent",
                        )
                        for b in self.blocks
                    ],
                    class_="flex flex-wrap gap-2",
                ),
                class_="mt-6 border-2 border-dashed border-border p-4 rounded-xl flex flex-col items-center justify-center",
            ),
            x_data=dumps_str(x_data),
            class_="lex-builder w-full",
        )

    def _render_block_fields(self, block: Any) -> Any:
        """Render the fields for a specific block type, wrapped in an Alpine conditional."""
        with NoContext():
            field_els = []
            for field in block.fields:
                # We need to bind the field's value to item.data[field_name]
                # Lexigram components use self.name and self.props['value']
                # We'll inject Alpine x-model into the component's props
                field.props["x-model"] = f"item.data['{field.name}']"
                field_els.append(field.render())

            return el(
                "div",
                *field_els,
                x_show=f"item.type === '{block.name}'",
                class_="space-y-4",
            )
