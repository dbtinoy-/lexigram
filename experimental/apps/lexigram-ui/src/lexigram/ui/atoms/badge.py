from __future__ import annotations

from typing import Any, Literal

from lexigram.ui.core.base import Component, el
from lexigram.ui.styles import get_semantic_classes

BadgeVariant = Literal[
    "default",
    "gray",
    "primary",
    "success",
    "warning",
    "danger",
    "info",
    "red",
    "yellow",
    "green",
    "blue",
    "indigo",
    "purple",
    "pink",
    "orange",
]


class Badge(Component):
    """Badge component for status indicators.

    Args:
        text: Label shown inside the badge.
        variant: Semantic colour variant.
        live: Whether the badge is an ARIA live region. Off by default.

            ``role="status"`` makes assistive technology announce the badge
            whenever its content changes, which is right for a value that
            updates in place (a job state, a reconnecting indicator) and
            wrong for the common case. Most badges are static labels -- a
            "Draft" tag, a row's plan tier -- and a table of them turns
            into a stream of announcements that drowns out the content the
            user actually navigated to. Opt in only where the badge really
            does report changing status.
        **props: Extra attributes forwarded to the rendered ``<span>``
            (``title``, ``id``, ``data_*`` and similar).
    """

    def __init__(
        self,
        text: str,
        variant: BadgeVariant = "default",
        *,
        live: bool = False,
        **props: Any,
    ) -> None:
        super().__init__(text=text, variant=variant, **props)
        self.text = text
        self.variant = variant
        self.live = live

    def render(self) -> Any:
        variant_cls = get_semantic_classes(self.variant)

        # Caller props are forwarded rather than dropped, but the badge's
        # own class list wins: a caller passing class_ extends it instead
        # of silently discarding the variant styling.
        attrs: dict[str, Any] = {
            key: value
            for key, value in self.props.items()
            if key not in ("text", "variant", "children")
        }
        extra_cls = attrs.pop("class_", None) or attrs.pop("class", None)

        classes = (
            "inline-flex items-center rounded-full border px-2.5 py-0.5 "
            "text-xs font-semibold transition-colors focus:outline-none "
            "focus:ring-2 focus:ring-ring focus:ring-offset-2 "
            f"border-transparent {variant_cls}"
        )
        if extra_cls:
            classes = f"{classes} {extra_cls}"

        if self.live:
            attrs.setdefault("role", "status")
            attrs.setdefault("aria_live", "polite")

        return el("span", self.text, class_=classes, **attrs)
