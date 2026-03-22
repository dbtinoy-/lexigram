from __future__ import annotations

from typing import Any

from lexigram.ui import Component, DateInput, el


class DateRangeFilter(Component):
    """
    A simple date range filter with start and end inputs.
    """

    def __init__(
        self,
        name_prefix: str = "date",
        label: str = "Date Range",
        **props,
    ) -> None:
        super().__init__(name_prefix=name_prefix, label=label, **props)
        self.name_prefix = name_prefix
        self.label = label

    def render(self) -> Any:
        return el(
            "div",
            el(
                "label",
                self.label,
                class_="block text-sm font-medium text-foreground mb-1.5",
            ),
            el(
                "div",
                DateInput(
                    name=f"{self.name_prefix}_start",
                    class_="rounded-t-md sm:rounded-l-md sm:rounded-t-none",
                    hx_get=self.props.get("hx_get"),
                    hx_trigger="change",
                    hx_target=self.props.get("hx_target", "#main-content"),
                ).render(),
                el(
                    "span",
                    "to",
                    class_="px-2 text-muted-foreground text-sm self-center sm:py-0 py-2",
                ),
                DateInput(
                    name=f"{self.name_prefix}_end",
                    class_="rounded-b-md sm:rounded-r-md sm:rounded-b-none",
                    hx_get=self.props.get("hx_get"),
                    hx_trigger="change",
                    hx_target=self.props.get("hx_target", "#main-content"),
                ).render(),
                class_="flex flex-col sm:flex-row",
            ),
            class_="min-w-[300px]",
        )
