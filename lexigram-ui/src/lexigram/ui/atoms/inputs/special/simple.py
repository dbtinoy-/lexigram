from __future__ import annotations

from typing import Any

from lexigram.ui.atoms.inputs.base import AbstractInput
from lexigram.ui.core.base import el


class Hidden(AbstractInput):
    """Hidden input field."""

    def _render_input(self) -> Any:
        return el(
            "input",
            type="hidden",
            name=self.name,
            value=self.value,
            id=self.input_id,
        )

    def render(self) -> Any:
        return self._render_input()


class TimePicker(AbstractInput):
    """Time selection input."""

    def _render_input(self) -> Any:
        return el(
            "input",
            type="time",
            name=self.name,
            id=self.input_id,
            value=self.value or "",
            disabled=self.disabled,
            class_=self._get_input_classes("pl-3 pr-3"),
            **self._get_extra_props(),
        )


class ColorPicker(AbstractInput):
    """Color selection input."""

    def _render_input(self) -> Any:
        return el(
            "input",
            type="color",
            name=self.name,
            id=self.input_id,
            value=self.value or "#000000",
            disabled=self.disabled,
            class_="h-10 w-20 rounded border border-input bg-background cursor-pointer",
            **self._get_extra_props(),
        )
