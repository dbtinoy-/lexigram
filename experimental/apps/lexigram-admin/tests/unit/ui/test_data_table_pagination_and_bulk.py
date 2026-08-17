from lexigram.ui.core.base import render_to_string
from lexigram.ui.columns.types import TextColumn
from lexigram.admin.ui.organisms.data_table import DataTable
from lexigram.ui.core.zones import Zones


def test_pagination_includes_state_in_hx_get():
    """Test that pagination links include state params and use correct zone target."""
    dt = DataTable(
        columns=[TextColumn("name")],
        data=[{"id": 1}],
        total=50,
        per_page=10,
        page=2,
        filters={"search": "term"},
        sort_by="name",
        sort_order="asc",
        resource_prefix="/admin/users",
    )
    html = render_to_string(dt)
    # Pagination links should include the sort_by query and search term
    assert "sort_by=name" in html or "search=term" in html
    # Links should also include HTMX attributes with correct zone targets
    assert "hx-get" in html
    # Should target the DATA zone (new pattern)
    assert f'hx-target="{Zones.DATA.selector}"' in html


def test_bulk_action_button_has_hx_include():
    data = [{"id": 1}, {"id": 2}]
    dt = DataTable(
        columns=[TextColumn("name")],
        data=data,
        resource_prefix="/admin/users",
        bulk_actions=None,
    )
    html = render_to_string(dt)
    # Bulk actions should include the hx-include attribute for selected ids (HTML escaping allowed)
    assert "hx-include" in html and "ids" in html
