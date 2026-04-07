from lexigram.ui.atoms.link import Link
from lexigram.ui.core.base import render_to_string


def test_link_renders_anchor_and_href_and_classes():
    html = render_to_string(
        Link("Go", href="/x", variant="primary", size="sm", id_="go"),
    )
    assert html.startswith("<a")
    assert 'href="/x"' in html
    assert 'id="go"' in html
    assert "text-primary" in html


def test_link_custom_class_merge():
    html = render_to_string(Link("More", href="/more", class_="extra"))
    assert "extra" in html
    assert "<a" in html
