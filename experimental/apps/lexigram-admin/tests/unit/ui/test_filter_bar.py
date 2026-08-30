from lexigram.admin.schema import SelectField
from lexigram.admin.ui.filters.types import SelectFilter
from lexigram.admin.ui.molecules.filter_bar import FilterBar
from lexigram.ui.state import TableState
from lexigram.ui.core.base import render_to_string


def test_filter_bar_renders_various_controls_and_htmx_attrs():
    filters = {
        "status": {"type": "select", "options": ["active", "inactive"]},
        "is_featured": {"type": "checkbox"},
        "start_date": {"type": "date"},
        "name": {"type": "select", "options": []},
    }
    current = {"status": "active", "is_featured": "true", "start_date": "2025-01-01"}
    fb = FilterBar(
        filters=filters, current_values=current, resource_prefix="/admin/items",
    )
    html = render_to_string(fb)

    assert "Status" in html or "status" in html
    assert "Is Featured" in html or "is_featured" in html
    assert "Start Date" in html or "start_date" in html
    assert 'name="filter_start_date"' in html
    assert 'type="date"' in html
    assert "Filter by name" in html or "name" in html

    # HTMX attributes should be present
    assert "hx-get" in html
    assert "hx-target" in html
    assert "hx-include" in html
    assert "hx-trigger" in html or "keyup" in html


def test_filter_bar_preserves_search_sort_layout():
    """FilterBar with state should include state via hx-include."""
    state = TableState(
        search="findme", sort_by="name", sort_order="asc", layout="sidebar"
    )
    fb = FilterBar(
        filters=[SelectFilter("status", options=["a", "b"])],
        resource_prefix="/admin/users",
        state=state,
    )
    html = str(fb.render())

    # Targets data zone (canonical contract)
    assert 'hx-target="#table-data"' in html
    # hx-include dynamically picks up state from hidden inputs at request time
    assert "hx-include" in html
    assert "hx-vals" not in html  # no longer baked — hx-include replaces it


def test_filter_bar_wires_declarative_schema_filters() -> None:
    fb = FilterBar(
        filters=[SelectField(name="status", options=[("active", "Active")])],
        current_values={"status": "active"},
        resource_prefix="/admin/items",
        state=TableState(),
    )

    html = render_to_string(fb)

    assert 'name="status"' in html
    assert 'hx-get="/admin/items/"' in html
    assert 'hx-target="#table-data"' in html
    assert 'hx-trigger="change"' in html
