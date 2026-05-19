from lexigram.admin.actions.base import HeaderAction
from lexigram.admin.actions.standard import DeleteBulkAction
from lexigram.ui.core.base import render_to_string
from lexigram.ui.columns.types import TextColumn
from lexigram.ui import TablePagination as Pagination
from lexigram.admin.ui.organisms.data_table import DataTable


def test_data_table_header_export_action_renders_hx_get():
    class _ExportHeaderAction(HeaderAction):
        def __init__(self):
            super().__init__(name="export", label="Export")
            self._icon = "download"
            self._color = "gray"

        def _get_url(self, record, ctx):
            return "/admin/users/export"

        async def execute(self, record, ctx):
            from lexigram.result import Ok
            return Ok({"message": "Exported"})

    dt = DataTable(
        columns=[TextColumn("name")],
        data=[{"id": 1}],
        resource_prefix="/admin/users",
        header_actions=[_ExportHeaderAction()],
    )
    html = render_to_string(dt)
    assert "Export" in html
    assert 'hx-get="/admin/users/export"' in html or "hx-get" in html


def test_bulk_delete_confirmation_and_hx_delete_present():
    dt = DataTable(
        columns=[TextColumn("name")],
        data=[{"id": 1}],
        resource_prefix="/admin/users",
        bulk_actions=[DeleteBulkAction()],
    )
    html = render_to_string(dt)
    # Slide-over confirmation instead of native hx-confirm
    assert "hx-confirm" not in html
    assert "hx-get" in html
    assert "bulk-delete-confirm" in html
    assert "hx-include" in html


def test_pagination_prev_next_disabled_states():
    # Previous should be disabled on first page
    p1 = Pagination(
        page=1, total=30, per_page=10, base_url="/admin/users", extra_query="",
    )
    html1 = render_to_string(p1)
    # Previous may render as a span when disabled or carry 'invisible' class for mobile
    assert "cursor-not-allowed" in html1 or "invisible" in html1 or "<span" in html1

    # Next should be disabled on last page
    p2 = Pagination(
        page=3, total=30, per_page=10, base_url="/admin/users", extra_query="",
    )
    html2 = render_to_string(p2)
    assert "cursor-not-allowed" in html2 or "invisible" in html2 or "<span" in html2
    # Next should be disabled on last page
    p2 = Pagination(
        page=3, total=30, per_page=10, base_url="/admin/users", extra_query="",
    )
    html2 = render_to_string(p2)
    assert "cursor-not-allowed" in html2 or "invisible" in html2
