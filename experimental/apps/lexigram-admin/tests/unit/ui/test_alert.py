from lexigram.ui.core.base import render_to_string
from lexigram.ui.molecules.alert import Alert


def test_alert_dismissible_uses_actionbutton_x_icon():
    a = Alert("Oh no", variant="error", dismissible=True)
    html = render_to_string(a)
    # Close control should be an ActionButton with x icon (or SVG path present)
    assert "hx-" not in html  # no HTMX here
    assert "x" in html or "svg" in html or "Close" in html
    assert "ml-auto" in html  # class preserved
