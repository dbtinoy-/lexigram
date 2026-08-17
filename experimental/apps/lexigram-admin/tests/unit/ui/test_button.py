from lexigram.ui.atoms.button import Button, SubmitButton
from lexigram.ui.core.base import render_to_string


def test_button_renders_label_and_classes():
    html = render_to_string(Button("Save", variant="default", size="sm", id_="save-btn"))
    assert html.startswith("<button")
    assert "Save" in html
    assert "bg-primary" in html
    assert "px-3" in html
    assert 'id="save-btn"' in html


def test_button_custom_class_merged():
    html = render_to_string(Button("Ok", class_="extra-class"))
    assert "Ok" in html
    assert "extra-class" in html


def test_submit_button_renders_loading_and_disabled():
    sb = SubmitButton(
        label="Send",
        loading_label="Sending...",
        variant="secondary",
        size="sm",
        disabled=True,
    )
    html = render_to_string(sb)
    assert "Send" in html
    assert "Sending..." in html
    assert 'type="submit"' in html
    # disabled is a boolean attribute - check presence
    assert "disabled" in html
    # Alpine attributes should be present
    assert 'x-data="{ loading: false }"' in html
    assert 'x-on-click="loading = true"' in html
    assert 'x-on-htmx-after-request="loading = false"' in html
