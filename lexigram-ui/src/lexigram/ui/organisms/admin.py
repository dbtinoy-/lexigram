"""Admin UI organisms — AdminCard and PageLayout.

Components for building admin dashboard pages with ShadCN-compatible styling.
"""

from __future__ import annotations

from typing import Any

from lexigram.ui.core.base import Component, el, raw, render_to_string


class AdminCard(Component):
    """ShadCN-styled card for admin dashboard sections.

    Args:
        title: Optional card header text.
        content: Card body — a string, htpy element, or Component.
        **props: Additional HTML attributes applied to the outer div.
    """

    def __init__(
        self,
        title: str | Any | None = None,
        content: str | Any | None = None,
        **props: Any,
    ) -> None:
        super().__init__(title=title, content=content, **props)
        self.title = title
        self.content = content

    def render(self) -> Any:
        cls = (
            "bg-card text-card-foreground border border-border rounded-xl "
            "shadow-sm overflow-hidden"
        )
        custom_cls = self.props.get("class_") or self.props.get("class")
        if custom_cls:
            cls = f"{cls} {custom_cls}"

        attrs = {
            k: v
            for k, v in self.props.items()
            if k not in ("title", "content", "class_", "class")
        }

        header_el = None
        if self.title:
            header_el = el(
                "div",
                str(self.title),
                class_="px-6 py-4 border-b border-border font-semibold text-card-foreground",
            )

        body_content: str
        if self.content is None:
            body_content = ""
        elif hasattr(self.content, "__html__") or hasattr(self.content, "render"):
            body_content = render_to_string(self.content)
        else:
            body_content = str(self.content)

        body_el = el("div", raw(body_content), class_="px-6 py-4")

        return el("div", header_el, body_el, class_=cls, **attrs)


class PageLayout(Component):
    """Full-page admin layout wrapper with a header bar and content area.

    Args:
        title: Page title rendered in the header.
        children: Main page content — string, htpy element, Component, or list thereof.
        actions: Optional list of elements (e.g. Buttons) rendered in the header right side.
        **props: Additional HTML attributes applied to the outer wrapper div.
    """

    def __init__(
        self,
        title: str = "",
        children: Any = None,
        actions: list[Any] | None = None,
        **props: Any,
    ) -> None:
        super().__init__(**props)
        self.title = title
        if children is not None:
            self.children = children if isinstance(children, list) else [children]
        else:
            self.children = []
        self.actions = actions or []

    def render(self) -> Any:
        wrapper_cls = "flex flex-col min-h-full"
        custom_cls = self.props.get("class_") or self.props.get("class")
        if custom_cls:
            wrapper_cls = f"{wrapper_cls} {custom_cls}"

        attrs = {
            k: v
            for k, v in self.props.items()
            if k not in ("title", "children", "actions", "class_", "class")
        }

        title_el = el(
            "h1",
            self.title,
            class_="text-2xl font-semibold text-foreground",
        )

        actions_el = None
        if self.actions:
            rendered_actions = [
                raw(render_to_string(a))
                if hasattr(a, "__html__") or hasattr(a, "render")
                else str(a)
                for a in self.actions
            ]
            actions_el = el(
                "div",
                *rendered_actions,
                class_="flex items-center gap-2",
            )

        header_el = el(
            "div",
            title_el,
            actions_el,
            class_="flex items-center justify-between px-6 py-4 border-b border-border bg-background",
        )

        rendered_children = [
            raw(render_to_string(c))
            if hasattr(c, "__html__") or hasattr(c, "render")
            else str(c)
            for c in self.children
        ]
        content_el = el(
            "div",
            *rendered_children,
            class_="flex-1 p-6",
        )

        return el("div", header_el, content_el, class_=wrapper_cls, **attrs)


__all__ = ["AdminCard", "PageLayout"]
