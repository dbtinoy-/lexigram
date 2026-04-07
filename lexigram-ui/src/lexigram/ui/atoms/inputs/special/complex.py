from __future__ import annotations

from typing import Any

from lexigram import serialization as json
from lexigram.serialization import dumps_str
from lexigram.ui.atoms.inputs.base import AbstractInput
from lexigram.ui.core.base import el


class Rating(AbstractInput):
    """Star rating component."""

    def __init__(
        self,
        name: str,
        max_value: int = 5,
        **kwargs,
    ) -> None:
        super().__init__(name=name, **kwargs)
        self.max = max_value

    def _render_input(self) -> Any:
        stars = []
        current_val = int(self.value or 0)
        for i in range(1, self.max + 1):
            is_active = i <= current_val
            color = "text-warning" if is_active else "text-muted-foreground"
            star = el(
                "button",
                el(
                    "svg",
                    el(
                        "path",
                        d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z",
                    ),
                    class_=f"w-6 h-6 {color}",
                    viewBox="0 0 20 20",
                    fill="currentColor",
                ),
                type="button",
                disabled=self.disabled,
                class_="focus:outline-none",
            )
            stars.append(star)

        hidden_input = el("input", type="hidden", name=self.name, value=current_val)

        return el("div", *stars, hidden_input, class_="flex items-center gap-1")

    def render(self) -> Any:
        content = self._render_input()

        if not self.label:
            return content

        return el(
            "div",
            el(
                "label",
                self.label,
                class_="block text-sm font-medium text-foreground mb-2",
            ),
            content,
            self._render_error(),
            class_="mb-6",
        )


class TagsInput(AbstractInput):
    """
    Premium tags input using Alpine.js.
    Allows adding strings as tags/chips.
    """

    def __init__(
        self,
        name: str,
        placeholder: str = "Add tag...",
        **kwargs,
    ) -> None:
        super().__init__(name=name, **kwargs)
        self.placeholder = placeholder

    def _render_input(self) -> Any:
        if isinstance(self.value, str):
            tags_list = list(
                filter(
                    lambda v: v.strip(),
                    (v.strip() for v in self.value.split(",")),
                ),
            )
        else:
            tags_list = self.value or []

        initial_tags = dumps_str(tags_list)

        container_classes = (
            "block w-full rounded-lg border-0 p-1.5 shadow-sm ring-1 ring-inset sm:text-sm min-h-[42px] transition-all duration-200 bg-background "
            f"{'ring-destructive focus-within:ring-destructive' if self.error else 'ring-[var(--input)] focus-within:ring-ring'} "
            f"{'opacity-50 cursor-not-allowed' if self.disabled else ''}"
        )

        x_data = f"{{ tags: {initial_tags}, inputValue: '', addTag() {{ if(this.inputValue.trim() && !this.tags.includes(this.inputValue.trim())) {{ this.tags.push(this.inputValue.trim()); this.inputValue = ''; }} }}, removeTag(index) {{ this.tags.splice(index, 1); }} }}"

        chips = el(
            "template",
            el(
                "span",
                el("span", **{"x-text": "tag"}),
                el(
                    "button",
                    el(
                        "svg",
                        el(
                            "path",
                            d="M6 18L18 6M6 6l12 12",
                            stroke_linecap="round",
                            stroke_linejoin="round",
                            stroke_width="2",
                        ),
                        class_="w-3 h-3",
                        fill="none",
                        viewBox="0 0 24 24",
                        stroke="currentColor",
                    ),
                    type="button",
                    **{"@click": "removeTag(index)"},
                    class_="ml-1 hover:text-primary focus:outline-none",
                ),
                class_="inline-flex items-center px-2.5 py-0.5 rounded-md text-sm font-medium bg-primary/10 text-primary mr-2 mb-1",
            ),
            **{"x-for": "(tag, index) in tags", ":key": "index"},
        )

        input_el = el(
            "input",
            type="text",
            placeholder=self.placeholder if not tags_list else "",
            class_="flex-1 border-0 focus:ring-0 bg-transparent text-foreground p-1 min-w-[120px] sm:text-sm",
            disabled=self.disabled,
            **{
                "x-model": "inputValue",
                "@keydown.enter.prevent": "addTag()",
                "@keydown.comma.prevent": "addTag()",
                "@keydown.backspace": "if(!inputValue && tags.length) removeTag(tags.length - 1)",
            },
        )

        hidden_input = el(
            "input",
            type="hidden",
            name=self.name,
            **{":value": "tags.join(',')"},
        )

        content = el(
            "div",
            chips,
            input_el,
            hidden_input,
            class_="flex flex-wrap items-center",
            **{"x-data": x_data},
        )

        return el("div", content, class_=container_classes)

    def render(self) -> Any:
        content = self._render_input()

        if not self.label:
            return content

        return el(
            "div",
            el(
                "label",
                self.label,
                for_=self.input_id,
                class_="block text-sm font-medium text-foreground mb-1",
            ),
            content,
            self._render_error(),
            class_="mb-6",
        )


