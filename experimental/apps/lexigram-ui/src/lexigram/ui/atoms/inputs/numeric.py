from __future__ import annotations

from typing import Any

from lexigram.ui.atoms.inputs.base import AbstractInput
from lexigram.ui.core.base import el


class NumberInput(AbstractInput):
    """
    Number input with min/max/step validation.

    Args:
        name: Input name attribute
        value: Input value
        min: Minimum allowed value
        max: Maximum allowed value
        step: Step increment
        label: Optional label text
        error: Error message to display
        **kwargs: Additional props
    """

    def __init__(
        self,
        name: str,
        value: float | None = None,
        min_value: float | None = None,
        max_value: float | None = None,
        step: float | None = None,
        placeholder: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(name=name, value=value, **kwargs)
        self.min = min_value
        self.max = max_value
        self.step = step
        self.placeholder = placeholder

    def _render_input(self) -> Any:
        return el(
            "input",
            type="number",
            name=self.name,
            id=self.input_id,
            value=str(self.value) if self.value is not None else "",
            min=self.min,
            max=self.max,
            step=self.step,
            placeholder=self.placeholder,
            disabled=self.disabled,
            required=self.required,
            readonly=self.readonly,
            class_=self._get_input_classes(),
            **self._get_extra_props(["min", "max", "step", "placeholder"]),
        )


class Slider(AbstractInput):
    """
    Range slider input.

    Args:
        name: Input name attribute
        value: Current value
        min: Minimum value (default: 0)
        max: Maximum value (default: 100)
        step: Step increment (default: 1)
        label: Optional label text
        **kwargs: Additional props
    """

    SLIDER_CLASSES = (
        "w-full h-2 bg-muted rounded-lg appearance-none "
        "cursor-pointer accent-[var(--primary)]"
    )

    def __init__(
        self,
        name: str,
        value: float = 0,
        min_value: float = 0,
        max_value: float = 100,
        step: float = 1,
        **kwargs: Any,
    ) -> None:
        super().__init__(name=name, value=value, **kwargs)
        self.min = min_value
        self.max = max_value
        self.step = step

    def _render_input(self) -> Any:
        return el(
            "input",
            type="range",
            name=self.name,
            id=self.input_id,
            value=self.value,
            min=self.min,
            max=self.max,
            step=self.step,
            disabled=self.disabled,
            class_=self.SLIDER_CLASSES,
        )

    def render(self) -> Any:
        """Custom render with value display."""
        slider = self._render_input()

        range_display = el(
            "div",
            el("span", str(self.min), class_="text-xs text-muted-foreground"),
            el("span", str(self.max), class_="text-xs text-muted-foreground"),
            class_="flex justify-between mt-1",
        )

        content = el("div", slider, range_display)

        if self.label:
            header = el(
                "div",
                el(
                    "label",
                    self.label,
                    class_="block text-sm font-medium text-foreground",
                ),
                el(
                    "span",
                    str(self.value),
                    class_="text-sm font-semibold text-primary",
                ),
                class_="flex justify-between mb-2",
            )
            return el("div", header, content, class_="mb-6")

        return content
