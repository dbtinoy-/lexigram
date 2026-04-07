from __future__ import annotations

from typing import Any

from lexigram.ui.atoms.inputs.base import AbstractInput
from lexigram.ui.core.base import el


class DateInput(AbstractInput):
    """Date input with label and error support."""

    def __init__(
        self,
        name: str,
        min_value: str | None = None,
        max_value: str | None = None,
        input_type: str = "date",
        **kwargs,
    ) -> None:
        super().__init__(name=name, **kwargs)
        self.type = input_type
        self.min = min_value
        self.max = max_value

    def _render_input(self) -> Any:
        attrs = {
            "type": self.type,
            "name": self.name,
            "id": self.input_id,
            "value": str(self.value) if self.value is not None else "",
            "disabled": self.disabled,
            "required": self.required,
            "readonly": self.readonly,
            "class_": self._get_input_classes("pl-3 pr-3"),
            "aria-invalid": "true" if self.error else None,
            "aria-describedby": f"{self.name}-error" if self.error else None,
            "aria-required": "true" if self.required else None,
        }

        if self.min:
            attrs["min"] = self.min
        if self.max:
            attrs["max"] = self.max

        return el(
            "input",
            **attrs,
            **self._get_extra_props(exclude=["min", "max", "type"]),
        )
