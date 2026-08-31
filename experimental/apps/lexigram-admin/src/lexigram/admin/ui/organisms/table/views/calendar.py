"""Calendar view for the data table.

Groups records by their date column and renders them in a month grid with
prev/next month navigation (HTMX full data refreshes), event drill-down
links, and a "today" shortcut.  Falls back to :class:`TabularView` when no
date field can be resolved from the columns or the data.
"""

from __future__ import annotations

import calendar
from collections import Counter, defaultdict
import contextlib
import datetime
import re
from typing import Any

from lexigram.admin.ui.organisms.data_table.actions import render_action_button
from lexigram.admin.ui.organisms.table.views.tabular import (
    AbstractDataView,
    TabularView,
)
from lexigram.admin.ui.organisms.table.views.tabular_rows import (
    extract_row_id,
    get_attr,
)
from lexigram.ui import Checkbox, DateColumn, HTMXAttrs, el

_MONTH_RE = re.compile(r"^(\d{4})-(\d{2})$")

#: Query-key used to persist the displayed month through the table state.
#: It round-trips as a generic state filter (``filter_month=YYYY-MM``).
MONTH_FILTER_KEY = "month"

_DATE_FIELD_CANDIDATES = (
    "created_at",
    "date",
    "timestamp",
    "birth_date",
    "start_date",
    "updated_at",
)


def _parse_month(value: Any) -> tuple[int, int] | None:
    """Parse a ``YYYY-MM`` string into a ``(year, month)`` tuple."""
    if not isinstance(value, str):
        return None
    match = _MONTH_RE.fullmatch(value)
    if not match:
        return None
    year, month = int(match.group(1)), int(match.group(2))
    if not 1 <= month <= 12:
        return None
    return year, month


def _shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    """Return the month *delta* months away from ``(year, month)``."""
    total = year * 12 + (month - 1) + delta
    return total // 12, (total % 12) + 1


def _month_filter_value(year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}"


