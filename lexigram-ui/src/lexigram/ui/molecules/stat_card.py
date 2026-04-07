from __future__ import annotations

from typing import Any

from lexigram.ui.core.base import Component, el


class StatCard(Component):
    """Dashboard metric card."""

    def __init__(
        self,
        label: str,
        value: Any,
        delta: str | None = None,
        delta_color: str = "green",
        icon: str | None = None,
        sparkline_data: list[float] | None = None,
        sparkline_color: str = "indigo",
        **props,
    ) -> None:
        super().__init__(
            label=label,
            value=value,
            delta=delta,
            delta_color=delta_color,
            icon=icon,
            sparkline_data=sparkline_data,
            sparkline_color=sparkline_color,
            **props,
        )
        self.label = label
        self.value = value
        self.delta = delta
        self.delta_color = delta_color
        self.icon = icon
        self.sparkline_data = sparkline_data
        self.sparkline_color = sparkline_color

    def _render_sparkline(self) -> Any:
        if not self.sparkline_data:
            return None

        values = list(map(float, self.sparkline_data))
        max_val = max(values, default=1.0)
        if max_val == 0:
            max_val = 1.0

        width = 80
        height = 30

        points = []
        n = len(values)
        for i, val in enumerate(values):
            x = (i / (n - 1)) * width if n > 1 else width / 2
            y = height - (val / max_val * height)
            points.append(f"{x:.1f},{y:.1f}")

        pts = " ".join(points)

        return el(
            "div",
            el(
                "svg",
                el(
                    "polyline",
                    points=pts,
                    fill="none",
                    stroke="currentColor",
                    stroke_width="2.5",
                    stroke_linecap="round",
                    stroke_linejoin="round",
                ),
                viewBox=f"0 0 {width} {height}",
                class_="w-full h-full text-primary",
                aria_hidden="true",
            ),
            class_="w-20 h-8 ml-auto self-end mb-1 opacity-80",
        )

    def render(self) -> Any:
        # Merge classes
        cls = "bg-card p-6 rounded-2xl shadow-sm border border-border hover:shadow-md transition-all duration-300"
        custom_cls = self.props.get("class_", self.props.get("class"))
        if custom_cls:
            cls = f"{cls} {custom_cls}"

        attrs = dict(
            filter(
                lambda item: (
                    item[0]
                    not in (
                        "label",
                        "value",
                        "delta",
                        "delta_color",
                        "icon",
                        "sparkline_data",
                        "sparkline_color",
                        "class_",
                        "class",
                    )
                ),
                self.props.items(),
            ),
        )

        # Icon placeholder (could integrate with Heroicons later)
        icon_el = None
        if self.icon:
            from lexigram.ui.atoms.icons import get_icon

            icon_node = get_icon(self.icon, class_name="w-6 h-6")
            icon_el = el(
                "div",
                icon_node,
                class_="p-3 rounded-full bg-primary/10 text-primary mr-4 shadow-sm border border-primary/20",
            )

        delta_el = None
        if self.delta:
            color_cls = (
                "text-success"
                if self.delta_color == "green"
                else "text-destructive"
            )
            delta_el = el(
                "span",
                self.delta,
                class_=f"text-sm font-semibold {color_cls} ml-2",
            )

        return el(
            "div",
            el(
                "div",
                el(
                    "div",
                    icon_el,
                    el(
                        "div",
                        el(
                            "p",
                            self.label,
                            class_="text-sm font-semibold text-muted-foreground truncate uppercase tracking-wider",
                        ),
                        el(
                            "div",
                            el(
                                "h3",
                                str(self.value),
                                class_="text-3xl font-extrabold text-foreground",
                            ),
                            delta_el,
                            class_="flex items-baseline mt-1",
                        ),
                    ),
                    class_="flex items-center",
                ),
                self._render_sparkline(),
                class_="flex justify-between items-center",
            ),
            class_=cls,
            **attrs,
        )
