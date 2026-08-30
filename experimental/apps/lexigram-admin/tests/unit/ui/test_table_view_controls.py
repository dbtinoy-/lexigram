"""Resource table chrome is wired per ``data_view``.

Tabular / stacked / grid / calendar are the highest-order view structure.
Search, filters, header (top) actions, row actions and bulk selection must
work in every view; presentation-only switchers (density, column visibility,
group-by, toolbar sort) follow the capability map.
"""

from __future__ import annotations

from lexigram.admin.resources.base import Resource
from lexigram.admin.resources.config import ResourceConfig
from lexigram.admin.ui.organisms.data_table import DataTable
from lexigram.admin.ui.organisms.data_table.view_controls import (
    DATA_VIEWS,
    controls_for,
)
from lexigram.ui import TableState, render_to_string
from lexigram.ui.columns.types import DateColumn, TextColumn

_VIEWS = DATA_VIEWS
_SLIDE_OVER = 'hx-target="#slide-over-container"'


def _columns() -> list:
    return [
        TextColumn("name").sortable().searchable(),
        DateColumn("start_date"),
        TextColumn("status"),
    ]


def _data() -> list[dict]:
    return [
        {
            "id": "1",
            "name": "Ada",
            "start_date": "2026-08-10",
            "status": "active",
        },
        {
            "id": "2",
            "name": "Alan",
            "start_date": "2026-08-15",
            "status": "archived",
        },
    ]


def _dt(view: str, **props: object) -> DataTable:
    return DataTable(
        columns=_columns(),
        data=_data(),
        resource_prefix="/admin/people",
        resource_name="people",
        filter_options={
            "status": {"type": "select", "options": ["active", "archived"]},
        },
        state=TableState(view=view, search="ada"),  # type: ignore[arg-type]
        **props,
    )


def _html(view: str, **props: object) -> str:
    return render_to_string(_dt(view, **props))


class TestViewCapabilityMap:
    def test_known_views(self) -> None:
        assert DATA_VIEWS == ("tabular", "stacked", "grid", "calendar")

    def test_unknown_view_falls_back_to_tabular(self) -> None:
        caps = controls_for("kanban")
        assert caps.column_sort is True
        assert caps.density is True

    def test_shared_chrome_on_every_view(self) -> None:
        for view in _VIEWS:
            caps = controls_for(view)
            assert caps.search is True
            assert caps.filters is True
            assert caps.header_actions is True
            assert caps.row_actions is True
            assert caps.bulk_actions is True
            assert caps.layout is True

    def test_presentation_controls_per_view(self) -> None:
        assert controls_for("tabular").column_sort is True
        assert controls_for("tabular").toolbar_sort is False
        assert controls_for("tabular").density is True
        assert controls_for("tabular").column_visibility is True
        assert controls_for("tabular").group_by is True

        assert controls_for("stacked").toolbar_sort is True
        assert controls_for("stacked").density is False
        assert controls_for("stacked").column_visibility is True
        assert controls_for("stacked").group_by is False

        assert controls_for("grid").toolbar_sort is True
        assert controls_for("grid").density is False
        assert controls_for("grid").column_visibility is False

        assert controls_for("calendar").toolbar_sort is False
        assert controls_for("calendar").density is False
        assert controls_for("calendar").column_visibility is False
        assert controls_for("calendar").group_by is False


class TestAllViewsShareWorkingChrome:
    def test_view_switcher_lists_all_four_strategies(self) -> None:
        for view in _VIEWS:
            html = _html(view)
            assert "view-switcher" in html
            assert "Tabular" in html
            assert "Stacked" in html
            assert "Grid" in html
            assert "Calendar" in html

    def test_view_switcher_preserves_search_when_changing_view(self) -> None:
        html = _html("tabular")
        assert "search=ada" in html
        assert "data_view=stacked" in html
        assert "data_view=grid" in html
        assert "data_view=calendar" in html

    def test_search_present_on_every_view(self) -> None:
        for view in _VIEWS:
            html = _html(view)
            assert 'name="search"' in html
            assert 'id="table-search"' in html

    def test_filters_present_on_every_view(self) -> None:
        for view in _VIEWS:
            html = _html(view)
            assert 'option value="active"' in html
            assert 'option value="archived"' in html

    def test_header_create_opens_slide_over_on_every_view(self) -> None:
        for view in _VIEWS:
            html = _html(view)
            assert "Create New" in html
            assert "/admin/people/create" in html
            assert _SLIDE_OVER in html

    def test_bulk_actions_wired_on_every_view(self) -> None:
        for view in _VIEWS:
            html = _html(view)
            assert "Delete Selected" in html
            assert 'name="ids"' in html
            assert 'x-model="selectedIds"' in html


class TestViewSpecificPresentation:
    def test_tabular_shows_column_sort_and_density(self) -> None:
        html = _html("tabular")
        assert "aria-sort" in html
        assert "density-switcher" in html
        assert "column-visibility-switcher" in html
        assert "group-by-switcher" in html
        assert "sort-switcher" not in html

    def test_stacked_shows_toolbar_sort_not_density(self) -> None:
        html = _html("stacked")
        assert "sort-switcher" in html
        assert "sort_by=name" in html
        assert "density-switcher" not in html
        assert "group-by-switcher" not in html
        assert "column-visibility-switcher" in html
        assert "aria-sort" not in html

    def test_grid_shows_toolbar_sort_and_hides_tabular_chrome(self) -> None:
        html = _html("grid")
        assert "sort-switcher" in html
        assert "density-switcher" not in html
        assert "column-visibility-switcher" not in html
        assert "group-by-switcher" not in html
        assert "View details" in html

    def test_calendar_hides_tabular_chrome_and_keeps_forms(self) -> None:
        html = _html("calendar")
        assert "sort-switcher" not in html
        assert "density-switcher" not in html
        assert "column-visibility-switcher" not in html
        assert "group-by-switcher" not in html
        assert "August 2026" in html
        assert 'href="/admin/people/1"' in html
        assert _SLIDE_OVER in html


class TestRowActionsAndFormsPerView:
    def test_edit_form_wired_from_tabular_row(self) -> None:
        html = _html("tabular")
        assert "/admin/people/1/edit" in html
        assert _SLIDE_OVER in html

    def test_edit_form_wired_from_stacked_card(self) -> None:
        html = _html("stacked")
        assert "/admin/people/1/edit" in html
        assert _SLIDE_OVER in html

    def test_edit_form_wired_from_grid_card(self) -> None:
        html = _html("grid")
        assert "/admin/people/1/edit" in html
        assert _SLIDE_OVER in html

    def test_edit_form_wired_from_calendar_event(self) -> None:
        html = _html("calendar")
        assert "/admin/people/1/edit" in html
        assert _SLIDE_OVER in html


class TestResourceDefaultView:
    def test_fluent_config_accepts_stacked_and_calendar(self) -> None:
        class EventResource(Resource):
            config = ResourceConfig.builder().view("calendar")

        assert EventResource.get_table_config().default_view == "calendar"

        class CardResource(Resource):
            config = ResourceConfig.builder().view("stacked")

        assert CardResource.get_table_config().default_view == "stacked"

    def test_class_data_view_attribute_is_honored(self) -> None:
        class GridResource(Resource):
            data_view = "grid"

        assert GridResource.get_table_config().default_view == "grid"
