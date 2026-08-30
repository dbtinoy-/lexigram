from lexigram.admin.actions.standard import DeleteBulkAction
from lexigram.ui.core.base import render_to_string
from lexigram.ui.columns.types import TextColumn
from lexigram.admin.ui.organisms.data_table import DataTable


def test_bulk_action_bar_includes_bulk_buttons_and_hx_include():
    bulk_actions = [DeleteBulkAction()]
    data = [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]
    dt = DataTable(
        columns=[TextColumn("name")],
        data=data,
        resource_prefix="/admin/users",
        bulk_actions=bulk_actions,
    )
    html = render_to_string(dt)
    # Bulk action label present
    assert "Delete Selected" in html
    # hx-include attribute present for selected ids (HTML-escaped quotes are expected)
    assert "hx-include" in html
    assert "name=&#x27;ids&#x27;" in html or "[name='ids']:checked" in html
    # Ensure ActionButton styling is used (inline-flex) and the action
    # opens the confirmation GET before posting the bulk mutation.
    assert "inline-flex" in html
    assert "hx-get" in html


def test_bulk_action_includes_action_name():
    """Bulk action button should send action name via hx-vals."""
    bulk_actions = [DeleteBulkAction()]
    data = [{"id": 1, "name": "A"}]
    dt = DataTable(
        columns=[TextColumn("name")],
        data=data,
        resource_prefix="/admin/users",
        bulk_actions=bulk_actions,
    )
    html = render_to_string(dt)
    # hx-vals JSON attribute present with action name
    assert 'hx-vals=' in html


def test_bulk_counter_says_on_this_page():
    """Counter should say 'selected on this page', not just 'selected'."""
    bulk_actions = [DeleteBulkAction()]
    data = [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]
    dt = DataTable(
        columns=[TextColumn("name")],
        data=data,
        resource_prefix="/admin/users",
        bulk_actions=bulk_actions,
    )
    html = render_to_string(dt)
    assert "selected on this page" in html


def test_select_all_aria_label():
    """Select-all checkbox should have clear page-scoped aria-label."""
    bulk_actions = [DeleteBulkAction()]
    data = [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]
    dt = DataTable(
        columns=[TextColumn("name")],
        data=data,
        resource_prefix="/admin/users",
        bulk_actions=bulk_actions,
    )
    html = render_to_string(dt)
    assert 'aria-label="Select all rows on this page"' in html
