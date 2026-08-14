from lexigram.ui.core.base import render_to_string
from lexigram.ui.columns.types import TextColumn


def test_text_column_copyable_renders_hx_on_click():
    col = TextColumn("email").copyable()
    cell = col.render_cell({"email": "user@example.com"})
    html = render_to_string(cell)

    assert 'title="Click to copy"' in html
    # Use hx-on-click for client-side click handlers now
    assert "hx-on-click" in html
    # HTML escaping may apply to quotes; check for the JS function and the value separately
    assert "navigator.clipboard.writeText" in html
    assert "user@example.com" in html
