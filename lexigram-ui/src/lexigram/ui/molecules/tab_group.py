"""Tab group component for organising resource pages.

Renders an Alpine.js-managed tab bar with content panels.
Tabs use CSS visibility toggling (no HTMX requests).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from lexigram.ui import Component, Element, raw


@dataclass(frozen=True, kw_only=True)
class Tab:
    """A single tab within a ``TabGroup``."""

    name: str
    label: str
    schema_fields: list[Any] = field(default_factory=list)
    icon: str | None = None
    badge: str | int | None = None


class TabGroup(Component):
    """Render a set of tabs with Alpine.js-driven switching.

    Each tab can hold a list of schema fields (for forms) or
    arbitrary content (for detail views).
    """

    def __init__(
        self,
        tabs: list[Tab],
        default_tab: str | None = None,
        **props: Any,
    ) -> None:
        super().__init__(tabs=tabs, default_tab=default_tab, **props)
        self.tabs = tabs
        default = default_tab or (tabs[0].name if tabs else "")
        self.default_tab = default

    def render(self) -> Element:
        if not self.tabs:
            return Element("div")

        x_data = f"{{ activeTab: '{self.default_tab}' }}"

        tab_bar = self._render_tab_bar()
        panels = self._render_panels()

        return Element(
            "div",
            tab_bar,
            panels,
            **{"x-data": x_data},
            class_="w-full",
        )

    def _render_tab_bar(self) -> Element:
        buttons: list[Element] = []
        for tab in self.tabs:
            classes = (
                "inline-flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium "
                "border-b-2 transition-all duration-200 focus:outline-none "
                "data-[active=true]:border-primary-600 data-[active=true]:text-primary-600 "
                "border-transparent text-muted-foreground dark:text-muted-foreground "
                "hover:text-foreground dark:hover:text-foreground "
                "hover:border-border dark:hover:border-border"
            )

            btn_content: list[Element | str] = []

            if tab.icon:
                btn_content.append(
                    Element(
                        "span",
                        raw(tab.icon),
                        class_="w-4 h-4",
                    )
                )

            btn_content.append(Element("span", tab.label))

            if tab.badge is not None:
                btn_content.append(
                    Element(
                        "span",
                        str(tab.badge),
                        class_=(
                            "ml-1.5 inline-flex items-center px-2 py-0.5 "
                            "rounded-full text-xs font-medium "
                            "bg-primary-100 text-primary-800 "
                            "dark:bg-primary-900 dark:text-primary-200"
                        ),
                    )
                )

            button = Element(
                "button",
                *btn_content,
                type="button",
                role="tab",
                **{
                    "@click": f"activeTab = '{tab.name}'",
                    ":data-active": f"activeTab === '{tab.name}'",
                    ":aria-selected": f"activeTab === '{tab.name}'",
                },
                class_=classes,
            )
            buttons.append(button)

        return Element(
            "div",
            *buttons,
            role="tablist",
            class_="flex border-b border-border overflow-x-auto",
        )

    def _render_panels(self) -> Element:
        panels: list[Element] = []
        for tab in self.tabs:
            content = self._render_tab_content(tab)
            panel = Element(
                "div",
                content,
                role="tabpanel",
                **{
                    "x-show": f"activeTab === '{tab.name}'",
                    "x-cloak": "",
                },
                class_="pt-4",
            )
            panels.append(panel)
        return Element("div", *panels, class_="w-full")

    def _render_tab_content(self, tab: Tab) -> Element:
        """Render the content body for a tab.

        If the tab has ``schema_fields``, render them as form
        controls. Otherwise show a placeholder.
        """
        if not tab.schema_fields:
            return Element("div")

        rows: list[Element] = []
        for schema_field in tab.schema_fields:
            rendered = schema_field.render_form(None)
            if isinstance(rendered, Element):
                rows.append(rendered)
            else:
                rows.append(Element("div", str(rendered)))

        return Element("div", *rows, class_="space-y-4")
