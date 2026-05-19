from lexigram.ui.core.base import render_to_string
from lexigram.ui.columns.types import TextColumn
from lexigram.admin.ui.organisms.data_table import DataTable


def test_data_table_renders_empty_state_when_no_data():
    dt = DataTable(
        columns=[TextColumn("name")], data=[], resource_prefix="/admin/users",
    )
    html = render_to_string(dt)
    assert "No results found" in html
    assert "Try adjusting your filters" in html


def test_data_table_renders_header_with_search_and_create():
    dt = DataTable(
        columns=[TextColumn("name")], data=[], resource_prefix="/admin/users",
    )
    html = render_to_string(dt)
    # header should contain search input wrapper and Create button
    assert "Create New" in html
    # Search input should be present
    assert "<input" in html or "Search" in html
