from __future__ import annotations

from typing import Any

from lexigram.ui import Component, el


class FilterDropdown(Component):
    """
    A dropdown filter for selecting categories or status.
    """

    def __init__(
        self,
        name: str,
        label: str,
        options: list[tuple[str, str]],
        multi: bool = False,
        **props: Any,
    ) -> None:
        super().__init__(name=name, label=label, options=options, multi=multi, **props)
        self.name = name
        self.label = label
        self.options = options
        self.multi = multi

    def render(self) -> Any:
        option_els = [
            el("option", option[1], value=option[0]) for option in self.options
        ]

        return el(
            "div",
            el(
                "label",
                self.label,
                for_=self.name,
                class_="block text-sm font-medium text-foreground mb-1.5",
            ),
            el(
                "select",
                el("option", f"All {self.label}s", value=""),
                *option_els,
                name=self.name,
                id=self.name,
                multiple=self.multi,
                class_="block w-full rounded-md border-border bg-card dark:bg-background text-sm focus:border-primary-500 focus:ring-primary-500 py-2 pl-3 pr-10 transition-colors",
                hx_get=self.props.get("hx_get"),
                hx_trigger="change",
                hx_target=self.props.get("hx_target", "#main-content"),
                hx_include=self.props.get("hx_include", "closest form"),
            ),
            class_="min-w-[150px]",
        )
