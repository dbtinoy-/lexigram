from __future__ import annotations

from typing import Any

from lexigram.ui.core.base import Component, el


class Row(Component):
    """Grid row component (flexible layout)."""

    def __init__(self, *children, cols: int = 1, gap: int = 4, **props) -> None:
        super().__init__(cols=cols, gap=gap, **props)
        if children:
            self.children = list(children)
        self.cols = cols
        self.gap = gap

    def render(self) -> Any:
        from lexigram.ui.core.base import raw, render_to_string

        children_html = [
            raw(render_to_string(c))
            if hasattr(c, "__html__") or hasattr(c, "render")
            else str(c)
            for c in self.children
        ]
        # Merge layout classes with any custom classes in props
        cls = f"grid grid-cols-{self.cols} gap-{self.gap}"
        custom_cls = self.props.get("class_", self.props.get("class"))
        if custom_cls:
            cls = f"{cls} {custom_cls}"

        # Create a copy of props to avoid mutating state, and remove layout-specifics
        attrs = {
            k: v
            for k, v in self.props.items()
            if k not in ("cols", "gap", "class_", "class")
        }
        return el("div", *children_html, class_=cls, **attrs)


class Col(Component):
    """Grid column component (vertical flow)."""

    def __init__(
        self,
        *children,
        gap: int = 4,
        span: int | None = None,
        **props,
    ) -> None:
        super().__init__(gap=gap, span=span, **props)
        if children:
            self.children = list(children)
        self.gap = gap
        self.span = span

    def render(self) -> Any:
        from lexigram.ui.core.base import raw, render_to_string

        children_html = [
            raw(render_to_string(c))
            if hasattr(c, "__html__") or hasattr(c, "render")
            else str(c)
            for c in self.children
        ]
        cls = f"flex flex-col gap-{self.gap}"

        # Add span class if specified
        if self.span:
            cls = f"{cls} col-span-{self.span}"

        custom_cls = self.props.get("class_", self.props.get("class"))
        if custom_cls:
            cls = f"{cls} {custom_cls}"

        attrs = {
            k: v
            for k, v in self.props.items()
            if k not in ("gap", "span", "class_", "class")
        }
        return el("div", *children_html, class_=cls, **attrs)


class Aside(Component):
    """A layout component for asides/sidebars within a page."""

    def __init__(
        self,
        *children,
        position: str = "left",
        width: str = "w-64",
        **props,
    ) -> None:
        super().__init__(position=position, width=width, **props)
        if children:
            self.children = list(children)
        self.position = position
        self.width = width

    def render(self) -> Any:
        from lexigram.ui.core.base import raw, render_to_string

        children_html = [
            raw(render_to_string(c))
            if hasattr(c, "__html__") or hasattr(c, "render")
            else str(c)
            for c in self.children
        ]
        cls = f"flex-shrink-0 {self.width} bg-card border-r border-border h-full overflow-y-auto"
        if self.position == "right":
            cls = cls.replace("border-r", "border-l")

        custom_cls = self.props.get("class_", self.props.get("class"))
        if custom_cls:
            cls = f"{cls} {custom_cls}"

        attrs = {
            k: v
            for k, v in self.props.items()
            if k not in ("position", "width", "class_", "class")
        }
        return el("aside", *children_html, class_=cls, **attrs)


class Grid(Component):
    """Generic CSS Grid component."""

    def __init__(
        self,
        *children,
        cols: int | dict[str, int] = 1,
        gap: int = 4,
        **props,
    ) -> None:
        super().__init__(cols=cols, gap=gap, **props)
        if children:
            self.children = list(children)
        self.cols = cols
        self.gap = gap

    def render(self) -> Any:
        cls = "grid"
        if isinstance(self.cols, int):
            cls += f" grid-cols-{self.cols}"
        elif isinstance(self.cols, dict):
            if "default" in self.cols:
                cls += f" grid-cols-{self.cols['default']}"
            for break_pt, count in self.cols.items():
                if break_pt != "default":
                    cls += f" {break_pt}:grid-cols-{count}"

        cls += f" gap-{self.gap}"
        custom_cls = self.props.get("class_", self.props.get("class"))
        if custom_cls:
            cls = f"{cls} {custom_cls}"

        from lexigram.ui.core.base import raw, render_to_string

        children_html = [
            raw(render_to_string(c))
            if hasattr(c, "__html__") or hasattr(c, "render")
            else str(c)
            for c in self.children
        ]
        attrs = {
            k: v
            for k, v in self.props.items()
            if k not in ("cols", "gap", "class_", "class")
        }
        return el("div", *children_html, class_=cls, **attrs)


class Stack(Component):
    """Vertical stack component (flex column)."""

    def __init__(self, *children, gap: int = 4, **props) -> None:
        super().__init__(gap=gap, **props)
        if children:
            self.children = list(children)
        self.gap = gap

    def render(self) -> Any:
        cls = f"flex flex-col gap-{self.gap}"
        custom_cls = self.props.get("class_", self.props.get("class"))
        if custom_cls:
            cls = f"{cls} {custom_cls}"

        from lexigram.ui.core.base import raw, render_to_string

        children_html = [
            raw(render_to_string(c))
            if hasattr(c, "__html__") or hasattr(c, "render")
            else str(c)
            for c in self.children
        ]
        attrs = {
            k: v for k, v in self.props.items() if k not in ("gap", "class_", "class")
        }
        return el("div", *children_html, class_=cls, **attrs)


class Container(Component):
    def __init__(self, *children, **props) -> None:
        super().__init__(**props)
        if children:
            self.children = list(children)

    def render(self) -> Any:
        from lexigram.ui.core.base import raw, render_to_string

        children_html = [
            raw(render_to_string(c))
            if hasattr(c, "__html__") or hasattr(c, "render")
            else str(c)
            for c in self.children
        ]
        cls = "max-w-7xl mx-auto px-4"
        custom_cls = self.props.get("class_", self.props.get("class"))
        if custom_cls:
            cls = f"{cls} {custom_cls}"

        attrs = {k: v for k, v in self.props.items() if k not in ("class_", "class")}
        return el("div", *children_html, class_=cls, **attrs)
