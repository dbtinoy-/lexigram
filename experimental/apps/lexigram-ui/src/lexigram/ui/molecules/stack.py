"""Stack layout component.

Renders a vertical flex-column container with configurable gap between
children.  Built on top of the ``htpy`` element builder.
"""

from __future__ import annotations

from typing import Any

from htpy import el as _el

el: Any = _el


class Stack:
    """A vertical flex-column layout container.

    Stacks its *children* elements vertically with a Tailwind CSS gap.

    Args:
        children: Sequence of child elements to render inside the stack.
        gap: Tailwind spacing unit for ``gap-*`` (e.g. ``6`` → ``gap-6``).
        class_: Additional CSS classes appended to the container element.

    Example::

        content = Stack(
            gap=4,
            children=[
                el("h2", "Title"),
                el("p", "Body text"),
            ],
        )
    """

    def __init__(
        self,
        children: list[Any] | None = None,
        gap: int = 4,
        class_: str = "",
    ) -> None:
        self.children: list[Any] = children or []
        self.gap = gap
        self.class_ = class_

    def __iter__(self) -> Any:
        """Render as an htpy-compatible element iterator."""
        base_classes = f"flex flex-col gap-{self.gap}"
        if self.class_:
            base_classes = f"{base_classes} {self.class_}"
        yield from el(
            "div",
            self.children,
            class_=base_classes,
        )

    def __html__(self) -> str:
        """Return the rendered HTML string."""
        parts: list[str] = []
        base_classes = f"flex flex-col gap-{self.gap}"
        if self.class_:
            base_classes = f"{base_classes} {self.class_}"
        parts.append(f'<div class="{base_classes}">')
        for child in self.children:
            if hasattr(child, "__html__"):
                parts.append(child.__html__())
            elif hasattr(child, "__iter__"):
                try:
                    parts.extend(str(c) for c in child)
                except TypeError:
                    parts.append(str(child))
            else:
                parts.append(str(child))
        parts.append("</div>")
        return "".join(parts)

    def __str__(self) -> str:
        return self.__html__()


__all__ = ["Stack"]
