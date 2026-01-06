from __future__ import annotations

from typing import Any

from lexigram.ui.core.base import Component, el


class InputGroup(Component):
    """
    Input with prefix or suffix add-ons.
    """

    def __init__(
        self,
        label: str,
        name: str,
        input_type: str = "text",
        prefix: str | None = None,
        suffix: str | None = None,
        placeholder: str | None = None,
        value: str = "",
        error: str | None = None,
        **props,
    ) -> None:
        super().__init__(
            label=label,
            name=name,
            type=input_type,
            prefix=prefix,
            suffix=suffix,
            placeholder=placeholder,
            value=value,
            error=error,
            **props,
        )
        self.label = label
        self.name = name
        self.type = type
        self.prefix = prefix
        self.suffix = suffix
        self.placeholder = placeholder
        self.value = value
        self.error = error

    def render(self) -> Any:
        return el(
            "div",
            el(
                "label",
                self.label,
                for_=self.name,
                class_="block text-sm font-medium text-foreground mb-1",
            ),
            el(
                "div",
                (
                    el(
                        "div",
                        el(
                            "span",
                            self.prefix,
                            class_="text-muted-foreground sm:text-sm px-3",
                        ),
                        class_="flex items-center pointer-events-none",
                    )
                    if self.prefix
                    else ""
                ),
                el(
                    "input",
                    type=self.type,
                    name=self.name,
                    id=self.name,
                    value=self.value,
                    placeholder=self.placeholder,
                    **({"aria_describedby": f"{self.name}-error"} if self.error else {}),
                    **({"aria_invalid": "true"} if self.error else {}),
                    class_=f"block w-full min-w-0 flex-1 border-0 bg-transparent py-2 text-foreground placeholder:text-muted-foreground focus:ring-0 sm:text-sm {'pl-1' if self.prefix else 'pl-3'} {'pr-1' if self.suffix else 'pr-3'}",
                ),
                (
                    el(
                        "div",
                        el(
                            "span",
                            self.suffix,
                            class_="text-muted-foreground sm:text-sm px-3",
                        ),
                        class_="flex items-center pointer-events-none",
                    )
                    if self.suffix
                    else ""
                ),
                class_=f"flex rounded-lg shadow-sm ring-1 ring-inset focus-within:ring-2 focus-within:ring-inset transition-all duration-200 {'ring-destructive focus-within:ring-destructive' if self.error else 'ring-[var(--input)] focus-within:ring-ring'} bg-background",
            ),
            (
                el("p", self.error, id=f"{self.name}-error", class_="mt-2 text-sm text-destructive")
                if self.error
                else ""
            ),
            class_="mb-6",
        )