class CalendarView(AbstractDataView):
    """Render data as a calendar month grid."""

    def render(self) -> Any:
        # 1. Detect Date Field
        date_field = self._detect_date_field()

        if not date_field:
            # Fallback to tabular if no date field
            return TabularView(
                self.data,
                self.config,
                self.state,
                self.total,
                self.summary,
                self.user,
                self.resource_name,
                self.next_cursor,
            ).render()

        # 2. Group Data by Date
        events_by_date, relevant_dates = self._group_by_date(date_field)

        # 3. Determine Month to Show: explicit state month > most common
        #    date in the data > current month.
        requested = self.state.filters.get(MONTH_FILTER_KEY)
        parsed = _parse_month(requested)
        if parsed is not None:
            curr_year, curr_month = parsed
        elif relevant_dates:
            most_common = Counter(
                [(d.year, d.month) for d in relevant_dates],
            ).most_common(1)[0][0]
            curr_year, curr_month = most_common
        else:
            now = datetime.datetime.now()
            curr_year, curr_month = now.year, now.month

        month_grid = self._render_month_grid(
            events_by_date,
            curr_year,
            curr_month,
        )

        # Select-all bar for bulk operations
        select_all_bar = self.render_select_all_bar()
        if select_all_bar:
            return el("div", select_all_bar, month_grid)

        return month_grid

    def _detect_date_field(self) -> str | None:
        """Resolve the column that carries the event date."""
        for col in self.config.columns:
            if isinstance(col, DateColumn):
                return col.name

        if not self.data:
            return None

        first_item = self.data[0]
        for key in _DATE_FIELD_CANDIDATES:
            if isinstance(first_item, dict):
                if key in first_item:
                    return key
            elif hasattr(first_item, key):
                return key
        return None

    def _group_by_date(
        self,
        date_field: str,
    ) -> tuple[defaultdict[datetime.date, list[Any]], list[datetime.date]]:
        """Bucket records by normalized date."""
        events_by_date: defaultdict[datetime.date, list[Any]] = defaultdict(list)
        relevant_dates: list[datetime.date] = []
        for item in self.data:
            val = get_attr(item, date_field)
            if not val:
                continue

            d = self._normalize_date(val)
            if d is None:
                continue
            events_by_date[d].append(item)
            relevant_dates.append(d)
        return events_by_date, relevant_dates

    @staticmethod
    def _normalize_date(val: Any) -> datetime.date | None:
        """Normalize a date-ish value to a ``datetime.date``."""
        if isinstance(val, datetime.datetime):
            return val.date()
        if isinstance(val, datetime.date):
            return val
        if isinstance(val, str):
            with contextlib.suppress(ValueError, TypeError):
                parsed = datetime.datetime.fromisoformat(
                    val.replace("Z", "+00:00"),
                )
                return parsed.date()
        return None

    def _render_month_grid(
        self,
        events_by_date: defaultdict[datetime.date, list[Any]],
        curr_year: int,
        curr_month: int,
    ) -> Any:
        cal = calendar.Calendar(firstweekday=6)  # Sunday start
        month_days = cal.monthdayscalendar(curr_year, curr_month)
        month_name = calendar.month_name[curr_month]
        month_value = _month_filter_value(curr_year, curr_month)

        today = datetime.date.today()
        prefix = self.config.resource_prefix or ""

        days_header = [
            el(
                "div",
                day,
                role="columnheader",
                class_="text-center font-medium text-muted-foreground py-2",
            )
            for day in ("Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat")
        ]

        weeks = []
        for week in month_days:
            days = []
            for day in week:
                if day == 0:
                    days.append(
                        el(
                            "div",
                            "",
                            role="gridcell",
                            class_="h-32 bg-muted/50 border border-border",
                        ),
                    )
                    continue

                curr_date = datetime.date(curr_year, curr_month, day)
                is_today = curr_date == today
                days.append(
                    self._render_day_cell(
                        curr_date,
                        day,
                        events_by_date.get(curr_date, []),
                        prefix,
                        month_value,
                        is_today=is_today,
                    ),
                )
            weeks.append(el("div", *days, role="row", class_="grid grid-cols-7"))

        return el(
            "div",
            self._render_nav_bar(curr_year, curr_month, month_value),
            el(
                "div",
                *days_header,
                role="row",
                class_="grid grid-cols-7 border-b border-border mb-2",
            ),
            el(
                "div",
                *weeks,
                role="grid",
                aria_label=f"{month_name} {curr_year} calendar",
            ),
            # Keep month state flowing into the data zone's hidden inputs so
            # a subsequent filter/search keeps the selected month.
            el(
                "input",
                type="hidden",
                name=f"filter_{MONTH_FILTER_KEY}",
                value=month_value,
                data_state="true",
            ),
            class_="bg-card p-4 rounded-lg shadow-sm border border-border",
        )

    def _render_nav_bar(
        self,
        curr_year: int,
        curr_month: int,
        month_value: str,
    ) -> Any:
        """Render prev/next/today month navigation."""
        month_name = calendar.month_name[curr_month]
        prefix = self.config.resource_prefix or ""

        def _nav_attrs(target_month: str) -> dict[str, str]:
            if prefix:
                return HTMXAttrs.for_data_refresh(
                    self.state,
                    prefix,
                    **{f"filter_{MONTH_FILTER_KEY}": target_month},
                    push_url=True,
                )
            return {}

        def _nav_href(target_month: str) -> str:
            if prefix:
                from urllib.parse import urlencode

                params = self.state.to_query_params()
                params[f"filter_{MONTH_FILTER_KEY}"] = target_month
                url = prefix.rstrip("/") + "/"
                return f"{url}?{urlencode(params, doseq=True)}" if params else url
            return f"?filter_{MONTH_FILTER_KEY}={target_month}"

        def _nav_link(
            label: str,
            target_month: str,
            aria_label: str,
        ) -> Any:
            attrs = _nav_attrs(target_month)
            return el(
                "a",
                label,
                href=_nav_href(target_month),
                **attrs,
                class_=button_cls,
                aria_label=aria_label,
            )

        prev_year, prev_month = _shift_month(curr_year, curr_month, -1)
        next_year, next_month = _shift_month(curr_year, curr_month, 1)
        prev_value = _month_filter_value(prev_year, prev_month)
        next_value = _month_filter_value(next_year, next_month)

        today = datetime.date.today()
        today_value = _month_filter_value(today.year, today.month)

        button_cls = (
            "px-3 py-1.5 text-sm rounded-md border border-border "
            "bg-card hover:bg-muted transition-colors text-foreground "
            "cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
        )

        title = el(
            "h2",
            f"{month_name} {curr_year}",
            role="heading",
            aria_level="2",
            class_="text-lg font-bold text-center",
        )

        today_link = el(
            "a",
            "Today",
            href=_nav_href(today_value),
            **_nav_attrs(today_value),
            class_=button_cls,
            aria_label=f"Jump to {calendar.month_name[today.month]} {today.year}",
        )

        return el(
            "div",
            _nav_link("< Prev", prev_value, "Previous month"),
            title,
            el(
                "div",
                _nav_link("Next >", next_value, "Next month"),
                today_link,
                class_="flex items-center gap-2",
            ),
            class_="grid grid-cols-3 items-center mb-4 gap-2 max-w-3xl",
        )

    def _render_day_cell(
        self,
        curr_date: datetime.date,
        day_number: int,
        day_events: list[Any],
        prefix: str,
        month_value: str,
        *,
        is_today: bool,
    ) -> Any:
        """Render a single calendar day cell."""
        event_els = []
        for event in day_events[:3]:
            event_els.append(self._render_event(event, prefix))

        if len(day_events) > 3:
            more_href = (
                f"{prefix}/?filter_{MONTH_FILTER_KEY}={month_value}"
                if prefix
                else f"?filter_{MONTH_FILTER_KEY}={month_value}"
            )
            event_els.append(
                el(
                    "a",
                    f"+{len(day_events) - 3} more",
                    href=more_href,
                    class_=(
                        "text-xs text-muted-foreground pl-1 hover:text-foreground "
                        "transition-colors"
                    ),
                ),
            )

        if not day_events:
            event_els.append(
                el(
                    "div",
                    "",
                    aria_hidden="true",
                    class_="text-xs text-muted-foreground",
                ),
            )

        cell_cls = (
            "h-32 bg-card border border-border p-2 hover:bg-muted "
            "transition-colors overflow-hidden"
        )
        if is_today:
            cell_cls += " border-primary-500 ring-1 ring-primary-500/50"

        day_cls = "text-right text-sm font-medium mb-1 " + (
            "text-primary-600" if is_today else "text-foreground"
        )

        return el(
            "div",
            el(
                "div",
                str(day_number),
                role="presentation",
                class_=day_cls,
            ),
            *event_els,
            role="gridcell",
            class_=cell_cls,
            aria_label=f"{curr_date.isoformat()}, {len(day_events)} events",
        )

    def _render_event(self, event: Any, prefix: str) -> Any:
        """Render one calendar event chip with bulk select and row actions."""
        title = (
            get_attr(event, "name")
            or get_attr(event, "title")
            or get_attr(event, "label")
            or "Event"
        )
        rid = extract_row_id(event)
        href = f"{prefix}/{rid}" if prefix and rid else "#"

        select_node: Any = ""
        if prefix and self.config.bulk_actions and rid:
            select_node = Checkbox(
                name="ids",
                value=rid,
                x_model="selectedIds",
                class_="flex-shrink-0 mt-0.5",
                aria_label=f"Select {rid}",
            )

        action_nodes: list[Any] = []
        if prefix and rid:
            for action in self.config.actions:
                if not action.is_visible(
                    user=self.user,
                    resource_name=self.resource_name,
                    record=event,
                ):
                    continue
                node = render_action_button(
                    action,
                    record=event,
                    user=self.user,
                    resource_name=self.resource_name,
                    resource_prefix=prefix,
                    form_display_mode=getattr(self.config, "form_display_mode", None),
                )
                if node:
                    action_nodes.append(node)

        actions_row = (
            el(
                "div",
                *action_nodes,
                class_=(
                    "flex flex-wrap items-center gap-1 mt-0.5 "
                    "opacity-0 group-hover:opacity-100 transition-opacity"
                ),
            )
            if action_nodes
            else ""
        )

        return el(
            "div",
            select_node,
            el(
                "div",
                (
                    el(
                        "a",
                        title,
                        href=href,
                        title=str(title),
                        class_="truncate block hover:underline",
                    )
                    if rid
                    else el(
                        "span",
                        title,
                        title=str(title),
                        class_="truncate block",
                    )
                ),
                actions_row,
                class_="min-w-0 flex-1",
            ),
            class_=(
                "group flex items-start gap-1 text-xs bg-primary-100 "
                "text-primary-700 rounded px-1 py-0.5 mb-1 "
                "hover:bg-primary-200 transition-colors"
            ),
        )
