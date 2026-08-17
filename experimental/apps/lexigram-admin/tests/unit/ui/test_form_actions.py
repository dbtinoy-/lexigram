from lexigram.ui.core.base import render_to_string
from lexigram.ui.molecules.form_actions import FormActions


def test_form_actions_cancel_uses_hx_on_click():
    html = render_to_string(FormActions(primary_text="Save", secondary_text="Cancel"))

    assert "Cancel" in html
    assert "hx-on-click" in html
    assert "history.back" in html
