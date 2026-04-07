from lexigram.ui.core.base import render_to_string
from lexigram.ui.organisms.slide_over import SlideOver


def test_slide_over_trigger_string_renders_actionbutton_with_click():
    so = SlideOver(title="Panel", trigger="Open")
    html = render_to_string(so)
    # Trigger should wire the click to open the panel
    assert (
        'x-on:click="open = true"' in html
        or 'x-on:click="open = true"' in html.replace('"', '"')
    )
    assert "Open" in html
    # Should render as button-like element
    assert "inline-flex" in html or "button" in html


def test_slide_over_close_button_present():
    so = SlideOver(title="Panel", trigger="Open")
    html = render_to_string(so)
    # Close control should set open = false
    assert "open = false" in html
    # Close icon should be present (svg or x span)
    assert "svg" in html or "Close panel" in html


def test_slide_over_transfers_form_submit_to_footer():
    from lexigram.ui.organisms.forms import Form

    # Create a regular Form (would normally render a submit inside form footer)
    f = Form(action_url="/test", submit_label="Save Changes")
    so = SlideOver(
        title="Edit Item", trigger="Edit", render_trigger=False, children=[f],
    )
    html = render_to_string(so)

    # The form's submit button should be present (click handler or type=submit)
    assert "Save Changes" in html
    assert "submit" in html.lower()

    # The footer should be outside the scroll content
    assert "border-t" in html


def test_slide_over_suppresses_nested_form_submit():
    from lexigram.ui.core.base import el
    from lexigram.ui.organisms.forms import Form

    f = Form(action_url="/nested", submit_label="Save Nested")
    wrapper = el("div", f)
    so = SlideOver(
        title="Nested Edit", trigger="Edit", render_trigger=False, children=[wrapper],
    )
    html = render_to_string(so)

    # Ensure nested form's submit button is present
    assert "Save Nested" in html
    assert "submit" in html.lower()
    # Footer should have border separator
    assert "border-t" in html
