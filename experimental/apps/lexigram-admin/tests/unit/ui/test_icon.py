from lexigram.ui.atoms.icon import Icon
from lexigram.ui.core.base import render_to_string


def test_icon_renders_svg_for_known_icon():
    html = render_to_string(Icon("search"))
    assert html.startswith("<svg")
    assert 'viewBox="0 0 24 24"' in html


def test_icon_renders_fallback_for_emoji_short_name():
    html = render_to_string(Icon("🔍"))
    assert html.startswith("<span")
    assert "🔍" in html
