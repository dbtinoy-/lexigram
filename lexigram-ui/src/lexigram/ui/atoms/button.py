from __future__ import annotations

from typing import Any, Literal

from lexigram.ui.core.base import Component, el

ButtonVariant = Literal[
    "default",
    "secondary",
    "destructive",
    "outline",
    "ghost",
    "link",
]

ButtonSize = Literal["default", "xs", "sm", "lg", "xl", "icon"]


_VARIANT_CLASSES: dict[str, str] = {
    "default": "bg-primary text-primary-foreground hover:bg-primary/90",
    "secondary": "bg-secondary text-secondary-foreground hover:bg-secondary/80",
    "destructive": (
        "bg-destructive text-destructive-foreground hover:bg-destructive/90"
    ),
    "outline": (
        "border border-input bg-background hover:bg-accent hover:text-accent-foreground"
    ),
    "ghost": (
        "hover:bg-accent hover:text-accent-foreground"
    ),
    "link": (
        "text-primary underline-offset-4 hover:underline"
    ),
}

_SIZE_CLASSES: dict[str, str] = {
    "default": "h-10 px-4 py-2",
    "xs": "h-7 rounded-md px-2 text-xs",
    "sm": "h-9 rounded-md px-3 text-xs",
    "lg": "h-11 rounded-md px-8",
    "xl": "h-12 rounded-md px-10 text-base",
    "icon": "h-10 w-10",
}

_BASE_CLASSES = (
    "inline-flex items-center justify-center gap-2 whitespace-nowrap "
    "rounded-md text-sm font-medium ring-offset-background "
    "transition-colors "
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 "
    "disabled:pointer-events-none disabled:opacity-50 "
    "[&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 "
)


class Button(Component):
    """Button with ShadCN-compatible variants and sizes.

    Args:
        label: Button text.
        variant: Visual style variant.
        size: Size variant.
        as_child: If True, renders as first child element.
        **props: Additional HTML attributes.
    """

    def __init__(
        self,
        label: str = "",
        *,
        variant: ButtonVariant = "default",
        size: ButtonSize = "default",
        as_child: bool = False,
        **props: Any,
    ) -> None:
        super().__init__(as_child=as_child, **props)
        self.label = label
        self.variant = variant
        self.size = size

    def render(self) -> Any:
        variant_cls = _VARIANT_CLASSES.get(self.variant, _VARIANT_CLASSES["default"])
        size_cls = _SIZE_CLASSES.get(self.size, _SIZE_CLASSES["default"])

        cls = " ".join(filter(None, [_BASE_CLASSES, variant_cls, size_cls]))

        custom_cls = self.props.get("class_") or self.props.get("class")
        if custom_cls:
            cls = f"{cls} {custom_cls}"

        extra_attrs = {
            k: v
            for k, v in self.props.items()
            if k not in ("class_", "class", "children")
        }
        extra_attrs.pop("label", None)
        extra_attrs.pop("type", None)

        return el("button", self.label, class_=cls, type="button", **extra_attrs)


class SubmitButton(Component):
    """Submit button with automatic loading state.

    Args:
        label: Button text.
        variant: Same as Button.
        size: Same as Button.
        disabled: Whether button is disabled.
        **props: Additional attributes.
    """

    def __init__(
        self,
        label: str = "Submit",
        *,
        loading_label: str = "Submitting...",
        variant: ButtonVariant = "default",
        size: ButtonSize = "default",
        disabled: bool = False,
        **props: Any,
    ) -> None:
        super().__init__(**props)
        self.label = label
        self.loading_label = loading_label
        self.variant = variant
        self.size = size
        self.disabled = disabled

    def render(self) -> Any:
        from lexigram.ui.atoms.spinner import Spinner

        variant_cls = _VARIANT_CLASSES.get(self.variant, _VARIANT_CLASSES["default"])
        size_cls = _SIZE_CLASSES.get(self.size, _SIZE_CLASSES["default"])
        cls = " ".join(filter(None, [_BASE_CLASSES, variant_cls, size_cls]))

        return el(
            "button",
            el(
                "span",
                self.label,
                x_show="!loading",
                class_="inline-flex items-center",
            ),
            el(
                "span",
                el(
                    "span",
                    Spinner(size="sm"),
                    class_="inline-block mr-2",
                ),
                self.loading_label,
                x_show="loading",
                x_cloak=True,
                class_="inline-flex items-center",
            ),
            type="submit",
            class_=cls,
            disabled=self.disabled,
            x_data="{ loading: false }",
            x_on_click="loading = true",
            x_on_htmx_after_request="loading = false",
        )