class KeyValueField(AbstractInput):
    """
    Component for editing key-value pairs (JSON dictionary).
    """

    def __init__(
        self,
        name: str,
        key_label: str = "Key",
        value_label: str = "Value",
        **kwargs,
    ) -> None:
        super().__init__(name=name, **kwargs)
        self.key_label = key_label
        self.value_label = value_label

    def _render_input(self) -> Any:
        from lexigram.serialization import loads_str

        val = self.value
        if isinstance(val, str):
            try:
                val = loads_str(val)
            except (ValueError, TypeError, json.JSONDecodeError):
                val = {}

        if isinstance(val, list):
            tmp = {}
            for item in val:
                if isinstance(item, dict) and "key" in item:
                    tmp[item.get("key")] = item.get("value")
                elif isinstance(item, (list, tuple)) and len(item) >= 2:
                    tmp[item[0]] = item[1]
            val = tmp

        if not isinstance(val, dict):
            val = {}

        initial_data = dumps_str(
            [{"key": kv[0], "value": kv[1]} for kv in (val or {}).items()],
        )

        _container_id = f"kv_{self.name}"
        x_data = f"{{ rows: {initial_data}, addRow() {{ this.rows.push({{key: '', value: ''}}); }}, removeRow(index) {{ this.rows.splice(index, 1); }}, getSerialized() {{ let obj = {{}}; this.rows.forEach(r => {{ if(r.key) obj[r.key] = r.value; }}); return JSON.stringify(obj); }} }}"

        header = el(
            "div",
            el(
                "div",
                self.key_label,
                class_="text-xs font-semibold text-muted-foreground flex-1",
            ),
            el(
                "div",
                self.value_label,
                class_="text-xs font-semibold text-muted-foreground flex-1",
            ),
            el("div", "", class_="w-8"),
            class_="flex gap-4 mb-2 px-2",
        )

        row_template = el(
            "template",
            el(
                "div",
                el(
                    "input",
                    type="text",
                    **{"x-model": "row.key"},
                    placeholder="Key",
                    class_="flex-1 rounded-lg border-input bg-background text-sm focus:ring-ring focus:border-ring",
                    disabled=self.disabled,
                ),
                el(
                    "input",
                    type="text",
                    **{"x-model": "row.value"},
                    placeholder="Value",
                    class_="flex-1 rounded-lg border-input bg-background text-sm focus:ring-ring focus:border-ring",
                    disabled=self.disabled,
                ),
                el(
                    "button",
                    el(
                        "svg",
                        el(
                            "path",
                            d="M6 18L18 6M6 6l12 12",
                            stroke_linecap="round",
                            stroke_linejoin="round",
                            stroke_width="2",
                        ),
                        fill="none",
                        viewBox="0 0 24 24",
                        stroke="currentColor",
                        class_="w-4 h-4",
                    ),
                    type="button",
                    **{"@click": "removeRow(index)"},
                    class_="p-1 text-muted-foreground hover:text-destructive transition-colors duration-200",
                ),
                class_="flex gap-4 mb-2 items-center px-1",
            ),
            **{"x-for": "(row, index) in rows", ":key": "index"},
        )

        add_button = el(
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
            "Add Pair",
            type="button",
            **{"@click": "addRow()"},
            class_="mt-2 inline-flex items-center px-3 py-1.5 text-xs font-medium text-primary bg-primary/5 hover:bg-primary/15 rounded-lg transition-colors duration-200",
            disabled=self.disabled,
        )

        hidden_input = el(
            "input",
            type="hidden",
            name=self.name,
            **{":value": "getSerialized()"},
        )

        return el(
            "div",
            header,
            row_template,
            add_button,
            hidden_input,
            class_="p-3 border border-border rounded-xl bg-background",
            **{"x-data": x_data},
        )

    def render(self) -> Any:
        content = self._render_input()

        if not self.label:
            return content

        return el(
            "div",
            el(
                "label",
                self.label,
                class_="block text-sm font-medium text-foreground mb-1",
            ),
            content,
            self._render_error(),
            class_="mb-6",
        )
