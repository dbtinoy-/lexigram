from lexigram.ui.core.base import render_to_string
from lexigram.admin.ui.molecules.pagination import Pagination
from lexigram.admin.ui.state import TableState


def test_pagination_renders_page_links_with_state():
    """Test that pagination with state includes all state params in URLs."""
    state = TableState(
        page=2,
        per_page=10,
        sort_by="name",
        sort_order="asc",
    )
    pag = Pagination(
        total=50,
        base_url="/admin/users/",
        state=state,
    )
    html = render_to_string(pag)
    # Should show proper counts
    assert "Showing" in html
    assert "50" in html
    # Links should include state params (baked URL pattern)
    # Note: page=1 may not be in URL if it's the default; check for page=3 instead
    assert "page=3" in html
    assert "sort_by=name" in html
    # HX target should be the DATA zone
    assert 'hx-target="#table-data"' in html


def test_pagination_legacy_mode():
    """Test that pagination works without state (legacy mode)."""
    pag = Pagination(
        page=2,
        total=50,
        per_page=10,
        base_url="/admin/users/",
    )
    html = render_to_string(pag)
    # Should render without errors
    assert "Showing" in html
    assert 'hx-target="#table-data"' in html


def test_pagination_empty_when_single_page():
    pag = Pagination(page=1, total=5, per_page=10, base_url="/admin/users/")
    html = render_to_string(pag)
    assert html == ""
