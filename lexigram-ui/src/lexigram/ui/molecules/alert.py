from __future__ import annotations

from typing import Any, Literal

from lexigram.ui.core.base import Component, el
from lexigram.ui.molecules.action_button import ActionButton
from lexigram.ui.styles import get_alert_classes
from lexigram.ui.styles.tokens import get_semantic_icon

AlertVariant = Literal["info", "success", "warning", "error", "danger"]


class Alert(Component):
    """Alert component for notifications and messages."""

    def __init__(
        self,
        message: str,
        variant: AlertVariant = "info",
        dismissible: bool = False,
        **props: Any,
    ) -> None:
        super().__init__(
            message=message,
            variant=variant,
            dismissible=dismissible,
            **props,
        )
        self.message = message
        self.variant = variant
        self.dismissible = dismissible

    def render(self) -> Any:
        from lexigram.ui.atoms.icons import get_icon

        variant_cls = get_alert_classes(self.variant)
        icon_name = get_semantic_icon(self.variant)

        content = [
            el(
                "div",
                get_icon(icon_name, class_name="w-5 h-5"),
                class_="mr-2 flex-shrink-0",
            ),
            el("span", self.message, class_="flex-1"),
        ]

        if self.dismissible:
            content.append(
                ActionButton(
                    label="",
                    icon="x",
                    color="ghost",
                    size="sm",
                    type="button",
                    onclick="this.parentElement.remove()",
                    class_="ml-auto text-xl font-bold opacity-50 hover:opacity-100",
                    aria_label="Dismiss alert",
                ).render(),
            )

        return el(
            "div",
            *content,
            class_=f"flex items-center px-4 py-3 rounded-lg border {variant_cls}",
            role="alert",
        )
