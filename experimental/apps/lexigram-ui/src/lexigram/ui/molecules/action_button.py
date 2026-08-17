"""ActionButton molecule component - standardized button with icon support."""

from __future__ import annotations

from typing import Any, Literal

from lexigram.ui.atoms.icons import get_icon
from lexigram.ui.core.base import Component, el


class ActionButton(Component):
    """Standardized action button with icon support and consistent styling."""

    def __init__(
        self,
        label: str,
        variant: Literal["primary", "secondary", "danger", "ghost", "link"] = "primary",
        icon: str | None = None,
        icon_position: Literal["left", "right"] = "left",
        size: Literal["sm", "md", "lg"] = "md",
        **props: Any,
    ) -> None:
        """
        Initialize action button.

        Args:
            label: Button text
            variant: Button style variant
            icon: Icon name (from icons.py)
            icon_position: Position of icon relative to label
            size: Button size
            **props: Additional props (HTMX attributes, type, disabled, etc.)
        """
        props.pop("color", None)
        super().__init__(
            label=label,
            color=variant,
            icon=icon,
            icon_position=icon_position,
            size=size,
            **props,
        )
        self.label = label
        self.variant = variant
        self.icon = icon
        self.icon_position = icon_position
        self.size = size

    def _get_variant_classes(self) -> str:
        """Get CSS classes for button variant."""
        variants = {
            "primary": "bg-primary text-primary-foreground hover:bg-primary/90 shadow-sm",
            "secondary": "bg-secondary text-secondary-foreground hover:bg-secondary/80 border border-border shadow-sm",
            "danger": "bg-destructive text-destructive-foreground hover:bg-destructive/90 shadow-sm",
            "ghost": "hover:bg-accent hover:text-accent-foreground",
            "link": "text-primary underline-offset-4 hover:underline bg-transparent shadow-none p-0",
        }
        return variants.get(self.variant, variants["primary"])

    def _get_size_classes(self) -> str:
        """Get CSS classes for button size."""
        sizes = {
            "sm": "h-8 px-3 text-xs",
            "md": "h-9 px-4 py-2",
            "lg": "h-10 px-8",
        }
        return sizes.get(self.size, sizes["md"])

    def render(self) -> Any:
        """Render action button."""
        # Build button classes
        base_classes = "inline-flex items-center whitespace-nowrap font-medium rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 transition-colors duration-200"
        variant_classes = self._get_variant_classes()
        size_classes = (
            self._get_size_classes() if self.variant != "link" else "px-0 py-0"
        )

        # Merge custom classes
        custom_class = self.props.get("class", self.props.get("class_", ""))
        button_classes = (
            f"{base_classes} {variant_classes} {size_classes} {custom_class}".strip()
        )

        # Build button content
        icon_size = "h-4 w-4" if self.size == "sm" else "h-5 w-5"
        icon_element = get_icon(self.icon, size=icon_size) if self.icon else None

        # Reserve icon space when requested to avoid layout shifts (e.g., table headers)
        reserve_icon = self.props.get("reserve_icon", False)

        content = []
        if icon_element and self.icon_position == "left":
            content.append(
                el("span", icon_element, class_="mr-2" if self.label else ""),
            )
        elif reserve_icon and self.icon_position == "left":
            # Placeholder that matches icon size so header text doesn't shift
            content.append(
                el(
                    "span",
                    "",
                    class_=("mr-2 " + icon_size + " inline-block icon-placeholder"),
                ),
            )

        if self.label:
            content.append(self.label)

        if icon_element and self.icon_position == "right":
            content.append(el("span", icon_element, class_="ml-2"))
        elif reserve_icon and self.icon_position == "right":
            content.append(
                el(
                    "span",
                    "",
                    class_=("ml-2 " + icon_size + " inline-block icon-placeholder"),
                ),
            )

        # Determine tag and extra attrs
        tag = "button"

        # Extract button-specific props
        button_attrs = {"class_": button_classes}

        if self.props.get("href"):
            tag = "a"
            button_attrs["href"] = self.props.get("href")  # type: ignore[assignment]
        else:
            button_attrs["type"] = self.props.get("type", "button")

        # Pass through all other props (HTMX attributes, etc.)
        for key, value in self.props.items():
            if key in [
                "label",
                "variant",
                "icon",
                "icon_position",
                "size",
                "href",
                "type",
                "class",
                "class_",
                "reserve_icon",
            ]:
                # Skip internal-only props (including reserve_icon)
                continue
            button_attrs[key] = value

        return el(tag, *content, **button_attrs)
