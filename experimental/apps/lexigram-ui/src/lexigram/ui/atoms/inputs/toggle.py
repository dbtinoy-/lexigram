from __future__ import annotations

from typing import Any

from lexigram.ui.atoms.inputs.base import AbstractInput
from lexigram.ui.core.base import el


class Toggle(AbstractInput):
    """Simple checkbox toggle (use Switch from forms.py for premium toggle)."""

    def __init__(
        self, name: str, value: Any = None, checked: bool | None = None, **kwargs: Any
    ) -> None:
        # Support legacy 'checked' prop passed as kwarg
        if checked is None and "checked" in kwargs:
            checked = kwargs.pop("checked")
        # Derive checked state: explicit param wins, then bool value, else False
        if checked is not None:
            self.checked = checked
        else:
            self.checked = isinstance(value, bool) and value
        super().__init__(name=name, value=value, **kwargs)

    CHECKBOX_CLASSES = (
        "h-4 w-4 rounded border-input text-primary focus:ring-ring "
        "bg-card disabled:opacity-50"
    )

    def _render_input(self) -> Any:
        return el(
            "input",
            type="checkbox",
            name=self.name,
            id=self.input_id,
            value=self.value,
            checked=self.checked,
            disabled=self.disabled,
            class_=f"{self.CHECKBOX_CLASSES} {self.props.get('class_', '')}".strip(),
            **self._get_extra_props(exclude=["checked"]),
        )

    def render(self) -> Any:
        # Checkboxes use a different horizontal layout than the standard AbstractInput wrapper
        checkbox_el = self._render_input()

        if not self.label:
            return checkbox_el

        return el(
            "div",
            el(
                "div",
                checkbox_el,
                class_="flex h-6 items-center",
            ),
            el(
                "div",
                el(
                    "label",
                    self.label,
                    for_=self.input_id,
                    class_="font-medium text-foreground",
                ),
                class_="ml-3 text-sm leading-6",
            ),
            class_="relative flex items-start mb-4",
        )


class Checkbox(Toggle):
    """Alias for Toggle for semantic clarity."""
