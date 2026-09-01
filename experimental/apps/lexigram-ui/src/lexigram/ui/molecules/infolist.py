"""Read-only entry display for admin detail pages.

Provides ``InfolistWidget`` — a component that renders labelled
key-value pairs in a grid layout, suitable for ``show`` / detail views.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any

from lexigram.ui import Component, Element
from lexigram.ui.atoms.icons import get_icon
from lexigram.ui.core.url import is_safe_navigation_url


class InfolistEntryType(str, Enum):
    TEXT = "text"
    BOOLEAN = "boolean"
    BADGE = "badge"
    DATE = "date"
    IMAGE = "image"
    MONEY = "money"
    URL = "url"
    EMAIL = "email"


@dataclass(frozen=True, kw_only=True)
class InfolistEntry:
    """A single labelled entry within an ``InfolistWidget``."""

    name: str
    label: str
    value: Any = None
    type: InfolistEntryType = InfolistEntryType.TEXT
    icon: str | None = None
    badge_type: str = "default"
    image_url: str | None = None
    currency: str = "USD"
    url: str | None = None
    section: str | None = None


class InfolistWidget(Component):
    """Render a read-only list of labelled entries suitable for detail pages.

    Entries are arranged in a configurable-column grid.  Supports
    grouping by section headings.
    """

    def __init__(
        self,
        entries: list[InfolistEntry],
        columns: int = 2,
        **props: Any,
    ) -> None:
        super().__init__(entries=entries, columns=columns, **props)
        self.entries = entries
        self.columns = max(1, min(columns, 4))

    def render(self) -> Element:
        if not self.entries:
            return Element(
                "div",
                Element(
                    "p",
                    "No information available.",
                    class_="text-sm text-muted-foreground italic",
                ),
                class_="p-6 text-center",
            )

        sections = self._group_by_section()

        parts: list[Element] = []
        for section_title, section_entries in sections:
            if section_title:
                parts.append(
                    Element(
                        "h3",
                        section_title,
                        class_=(
                            "text-sm font-semibold text-foreground "
                            "border-b border-border pb-2 mb-4"
                        ),
                    )
                )

            grid = self._render_entries_grid(section_entries)
            parts.append(grid)

        grid_class = (
            "grid gap-4 "
            f"{'grid-cols-1' if self.columns == 1 else ''}"
            f"{'grid-cols-1 sm:grid-cols-2' if self.columns == 2 else ''}"
            f"{'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3' if self.columns == 3 else ''}"
            f"{'grid-cols-1 sm:grid-cols-2 lg:grid-cols-4' if self.columns == 4 else ''}"
        )

        return Element(
            "div",
            *parts,
            class_=grid_class,
        )

    def _group_by_section(
        self,
    ) -> list[tuple[str | None, list[InfolistEntry]]]:
        groups: dict[str | None, list[InfolistEntry]] = {}
        for entry in self.entries:
            key = entry.section
            if key not in groups:
                groups[key] = []
            groups[key].append(entry)

        ordered: list[tuple[str | None, list[InfolistEntry]]] = []
        for entry in self.entries:
            key = entry.section
            if key in groups:
                ordered.append((key, groups.pop(key)))

        ordered.extend(groups.items())
        return ordered

    def _render_entries_grid(self, entries: list[InfolistEntry]) -> Element:
        cards: list[Element] = []
        for entry in entries:
            cards.append(self._render_entry_card(entry))
        return Element("div", *cards)

    def _render_entry_card(self, entry: InfolistEntry) -> Element:
        rendered_value = self._render_value(entry)

        # Resolve through the icon registry rather than embedding the value
        # as raw markup. `icon` reaches this component from resource schemas
        # and record data, so `raw(entry.icon)` made any caller that passed
        # a stored value an injection point -- it renders whatever HTML the
        # string contains. get_icon looks the name up in a fixed set and
        # only emits trusted SVG, so an unknown or hostile value renders
        # nothing instead of executing.
        icon_el = (
            Element(
                "span",
                get_icon(entry.icon, size="w-4 h-4"),
                class_="w-4 h-4 mr-1.5 inline-block",
            )
            if entry.icon
            else ""
        )

        return Element(
            "div",
            Element(
                "dt",
                icon_el,
                entry.label,
                class_=(
                    "text-xs font-medium text-muted-foreground dark:text-muted-foreground "
                    "uppercase tracking-wide mb-1"
                ),
            ),
            Element(
                "dd",
                rendered_value,
                class_="text-sm text-foreground",
            ),
            class_=("p-3 rounded-lg border border-border bg-background"),
        )

    def _render_value(self, entry: InfolistEntry) -> Element | str:
        if entry.value is None:
            return Element("span", "\u2014", class_="text-muted")

        if entry.type == InfolistEntryType.BOOLEAN:
            return self._render_boolean(entry.value)
        if entry.type == InfolistEntryType.BADGE:
            return self._render_badge(entry.value, entry.badge_type)
        if entry.type == InfolistEntryType.DATE:
            return self._render_date(entry.value)
        if entry.type == InfolistEntryType.IMAGE:
            return self._render_image(entry.value, entry.image_url)
        if entry.type == InfolistEntryType.MONEY:
            return self._render_money(entry.value, entry.currency)
        if entry.type == InfolistEntryType.URL:
            return self._render_url(str(entry.value), entry.url)
        if entry.type == InfolistEntryType.EMAIL:
            return self._render_email(str(entry.value))
        return self._render_text(str(entry.value))

    def _render_text(self, text: str) -> Element:
        return Element("span", text)

    def _render_boolean(self, value: Any) -> Element:
        is_true = bool(value)
        if is_true:
            return Element(
                "span",
                "\u2713 Yes",
                class_="text-success font-medium",
            )
        return Element(
            "span",
            "\u2717 No",
            class_="text-destructive font-medium",
        )

    def _render_badge(self, value: Any, badge_type: str) -> Element:
        color_map = {
            "success": "bg-success/10 text-success",
            "warning": "bg-warning/10 text-warning",
            "danger": "bg-destructive/10 text-destructive",
            "info": "bg-info/10 text-info",
            "default": "bg-muted text-foreground dark:bg-muted dark:text-foreground",
        }
        bg = color_map.get(badge_type, color_map["default"])
        return Element(
            "span",
            str(value),
            class_=f"inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium {bg}",
        )

    def _render_date(self, value: Any) -> Element:
        if isinstance(value, datetime):
            formatted = value.strftime("%Y-%m-%d %H:%M")
        elif isinstance(value, date):
            formatted = value.isoformat()
        else:
            formatted = str(value)
        return Element("span", formatted)

    def _render_image(self, value: Any, image_url: str | None = None) -> Element:
        src = image_url or str(value)
        if not is_safe_navigation_url(src):
            return Element("span", str(value))
        return Element(
            "img",
            src=src,
            alt=str(value),
            class_="max-h-20 rounded",
        )

    def _render_money(self, value: Any, currency: str = "USD") -> Element:
        try:
            amount = float(value)
            symbols = {"USD": "$", "EUR": "\u20ac", "GBP": "\u00a3"}
            symbol = symbols.get(currency, currency + " ")
            formatted = f"{symbol}{amount:,.2f}"
        except (ValueError, TypeError):
            formatted = str(value)
        return Element("span", formatted)

    def _render_url(self, value: str, url: str | None = None) -> Element:
        href = url or value
        if not is_safe_navigation_url(href):
            return Element("span", value)
        return Element(
            "a",
            value,
            href=href,
            target="_blank",
            rel="noopener noreferrer",
            class_="text-primary-600 hover:text-primary-800 underline",
        )

    def _render_email(self, value: str) -> Element:
        return Element(
            "a",
            value,
            href=f"mailto:{value}",
            class_="text-primary-600 hover:text-primary-800 underline",
        )
