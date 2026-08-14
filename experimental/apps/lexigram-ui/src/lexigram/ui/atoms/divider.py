from __future__ import annotations

from typing import Any

from lexigram.ui.core.base import Component, el


class Divider(Component):
    """Render a divider line.

    Args:
        orientation: 'horizontal' or 'vertical'
        class_name: Additional CSS classes
    """

    def __init__(
        self,
        orientation: str = "horizontal",
        class_name: str = "",
        **props: Any,
    ) -> None:
        super().__init__(**props)
        self.orientation = orientation
        self.class_name = class_name

    def render(self) -> Any:
        extra_attrs = {
            k: v
            for k, v in self.props.items()
            if k not in ("class_", "class", "children")
        }
        if self.orientation == "vertical":
            cls = f"border-l border-border {self.class_name}".strip()
            return el("div", "", class_=cls, **extra_attrs)

        cls = f"border-t border-border mb-6 {self.class_name}".strip()
        return el("hr", class_=cls, **extra_attrs)
