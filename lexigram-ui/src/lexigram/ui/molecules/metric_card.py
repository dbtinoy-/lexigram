"""
MetricCard component for displaying key metrics.

Shows a number with label, optional trend indicator, and icon.
Perfect for dashboard statistics.
"""

from __future__ import annotations

from typing import Any, Literal

from lexigram.ui.core.base import Component, el

MetricCardVariant = Literal["default", "success", "warning", "danger", "info"]
TrendDirection = Literal["up", "down"]


class MetricCard(Component):
    """
    MetricProtocol card for dashboard statistics.

    Example:
        MetricCard(
            value="1,234",
            label="Total Users",
            trend="+12%",
            trend_direction="up",
            icon="👥",
            color="success"
        )
    """

    def __init__(
        self,
        value: str | float,
        label: str,
        trend: str | None = None,
        trend_direction: TrendDirection | None = None,
        icon: str | None = None,
        variant: MetricCardVariant = "default",
        **props,
    ):
        """
        Initialize metric card.

        Args:
            value: The metric value (number or formatted string)
            label: Description label
            trend: Trend indicator (e.g., "+12%", "-5%")
            trend_direction: Direction of trend ("up" or "down")
            icon: Optional icon (emoji or icon class)
            variant: Color variant
            **props: Additional properties
        """
        super().__init__(
            value=value,
            label=label,
            trend=trend,
            trend_direction=trend_direction,
            icon=icon,
            color=variant,
            **props,
        )
        self.value = value
        self.label = label
        self.trend = trend
        self.trend_direction = trend_direction
        self.icon = icon
        self.variant = variant

    def render(self) -> Any:
        """Render the metric card."""
        # Variant color classes
        variant_classes = {
            "default": "border-border",
            "success": "border-success/30 bg-success/10",
            "warning": "border-warning/30 bg-warning/10",
            "danger": "border-destructive/30 bg-destructive/10",
            "info": "border-info/30 bg-info/10",
        }

        variant_text_classes = {
            "default": "text-foreground",
            "success": "text-success",
            "warning": "text-warning",
            "danger": "text-destructive",
            "info": "text-info",
        }

        card_classes = f"bg-card rounded-xl border {variant_classes.get(self.variant, variant_classes['default'])} p-6 shadow-sm hover:shadow-md transition-shadow"
        value_classes = f"text-3xl font-bold {variant_text_classes.get(self.variant, variant_text_classes['default'])}"

        # Icon element
        icon_el = ""
        if self.icon:
            icon_el = el("div", self.icon, class_="text-3xl mb-2 opacity-50")

        # Trend element
        trend_el = ""
        if self.trend:
            trend_color = "text-success"
            trend_arrow = "↑"

            if self.trend_direction == "down":
                trend_color = "text-destructive"
                trend_arrow = "↓"

            trend_el = el(
                "div",
                el("span", trend_arrow, class_="font-bold"),
                " ",
                el("span", self.trend),
                class_=f"text-sm font-medium {trend_color} mt-1",
            )

        return el(
            "div",
            icon_el,
            el("div", str(self.value), class_=value_classes),
            el(
                "div",
                self.label,
                class_="text-sm font-medium text-muted-foreground mt-1",
            ),
            trend_el,
            class_=card_classes,
        )
