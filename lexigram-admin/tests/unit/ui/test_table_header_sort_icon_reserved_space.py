from lexigram.ui.columns import TextColumn


def test_header_shows_sortable_indicator_when_not_sorted():
    """When a sortable column is not currently sorted, show a subtle indicator."""
    col = TextColumn("name").sortable()
    # Not currently sorted
    header_el = col.render_header(current_sort=None, sort_order="asc")
    html = str(header_el)

    # Should have an SVG icon (chevrons-up-down) that's hidden until hover
    assert "<svg" in html
    # The icon should have opacity-0 (hidden by default, shown on hover)
    assert "opacity-0" in html
    # Header should be clickable
    assert "cursor-pointer" in html


def test_header_shows_active_icon_when_sorted():
    """When a sortable column is currently sorted, show the direction icon."""
    col = TextColumn("name").sortable()
    # Column is currently sorted ascending
    header_el = col.render_header(current_sort="name", sort_order="asc")
    html = str(header_el)

    # When sorted, actual SVG icon should be present (chevron-up for asc)
    assert "<svg" in html
    # The icon should be visible (primary color, no opacity-0)
    assert "text-primary-600" in html or "text-primary-400" in html


def test_header_shows_descending_icon():
    """When sorted descending, show the down chevron."""
    col = TextColumn("name").sortable()
    header_el = col.render_header(current_sort="name", sort_order="desc")
    html = str(header_el)

    # Should have SVG and primary styling
    assert "<svg" in html
    assert "text-primary-600" in html or "text-primary-400" in html
