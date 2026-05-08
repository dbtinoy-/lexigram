from __future__ import annotations

from typing import Any

from lexigram.ui.atoms.button import Button
from lexigram.ui.core.base import Component, el, raw, render_to_string


class Card(Component):
    """Refined Card component for better aesthetics."""

    def __init__(
        self,
        title: str | Any | None = None,
        content: str | Any | None = None,
        footer: Any = None,
        *,
        as_child: bool = False,
        **props: Any,
    ) -> None:
        super().__init__(
            title=title, content=content, footer=footer, as_child=as_child, **props
        )
        self.title = title
        self.content = content
        self.footer = footer

    def render(self) -> Any:
        # Merge classes
        cls = "bg-card text-card-foreground border border-border rounded-xl overflow-hidden mb-6"
        custom_cls = self.props.get("class_", self.props.get("class"))
        if custom_cls:
            cls = f"{cls} {custom_cls}"

        # Clean attrs
        attrs = {
            k: v
            for k, v in self.props.items()
            if k not in ("title", "content", "footer", "actions", "class_", "class")
        }

        # Header
        header = None
        if self.title:
            title_content = self.title
            if not hasattr(title_content, "__html__"):
                title_content = str(title_content)
            header = el(
                "div",
                title_content,
                class_="px-6 py-4 border-b border-border font-semibold text-card-foreground card-header",
            )

        # Body
        body_content = self.content or ""
        if not hasattr(body_content, "__html__"):
            body_content = render_to_string(body_content)

        # Add any children from Streamlit-style usage
        if self.children:
            body_content += "".join(render_to_string(c) for c in self.children)

        body = el("div", raw(body_content), class_="px-6 py-4 card-body")

        # Footer / Actions (for backward compatibility)
        footer_el = None
        actions = self.props.get("actions", [])

        if self.footer or actions:
            footer_children = []
            if self.footer:
                footer_children.append(self.footer)

            for a in actions:
                if hasattr(a, "__html__") or (
                    hasattr(a, "render") and callable(a.render)
                ):
                    footer_children.append(a)
                else:
                    # Render string actions as buttons
                    footer_children.append(
                        Button(str(a), color="primary", class_="mx-1"),
                    )

            footer_content = raw("".join(render_to_string(c) for c in footer_children))
            footer_el = el(
                "div",
                footer_content,
                class_="px-6 py-4 bg-muted border-t border-border card-footer",
            )

        return el("div", header, body, footer_el, class_=cls, **attrs)
