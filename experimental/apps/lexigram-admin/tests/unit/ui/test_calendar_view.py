"""CalendarView month navigation and event links.

The calendar is no longer a simplified static grid: it must expose prev/next/
today month controls wired through HTMX data refreshes (``filter_month``),
link events to their record detail pages, and fall back to the tabular view
when no date field can be resolved.
"""

from __future__ import annotations

from lexigram.admin.resources.config import TableConfiguration
from lexigram.admin.ui.organisms.table.views.calendar import CalendarView
from lexigram.ui import TableState, render_to_string
from lexigram.ui.columns.types import DateColumn, TextColumn


class TestCalendarView:
    def _view(
        self,
        *,
        data: list[dict],
        columns: list | None = None,
        filters: dict | None = None,
    ) -> CalendarView:
        config = TableConfiguration(
            columns=columns or [DateColumn("start_date"), TextColumn("name")],
            resource_prefix="/admin/events",
            resource_name="events",
        )
        state = TableState(view="calendar", filters=filters or {})
        return CalendarView(
            data,
            config,
            state,
            total=len(data),
            user=None,
            resource_name="events",
        )

    def test_groups_events_into_month_grid(self) -> None:
        view = self._view(
            data=[
                {"id": "1", "name": "Launch", "start_date": "2026-08-10"},
                {"id": "2", "name": "Retro", "start_date": "2026-08-15"},
            ]
        )
        html = render_to_string(view.render())
        assert "August 2026" in html
        assert "Launch" in html
        assert "Retro" in html
        assert 'href="/admin/events/1"' in html
        assert 'href="/admin/events/2"' in html

    def test_month_navigation_uses_filter_param(self) -> None:
        view = self._view(
            data=[{"id": "1", "name": "Launch", "start_date": "2026-08-10"}]
        )
        html = render_to_string(view.render())
        # Prev/Next/Today links carry the month state as a filter param.
        assert "filter_month=2026-07" in html
        assert "filter_month=2026-09" in html
        assert "Today" in html
        assert 'hx-get="/admin/events/?data_view=calendar' in html

    def test_respects_requested_month_from_state(self) -> None:
        data = [{"id": "1", "name": "Launch", "start_date": "2026-01-10"}]
        view = self._view(data=data, filters={"month": "2026-12"})
        html = render_to_string(view.render())
        assert "December 2026" in html

    def test_hidden_input_round_trips_month(self) -> None:
        view = self._view(
            data=[{"id": "1", "name": "Launch", "start_date": "2026-08-10"}]
        )
        html = render_to_string(view.render())
        assert 'name="filter_month"' in html
        assert 'value="2026-08"' in html

    def test_falls_back_to_tabular_without_date_field(self) -> None:
        view = self._view(
            data=[{"id": "1", "name": "Launch", "note": "x"}],
            columns=[TextColumn("name")],
        )
        html = render_to_string(view.render())
        # Rendered as a table grid rather than a calendar grid.
        assert "<table" in html
        assert "Launch" in html
        assert 'role="grid"' not in html
