from __future__ import annotations

from typing import Any

from lexigram.serialization import dumps_str
from lexigram.ui.atoms.inputs.base import AbstractInput
from lexigram.ui.core.base import el


class Radio(AbstractInput):
    """Radio button group for single selection."""

    def __init__(
        self,
        name: str,
        choices: list[tuple[str, str]],
        inline: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(name=name, **kwargs)
        self.choices = choices
        self.inline = inline

    def _render_input(self) -> Any:
        radios = []
        for i, (val, label) in enumerate(self.choices):
            radio_id = f"{self.name}_{i}"
            inp = el(
                "input",
                type="radio",
                name=self.name,
                id=radio_id,
                value=val,
                checked=True if str(val) == str(self.value) else None,
                disabled=self.disabled,
                class_="h-4 w-4 border-input text-primary focus:ring-ring bg-background disabled:opacity-50",
            )
            item = el(
                "div",
                el("div", inp, class_="flex h-6 items-center"),
                el(
                    "div",
                    el(
                        "label",
                        label,
                        for_=radio_id,
                        class_="font-medium text-foreground text-sm",
                    ),
                    class_="ml-3",
                ),
                class_="relative flex items-start",
            )
            radios.append(item)

        container_class = "flex flex-wrap gap-4" if self.inline else "space-y-4"
        return el("div", *radios, class_=container_class)

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


class MultiSelect(AbstractInput):
    """Premium searchable tags-style multi-select."""

    def __init__(
        self,
        name: str,
        choices: list[tuple[str, str]],
        placeholder: str = "Select options...",
        **kwargs,
    ) -> None:
        super().__init__(name=name, **kwargs)
        self.choices = choices
        self.placeholder = placeholder

    def _render_input(self) -> Any:
        choices_json = dumps_str(
            [{"value": vl[0], "label": vl[1]} for vl in self.choices],
        )
        initial_values = dumps_str(self.value if self.value is not None else [])

        _container_id = f"ms_{self.name}"
        x_data = (
            f"{{ "
            f"open: false, "
            f"search: '', "
            f"selected: {initial_values}, "
            f"choices: {choices_json}, "
            f"toggle() {{ if(this.disabled) return; this.open = !this.open; if(this.open) this.$nextTick(() => this.$refs.searchInput.focus()); }}, "
            f"close() {{ this.open = false; this.search = ''; }}, "
            f"add(val) {{ if(!this.selected.includes(val)) this.selected.push(val); this.close(); }}, "
            f"remove(val) {{ this.selected = this.selected.filter(v => v !== val); }}, "
            f"get filteredChoices() {{ return this.choices.filter(c => c.label.toLowerCase().includes(this.search.toLowerCase()) && !this.selected.includes(c.value)); }}, "
            f"get selectedLabels() {{ return this.choices.filter(c => this.selected.includes(c.value)); }},"
            f"disabled: {'true' if self.disabled else 'false'}"
            f" }}"
        )

        trigger = el(
            "div",
            # Chips
            el(
                "template",
                el(
                    "span",
                    el("span", **{"x-text": "item.label"}),
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
                        **{"@click.stop": "remove(item.value)"},
                        class_="ml-1 hover:text-primary focus:outline-none",
                    ),
                    class_="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-primary/10 text-primary mr-1 mb-1",
                ),
                **{"x-for": "item in selectedLabels", ":key": "item.value"},
            ),
            # Placeholder/Search Proxy
            el(
                "span",
                self.placeholder,
                class_="text-muted-foreground text-sm py-1",
                **{"x-show": "selected.length === 0"},
            ),
            # Caret
            el(
                "div",
                el(
                    "svg",
                    el(
                        "path",
                        d="M19 9l-7 7-7-7",
                        stroke_linecap="round",
                        stroke_linejoin="round",
                        stroke_width="2",
                    ),
                    class_="w-4 h-4 text-muted-foreground",
                    fill="none",
                    viewBox="0 0 24 24",
                    stroke="currentColor",
                ),
                class_="ml-auto",
            ),
            class_=f"flex flex-wrap items-center min-h-[38px] px-3 py-1.5 rounded-lg border cursor-pointer bg-background shadow-sm transition-all duration-200 {'ring-2 ring-ring border-ring' if not self.error else 'border-destructive ring-destructive'} {'opacity-50 cursor-not-allowed' if self.disabled else 'border-input hover:border-input'}",
            **{"@click": "toggle()"},
        )

        dropdown = el(
            "div",
            el(
                "div",
                el(
                    "input",
                    type="text",
                    placeholder="Search...",
                    class_="w-full border-b border-border px-3 py-2 text-sm bg-transparent focus:ring-0 focus:outline-none text-foreground",
                    **{
                        "x-model": "search",
                        "x-ref": "searchInput",
                        "@keydown.escape": "close()",
                    },
                ),
                class_="p-1",
            ),
            el(
                "div",
                el(
                    "template",
                    el(
                        "div",
                        **{"x-text": "choice.label", "@click": "add(choice.value)"},
                        class_="px-3 py-2 text-sm cursor-pointer hover:bg-primary/5 text-popover-foreground",
                    ),
                    **{"x-for": "choice in filteredChoices", ":key": "choice.value"},
                ),
                el(
                    "div",
                    "No options found.",
                    class_="px-3 py-4 text-sm text-muted-foreground text-center",
                    **{"x-show": "filteredChoices.length === 0"},
                ),
                class_="max-h-60 overflow-y-auto",
            ),
            class_="absolute z-50 w-full mt-1 bg-popover border border-border rounded-lg shadow-xl overflow-hidden",
            **{"x-show": "open", "@click.away": "close()", "x-cloak": "true"},
        )

        hidden_input = el(
            "select",
            el(
                "template",
                el("option", **{":value": "v", "selected": "true"}),
                **{"x-for": "v in selected"},
            ),
            name=f"{self.name}[]",
            multiple="multiple",
            class_="hidden",
            **{":value": "selected"},
        )

        depends_on = self.props.get("depends_on")
        options_from = self.props.get("options_from")
        wrapper_attrs = {"x-data": x_data, "class": "relative"}

        if depends_on and options_from:
            wrapper_attrs["hx-get"] = options_from
            wrapper_attrs["hx-trigger"] = f"change from:#{depends_on}"
            wrapper_attrs["hx-target"] = "this"
            wrapper_attrs["hx-swap"] = "outerHTML"
            wrapper_attrs["hx-include"] = f"#{depends_on}"

        return el("div", trigger, dropdown, hidden_input, **wrapper_attrs)

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


class CheckboxList(AbstractInput):
    """Multiple checkboxes for list selection."""

    def __init__(
        self,
        name: str,
        choices: list[tuple[str, str]],
        inline: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(name=name, **kwargs)
        self.choices = choices
        self.inline = inline

    def _render_input(self) -> Any:
        items = []
        current_values = [str(v) for v in self.value or []]

        for i, (val, label) in enumerate(self.choices):
            check_id = f"{self.name}_{i}"
            inp = el(
                "input",
                type="checkbox",
                name=f"{self.name}[]",
                id=check_id,
                value=val,
                checked=True if str(val) in current_values else None,
                disabled=self.disabled,
                class_="h-4 w-4 rounded border-input text-primary focus:ring-ring bg-background disabled:opacity-50",
            )
            item = el(
                "div",
                el("div", inp, class_="flex h-6 items-center"),
                el(
                    "div",
                    el(
                        "label",
                        label,
                        for_=check_id,
                        class_="font-medium text-foreground text-sm",
                    ),
                    class_="ml-3",
                ),
                class_="relative flex items-start",
            )
            items.append(item)

        container_class = "flex flex-wrap gap-4" if self.inline else "space-y-4"
        return el("div", *items, class_=container_class)

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
