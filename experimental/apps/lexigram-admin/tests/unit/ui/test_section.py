from lexigram.ui.core.base import render_to_string
from lexigram.ui.molecules.section import Section


def test_section_collapsible_uses_alpine_js():
    s = Section(title="Test Section", collapsible=True)
    html = render_to_string(s)

    # Collapse button should use Alpine.js x-on:click attribute
    assert "x-on-click" in html or "x_on_click" in html
    assert "collapsed = !collapsed" in html
