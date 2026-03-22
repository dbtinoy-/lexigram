from __future__ import annotations

from typing import Any, Literal

from lexigram.ui.core.base import Component, el

LinkVariant = Literal["default", "muted", "primary"]
LinkSize = Literal["sm", "md", "lg"]


class Link(Component):
    """Create a consistent styled link element.

    Args:
        label: Link text
        href: URL
        variant: Visual style variant
        size: Optional size (sm, md, lg)
    """

    def __init__(
        self,
        label: str,
        href: str,
        *,
        as_child: bool = False,
        variant: LinkVariant = "default",
        size: LinkSize | None = None,
        **props,
    ) -> None:
        super().__init__(as_child=as_child, **props)
        self.label = label
        self.href = href
        self.variant = variant
        self.size = size

    def render(self) -> Any:
        base_classes = ["text-sm", "font-medium", "inline-flex", "items-center"]

        if self.variant == "primary":
            base_classes.append("text-primary hover:text-primary/80")
        elif self.variant == "muted":
            base_classes.append("text-muted-foreground hover:text-foreground")
        else:
            base_classes.append("text-foreground hover:underline")

        if self.size == "sm":
            base_classes.append("text-sm")
        elif self.size == "lg":
            base_classes.append("text-lg")

        custom_cls = self.props.get("class_") or self.props.get("class")
        cls = " ".join(base_classes) + (f" {custom_cls}" if custom_cls else "")

        extra_attrs = {
            k: v
            for k, v in self.props.items()
            if k not in ("class_", "class", "children")
        }
        return el("a", self.label, href=self.href, class_=cls, **extra_attrs)
