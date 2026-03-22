"""Label atom — accessible form field labels and standalone text labels."""

from __future__ import annotations

from typing import Any, Literal

from lexigram.ui.core.base import Component, el

LabelSize = Literal["xs", "sm", "md", "lg"]
LabelWeight = Literal["normal", "medium", "semibold", "bold"]


class Label(Component):
    """Accessible label component for form fields and descriptive text.

    Can be used as a standalone text label or associated with a form control
    via the ``for_`` attribute (renders as HTML ``for``).

    Example::

        Label("Email address", for_="email-input", required=True)
        Label("Optional note", size="sm", weight="normal")
    """

    def __init__(
        self,
        text: str,
        for_: str | None = None,
        required: bool = False,
        size: LabelSize = "sm",
        weight: LabelWeight = "medium",
        muted: bool = False,
        **props: Any,
    ) -> None:
        """Initialise a Label atom.

        Args:
            text: The visible label text.
            for_: The ``id`` of the associated form control (renders as ``for``).
            required: When ``True`` appends a required indicator asterisk.
            size: Text size variant — ``"xs"``, ``"sm"`` (default), ``"md"``, ``"lg"``.
            weight: Font-weight variant.
            muted: When ``True`` applies a muted/secondary text colour.
            **props: Additional HTML attributes forwarded to the element.
        """
        super().__init__(text=text, for_=for_, required=required, size=size, **props)
        self.text = text
        self.for_ = for_
        self.required = required
        self.size = size
        self.weight = weight
        self.muted = muted

    def render(self) -> Any:
        """Render the label element."""
        size_classes: dict[LabelSize, str] = {
            "xs": "text-xs",
            "sm": "text-sm",
            "md": "text-base",
            "lg": "text-lg",
        }
        weight_classes: dict[LabelWeight, str] = {
            "normal": "font-normal",
            "medium": "font-medium",
            "semibold": "font-semibold",
            "bold": "font-bold",
        }
        colour_class = "text-muted-foreground" if self.muted else "text-foreground"

        css = (
            f"block {size_classes.get(self.size, 'text-sm')} "
            f"{weight_classes.get(self.weight, 'font-medium')} "
            f"{colour_class}"
        )

        children: list[Any] = [self.text]
        if self.required:
            children.append(
                el(
                    "span",
                    " *",
                    class_="text-destructive ml-0.5",
                    aria_hidden="true",
                )
            )

        attrs: dict[str, Any] = {"class_": css}
        if self.for_:
            attrs["for_"] = self.for_

        return el("label", *children, **attrs)


__all__ = ["Label"]
