"""GridView card details link and record helpers.

Grid cards must link to the record detail page (``/resource/{id}``) rather
than hard-coding the edit route, and record-id resolution must go through the
shared ``extract_row_id`` helper.
"""

from __future__ import annotations

from lexigram.admin.actions.standard import DeleteBulkAction, EditAction
from lexigram.admin.resources.config import TableConfiguration
from lexigram.admin.ui.organisms.table.views.grid import GridView
from lexigram.admin.ui.organisms.table.views.tabular_rows import extract_row_id
from lexigram.ui import TableState, render_to_string
from lexigram.ui.columns.types import TextColumn


class TestGridView:
    def _view(self, data: list[dict]) -> GridView:
        config = TableConfiguration(
            columns=[TextColumn("name")],
            resource_prefix="/admin/events",
            resource_name="events",
        )
        return GridView(
            data,
            config,
            TableState(view="grid"),
            total=len(data),
            user=None,
            resource_name="events",
        )

    def test_details_link_points_to_record(self) -> None:
        view = self._view([{"id": "42", "name": "Launch"}])
        html = render_to_string(view.render())
        assert 'href="/admin/events/42"' in html
        assert "/admin/events/42/edit" not in html
        assert "View details" in html

    def test_card_shows_title_and_subtitle(self) -> None:
        view = self._view(
            [{"id": "1", "name": "Fido", "breed": "Labrador", "email": "x@y.z"}]
        )
        html = render_to_string(view.render())
        assert "Fido" in html
        assert "Labrador" in html

    def test_extract_row_id_shared_helper_handles_dict(self) -> None:
        assert extract_row_id({"id": 7}) == "7"
        assert extract_row_id({"user_id": 8}) == "8"
        assert extract_row_id({"id": None}) == ""

    def test_idless_cards_do_not_render_selection_or_detail_controls(self) -> None:
        config = TableConfiguration(
            columns=[TextColumn("name")],
            resource_prefix="/admin/events",
            resource_name="events",
            actions=[EditAction()],
            bulk_actions=[DeleteBulkAction()],
        )
        view = GridView(
            [{"name": "Unaddressable"}],
            config,
            TableState(view="grid"),
            resource_name="events",
        )
        html = render_to_string(view.render())
        assert 'name="ids"' not in html
        assert "View details" not in html
        assert "/admin/events/row-0" not in html
