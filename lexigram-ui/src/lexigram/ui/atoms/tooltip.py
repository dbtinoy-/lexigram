from __future__ import annotations

from typing import Any

from lexigram.ui.core.base import Component, el


class Tooltip(Component):
    """Tooltip component with auto-positioning and ARIA accessibility support.

    The tooltip element receives ``role="tooltip"`` and a stable ``id``.
    If a trigger element is wired via ``trigger_id``, the wrapper element
    receives ``aria-describedby`` pointing to the tooltip's ``id``.

    Args:
        content: The tooltip text shown on hover.
        position: Visual position hint (default: "top").
        tooltip_id: Explicit ``id`` for the tooltip span.  Defaults to a
            generated value so ``aria-describedby`` always resolves.
        trigger_id: Optional ``id`` of the associated trigger element.
    """

    def __init__(
        self,
        content: str,
        position: str = "top",
        tooltip_id: str | None = None,
        trigger_id: str | None = None,
        **props: Any,
    ) -> None:
        super().__init__(content=content, position=position, **props)
        self.content = content
        self.position = position
        self.tooltip_id = tooltip_id or f"tooltip-{id(self)}"
        self.trigger_id = trigger_id

    def render(self) -> Any:
        wrapper_attrs: dict[str, Any] = {
            "class_": "group relative flex justify-center",
        }
        if not self.trigger_id:
            wrapper_attrs["aria_describedby"] = self.tooltip_id

        return el(
            "div",
            *self.children,
            el(
                "span",
                self.content,
                id=self.tooltip_id,
                role="tooltip",
                class_="absolute top-10 scale-0 transition-all rounded bg-popover p-2 text-xs text-popover-foreground group-hover:scale-100 z-50 whitespace-nowrap",
            ),
            **wrapper_attrs,
        )
