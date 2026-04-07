"""Date hierarchy filter — Django Admin-style year/month/day drill-down.

Renders a breadcrumb-style date navigation bar that lets users drill into
a dataset by year, then month, then day.  Each level is a clickable link
that adds the appropriate ``year=``, ``month=``, ``day=`` query parameters.

Django Admin is the only framework with built-in date hierarchy; this
brings that feature to lexigram-admin.

Usage::

    bar = DateHierarchyFilter(
        field_name="created_at",
        year=2026,
        month=3,
        day=None,
        base_url="/admin/users",
        resource_prefix="/admin/users",
    )
    html = bar.render()
"""

from __future__ import annotations

import calendar
from typing import Any

from lexigram.ui import Component, el

# Month name abbreviations (locale-neutral; translatable via i18n layer)
_MONTH_NAMES = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
]


class DateHierarchyFilter(Component):
    """Year/month/day drill-down filter navigation.

    At each level the component renders quick-link buttons:

    - **No selection**: Shows clickable year links (last 5 years + current).
    - **Year selected**: Shows clickable month buttons (Jan–Dec).
    - **Year + month selected**: Shows clickable day buttons for that month.
    - **Year + month + day**: Shows breadcrumb with "×" clear button.

    HTMX is used to reload the table without a full page refresh.

    Args:
        field_name: Model field being filtered (used in URL params as
            ``{field_name}__year``, etc.).
        year: Currently selected year, or ``None``.
        month: Currently selected month (1–12), or ``None``.
        day: Currently selected day (1–31), or ``None``.
        base_url: Base URL for building drill-down links.
        resource_prefix: HTMX target resource prefix.
        available_years: Explicit list of years to show.  If ``None``,
            defaults to the 5 years before and including the current year
            from the *year* argument or ``2026``.
    """

    def __init__(
        self,
        field_name: str = "created_at",
        year: int | None = None,
        month: int | None = None,
        day: int | None = None,
        base_url: str = "",
        resource_prefix: str = "",
        available_years: list[int] | None = None,
        **props: Any,
    ) -> None:
        super().__init__(**props)
        self.field_name = field_name
        self.year = year
        self.month = month
        self.day = day
        self.base_url = base_url.rstrip("/")
        self.resource_prefix = (resource_prefix or base_url).rstrip("/")
        _anchor = year or 2026
        self.available_years = available_years or list(range(_anchor - 4, _anchor + 1))

    # ------------------------------------------------------------------
    # Public render
    # ------------------------------------------------------------------

    def render(self) -> Any:
        items = self._build_items()
        if not items:
            return ""

        return el(
            "nav",
            el(
                "ol",
                *items,
                class_="flex flex-wrap items-center gap-1",
            ),
            class_=(
                "flex items-center gap-2 text-sm "
                "bg-white dark:bg-gray-800 "
                "border border-gray-200 dark:border-gray-700 "
                "rounded-lg px-3 py-2 mb-3"
            ),
            **{"aria-label": "Date hierarchy"},
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _htmx_link(self, label: str, url: str, extra_cls: str = "") -> Any:
        """Render a single HTMX drill-down link."""
        return el(
            "a",
            label,
            href=url,
            class_=(
                f"px-2 py-0.5 rounded text-blue-600 dark:text-blue-400 "
                f"hover:bg-blue-50 dark:hover:bg-gray-700 "
                f"transition-colors cursor-pointer {extra_cls}"
            ),
            **{
                "hx-get": url,
                "hx-target": "#main-content",
                "hx-push-url": "true",
            },
        )

    def _clear_link(self) -> Any:
        """Render an 'x clear' link that strips all date params."""
        url = self.base_url or "?"
        return self._htmx_link(
            "\u00d7", url, extra_cls="text-gray-400 hover:text-red-500"
        )

    def _build_url(
        self,
        *,
        year: int | None = None,
        month: int | None = None,
        day: int | None = None,
    ) -> str:
        """Build a URL with the given date query params."""
        params: list[str] = []
        if year is not None:
            params.append(f"{self.field_name}__year={year}")
        if month is not None:
            params.append(f"{self.field_name}__month={month}")
        if day is not None:
            params.append(f"{self.field_name}__day={day}")
        base = self.base_url or "."
        return f"{base}?{'&'.join(params)}" if params else base

    def _build_items(self) -> list[Any]:
        """Build the ordered list items based on current drill-down level."""
        items: list[Any] = []

        if self.year is None:
            # Level 0 — show year buttons
            for y in sorted(self.available_years, reverse=True):
                url = self._build_url(year=y)
                items.append(el("li", self._htmx_link(str(y), url)))
            return items

        # Level 1+ — always show year breadcrumb
        items.append(
            el(
                "li",
                el(
                    "span",
                    self._htmx_link(str(self.year), self._build_url(year=self.year)),
                    el("span", "/", class_="text-gray-400 mx-1"),
                    class_="flex items-center",
                ),
            )
        )

        if self.month is None:
            # Level 1 — show month buttons
            for m_idx, m_name in enumerate(_MONTH_NAMES, start=1):
                url = self._build_url(year=self.year, month=m_idx)
                items.append(el("li", self._htmx_link(m_name, url)))
            items.append(el("li", self._clear_link()))
            return items

        # Level 2 — year + month breadcrumb
        items.append(
            el(
                "li",
                el(
                    "span",
                    self._htmx_link(
                        _MONTH_NAMES[self.month - 1],
                        self._build_url(year=self.year, month=self.month),
                    ),
                    el("span", "/", class_="text-gray-400 mx-1"),
                    class_="flex items-center",
                ),
            )
        )

        if self.day is None:
            # Level 2 — show day buttons
            _, days_in_month = calendar.monthrange(self.year, self.month)
            for d in range(1, days_in_month + 1):
                url = self._build_url(year=self.year, month=self.month, day=d)
                items.append(el("li", self._htmx_link(str(d), url)))
            items.append(el("li", self._clear_link()))
            return items

        # Level 3 — full breadcrumb + clear
        items.append(
            el(
                "li",
                el(
                    "span",
                    str(self.day),
                    class_="font-medium text-gray-700 dark:text-gray-200",
                ),
            )
        )
        items.append(el("li", self._clear_link()))
        return items
