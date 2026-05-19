from lexigram.ui.core.base import render_to_string
from lexigram.ui import TablePagination as Pagination
from lexigram.ui.state import TableState


def test_pagination_not_render_when_single_page():
    p = Pagination(page=1, total=5, per_page=10, base_url="/", show_size_selector=True)
    html = render_to_string(p)
    assert html == "" or "results" not in html


def test_pagination_hides_size_selector_when_disabled():
    p = Pagination(
        page=1, total=50, per_page=10, base_url="/", show_size_selector=False,
    )
    html = render_to_string(p)
    # When size selector disabled, the <select> should not be present even if the 'Show' label remains
    assert "<select" not in html


def test_pagination_with_state_includes_search():
    """Test that pagination with state includes search term in URLs."""
    state = TableState(
        page=2,
        per_page=10,
        search="term",
    )
    p = Pagination(
        total=50,
        base_url="/items",
        state=state,
    )
    html = render_to_string(p)
    # Ensure HTMX attributes are present and the state params are in URLs
    assert "hx-get" in html
    assert "search=term" in html
    assert "hx-push-url" in html
