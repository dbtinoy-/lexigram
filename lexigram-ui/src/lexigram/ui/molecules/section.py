"""
Section component for grouping form fields.

Provides titled sections with optional descriptions and collapsible functionality.
"""

from __future__ import annotations

from typing import Any

from lexigram.ui.core.base import Component, el


class Section(Component):
    """
    Form section component for grouping related fields.

    Example:
        Section(
            title="Personal Information",
            description="Basic details about the user",
            Grid(
                TextInput("first_name", label="First Name"),
                TextInput("last_name", label="Last Name"),
                cols=2
            )
        )
    """

    def __init__(
        self,
        *children,
        title: str,
        description: str | None = None,
        icon: str | None = None,
        collapsible: bool = False,
        collapsed: bool = False,
        **props,
    ):
        """
        Initialize section component.

        Args:
            *children: Child components
            title: Section title
            description: Optional description
            icon: Optional icon (emoji or icon class)
            collapsible: Whether section can be collapsed
            collapsed: Initial collapsed state
            **props: Additional properties
        """
        super().__init__(
            *children,
            title=title,
            description=description,
            icon=icon,
            collapsible=collapsible,
            collapsed=collapsed,
            **props,
        )
        self.children = children  # type: ignore[assignment]
        self.title = title
        self.description = description
        self.icon = icon
        self.collapsible = collapsible
        self.collapsed = collapsed

    def render(self) -> Any:
        """Render the section."""
        from lexigram.ui.core.base import raw, render_to_string

        # Render children
        children_html = [
            raw(render_to_string(c))
            if hasattr(c, "__html__") or hasattr(c, "render")
            else str(c)
            for c in self.children
        ]

        # Icon element
        icon_el = ""
        if self.icon:
            icon_el = el("span", self.icon, class_="text-xl mr-2")

        # Collapse button
        collapse_btn = ""
        if self.collapsible:
            collapse_btn = el(
                "button",
                type="button",
                class_="ml-2 text-muted-foreground hover:text-foreground",
                aria_expanded=str(not self.collapsed).lower(),
                x_on_click="collapsed = !collapsed",
                x_text="collapsed ? '▶' : '▼'",
            )

        # Title section
        title_section = el(
            "div",
            el(
                "h3",
                icon_el,
                self.title,
                collapse_btn,
                class_="text-lg font-semibold text-foreground flex items-center",
            ),
            el(
                "p",
                self.description,
                class_="mt-1 text-sm text-muted-foreground",
            )
            if self.description
            else "",
            class_="mb-4",
        )

        # Content section
        content_attrs: dict[str, Any] = {}
        if self.collapsible:
            content_attrs["x_show"] = "!collapsed"

        content_section = el(
            "div",
            *children_html,
            id=f"{self.title.replace(' ', '_')}_content",
            class_="space-y-4",
            **content_attrs,
        )

        section_attrs = {}
        if self.collapsible:
            section_attrs["x_data"] = (
                f"{{ collapsed: {'true' if self.collapsed else 'false'} }}"
            )

        return el(
            "div",
            title_section,
            content_section,
            class_="bg-card rounded-lg border border-border p-6 mb-6",
            **section_attrs,
        )
