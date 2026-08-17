from lexigram.ui.core.base import el, render_to_string
from lexigram.ui.molecules.modal import Modal
from lexigram.ui.organisms.forms import Form
from lexigram.ui.organisms.slide_over import SlideOver


def make_long_form(label="Save"):
    f = Form(action_url="/long", submit_label=label)
    # Add many lines to force overflow
    for i in range(50):
        f.children.append(el("div", f"Line {i}", class_="py-6"))
    return f


def test_modal_form_renders_sticky_footer():
    f = make_long_form()
    m = Modal("Long Form", trigger=None, render_trigger=False, children=[f])
    html = render_to_string(m)

    # Footer should be sticky
    assert "sticky bottom-0" in html

    # Footer should appear after the scrollable content div
    assert html.index("overflow-y-auto") < html.index("sticky bottom-0")


def test_slideover_form_renders_sticky_footer():
    f = make_long_form("Save Changes")
    so = SlideOver("Long Edit", trigger=None, render_trigger=False, children=[f])
    html = render_to_string(so)

    # Footer should have the submit button
    assert "Save Changes" in html

    # Footer should have visible border separator
    assert "border-t" in html

    # Footer should appear after scrollable content
    assert "overflow-y-auto" in html
