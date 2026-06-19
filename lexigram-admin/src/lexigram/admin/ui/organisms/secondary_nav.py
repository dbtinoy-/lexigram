"""Secondary navigation column for cluster centers (e.g. Infrastructure).

Mirrors the settings Configuration Center sidebar design: one group per
top-level entry — an icon+label header row with indented child links —
without a card container.
"""

from __future__ import annotations

from typing import Any

from lexigram.ui import Component, el


class ClusterLayout(Component):
    """Two-column content layout for cluster centers.

    Renders the secondary nav sidebar next to the page content, inside
    the content section (settings ConfigLayout pattern). Cluster pages
    own their layout so ``#main-content`` stays a plain wrapper.
    """

    def __init__(
        self,
        items: list[dict[str, Any]],
        content: Any,
        **props: Any,
    ) -> None:
        super().__init__(items=items, content=content, **props)
        self.items = items
        self.content = content

    def render(self) -> Any:
        return el(
            "div",
            SecondaryNav(items=self.items).render(),
            el("div", self.content, class_="flex-1 min-w-0"),
            class_="flex flex-col md:flex-row gap-6",
        )


class SecondaryNav(Component):
    """Secondary sidebar column shown inside a cluster center.

    Renders a flat vertical list of linked sections (with optional nested
    child links) beside the main content area, styled after the settings
    sidebar groups.
    """

    def __init__(
        self,
        items: list[dict[str, Any]],
        title: str = "",
        **props,
    ) -> None:
        super().__init__(items=items, title=title, **props)
        self.items = items
        self.title = title

    def render(self) -> Any:
        groups = [self._render_group(item) for item in self.items]
        return el(
            "nav",
            *groups,
            class_="w-full md:w-64 flex-shrink-0",
            aria_label=self.title or "Secondary navigation",
        )

    def _render_group(self, item: dict[str, Any]) -> Any:
        """Render one group: header link plus indented child links."""
        active = bool(item.get("active"))
        header = el(
            "a",
            self._render_header_icon(item.get("icon")),
            el("span", item.get("label", ""), class_="font-medium"),
            href=item.get("href", "#"),
            class_=(
                "flex items-center gap-2 px-3 py-2 text-sm "
                + (
                    "text-primary-700 dark:text-primary-400"
                    if active
                    else "text-muted-foreground dark:text-muted-foreground"
                )
            ),
            title=item.get("label", ""),
        )

        children = [
            el(
                "a",
                el("span", child.get("label", ""), class_="truncate"),
                href=child.get("href", "#"),
                class_=(
                    "block px-3 py-2 pl-9 text-sm rounded-lg transition-colors "
                    + (
                        "bg-primary-50 text-primary-700 dark:bg-primary-900/30 "
                        "dark:text-primary-400 font-medium"
                        if child.get("active")
                        else "text-muted-foreground hover:bg-muted "
                        "dark:text-muted-foreground dark:hover:bg-card"
                    )
                ),
                title=child.get("label", ""),
            )
            for child in item.get("children", [])
        ]

        nodes: list[Any] = [header]
        if children:
            nodes.append(el("div", *children, class_="space-y-1"))

        return el("div", *nodes, class_="mb-4")

    def _render_header_icon(self, icon_name: Any) -> Any:
        if not icon_name:
            return el("span", class_="w-5 h-5 flex-shrink-0")
        try:
            from lexigram.ui import get_icon

            return get_icon(
                icon_name,
                class_name="w-5 h-5 opacity-70",
            )
        except (ImportError, ModuleNotFoundError, AttributeError):
            return el("span", "●", class_="text-muted-foreground")


__all__ = ["ClusterLayout", "SecondaryNav"]
