from __future__ import annotations

from typing import Any

from lexigram.ui.core.base import Component, el


class SimpleAlert(Component):
    """Inline alert component for contextual feedback.

    Args:
        message: Alert message
        type: Alert type (info, success, warning, error)
        title: Optional alert title
    """

    def __init__(
        self,
        message: str,
        alert_type: str = "info",
        title: str | None = None,
        **props: Any,
    ) -> None:
        super().__init__(message=message, type=alert_type, title=title, **props)
        self.message = message
        self.type = alert_type
        self.title = title

    def render(self) -> Any:
        from lexigram.ui.atoms.icons import get_icon
        from lexigram.ui.styles.tokens import get_alert_classes, get_semantic_icon

        classes = get_alert_classes(self.type)
        icon_name = get_semantic_icon(self.type)

        return el(
            "div",
            el(
                "div",
                el(
                    "div",
                    get_icon(icon_name, class_name="h-5 w-5"),
                    class_="flex-shrink-0",
                ),
                el(
                    "div",
                    el("h3", self.title, class_="text-sm font-medium")
                    if self.title
                    else "",
                    el(
                        "div",
                        self.message,
                        class_=f"text-sm {'mt-2' if self.title else ''}",
                    ),
                    class_="ml-3",
                ),
                class_="flex",
            ),
            class_=f"rounded-md p-4 border {classes}",
            role="alert",
        )
