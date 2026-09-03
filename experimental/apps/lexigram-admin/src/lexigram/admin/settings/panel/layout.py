"""Configuration Center layout component.

This is a nested layout that renders inside the admin shell's #main-content.
It provides a secondary sidebar for configuration categories while the main
admin chrome (topbar, primary sidebar) remains intact.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.ui import Card, Component, el

if TYPE_CHECKING:
    from lexigram.admin.settings.panel.types import ConfigCategory

__all__ = ["ConfigLayout"]


class ConfigLayout(Component):
    """Two-column layout for Configuration Center.

    Renders a secondary sidebar with category groups and a main content area
    for the active configuration form. Designed to be placed inside the admin
    shell's main content area.

    Example:
        ```python
        layout = ConfigLayout(
            categories=categories,
            active_category="env",
            active_namespace="system.core",
            content=form_component,
        )
        return await self.render_admin(request, layout, title="Configuration")
        ```
    """

    def __init__(
        self,
        categories: list[ConfigCategory],
        active_category: str | None = None,
        active_namespace: str | None = None,
        content: Any = None,
        title: str = "Configuration",
        admin_prefix: str = "/admin",
        panel_links: list[Any] | None = None,
        **props,
    ) -> None:
        super().__init__(**props)
        self.categories = categories
        self.active_category = active_category
        self.active_namespace = active_namespace
        self.content = content
        self.title = title
        self.admin_prefix = admin_prefix.rstrip("/") or "/admin"
        self.panel_links = panel_links or []

    def render(self) -> Any:
        """Render the full two-column configuration layout."""
        return el(
            "div",
            self._render_header(),
            el(
                "div",
                self._render_sidebar(),
                self._render_main(),
                class_="flex flex-col md:flex-row gap-6",
            ),
        )

    def _render_header(self) -> Any:
        """Render page header with title and description."""
        return el(
            "div",
            el(
                "h1",
                self.title,
                class_="text-2xl font-bold text-foreground",
            ),
            el(
                "p",
                "Manage system configuration, environment variables, and application settings.",
                class_="text-muted-foreground mt-1",
            ),
            class_="mb-2",
        )

    def _render_sidebar(self) -> Any:
        """Render the category navigation sidebar."""
        groups = []

        for category in sorted(self.categories, key=lambda c: c.order):
            is_active_category = category.name == self.active_category

            # Category header
            header = el(
                "div",
                self._render_icon(category.icon),
                el("span", category.label, class_="font-medium"),
                class_=f"flex items-center gap-2 px-3 py-2 text-sm {'text-primary-700 dark:text-primary-400' if is_active_category else 'text-muted-foreground dark:text-muted-foreground'}",
            )

            # Spec links within category
            spec_links = []
            for spec in category.specs:
                is_active_spec = spec.namespace == self.active_namespace

                spec_links.append(
                    el(
                        "a",
                        el("span", spec.label or spec.namespace, class_="truncate"),
                        href=f"{self.admin_prefix}/settings/{spec.namespace}",
                        hx_get=f"{self.admin_prefix}/settings/{spec.namespace}",
                        hx_target="#main-content",
                        hx_swap="innerHTML",
                        hx_push_url="true",
                        data_admin_navigation=True,
                        data_settings_nav=True,
                        aria_current="page" if is_active_spec else None,
                        class_=f"block px-3 py-2 pl-9 text-sm rounded-lg transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring {'bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-400 font-medium' if is_active_spec else 'text-muted-foreground hover:bg-muted dark:text-muted-foreground dark:hover:bg-card'}",
                    ),
                )

            # Category group
            groups.append(
                el(
                    "div",
                    header,
                    el("div", *spec_links, class_="space-y-1")
                    if spec_links
                    else el(
                        "div",
                        "No configurations",
                        class_="px-3 py-2 pl-9 text-xs text-muted-foreground italic",
                    ),
                    class_="mb-4",
                ),
            )

        return el(
            "nav",
            *groups,
            *self._render_panel_groups(),
            class_="w-full md:w-64 flex-shrink-0",
            aria_label="Configuration categories",
        )

    def _render_panel_groups(self) -> list[Any]:
        """Contributor-panel link groups (R50, docs/09-01-2026/46-…md).

        Panels (e.g. the core contributor's System Info page) live in a
        separate catalog from ConfigRegistry specs; the sidebar is the
        union. Links reuse the spec-link classes and htmx attributes —
        structured pages return bare fragments for ``HX-Target`` fetches
        (doc 32), so swapping into ``#main-content`` behaves identically.
        With no panels this renders nothing (output identical to before).
        """
        if not self.panel_links:
            return []
        by_category: dict[str, list[Any]] = {}
        for link in self.panel_links:
            by_category.setdefault(str(getattr(link, "category", "Tools")), []).append(
                link
            )
        groups: list[Any] = []
        for category_label in sorted(by_category):
            header = el(
                "div",
                self._render_icon("folder"),
                el("span", category_label, class_="font-medium"),
                class_=(
                    "flex items-center gap-2 px-3 py-2 text-sm "
                    "text-muted-foreground dark:text-muted-foreground"
                ),
            )
            links = [
                el(
                    "a",
                    el("span", link.title, class_="truncate"),
                    href=link.url,
                    hx_get=link.url,
                    hx_target="#main-content",
                    hx_swap="innerHTML",
                    hx_push_url="true",
                    data_admin_navigation=True,
                    data_settings_nav=True,
                    class_=(
                        "block px-3 py-2 pl-9 text-sm rounded-lg transition-colors "
                        "focus-visible:outline-none focus-visible:ring-2 "
                        "focus-visible:ring-ring text-muted-foreground hover:bg-muted "
                        "dark:text-muted-foreground dark:hover:bg-card"
                    ),
                )
                for link in by_category[category_label]
            ]
            groups.append(
                el(
                    "div",
                    header,
                    el("div", *links, class_="space-y-1"),
                    class_="mb-4",
                    data_testid="settings-panel-links",
                )
            )
        return groups

    def _render_main(self) -> Any:
        """Render the main content area."""
        if self.content:
            return el(
                "div",
                el("div", self.content, class_="p-6"),
                class_="flex-1 min-w-0",
            )

        # Empty state
        return Card(
            children=[
                el(
                    "div",
                    el("div", "⚙️", class_="text-5xl mb-4"),
                    el(
                        "h3",
                        "Select a Configuration",
                        class_="text-lg font-semibold text-foreground",
                    ),
                    el(
                        "p",
                        "Choose a configuration from the sidebar to view and edit settings.",
                        class_="text-muted-foreground mt-2 max-w-sm",
                    ),
                    class_="text-center py-16",
                ),
            ],
            class_="flex-1",
        )

    def _render_icon(self, icon_name: str) -> Any:
        """Render an icon by name."""
        try:
            from lexigram.ui import get_icon

            return get_icon(icon_name, class_name="w-5 h-5 opacity-70")
        except (ImportError, ModuleNotFoundError, AttributeError):
            return el("span", "●", class_="text-muted-foreground")
