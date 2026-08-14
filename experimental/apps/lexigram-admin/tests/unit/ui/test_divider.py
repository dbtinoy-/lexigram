from lexigram.ui.atoms.divider import Divider
from lexigram.ui.core.base import render_to_string


def test_divider_renders_hr_by_default():
    html = render_to_string(Divider())
    assert html.startswith("<hr") or html.startswith("<div")
    assert "border-t" in html


def test_divider_vertical_renders_div_with_border_left():
    html = render_to_string(Divider(orientation="vertical", class_name="h-6"))
    assert "border-l" in html
    assert "h-6" in html
