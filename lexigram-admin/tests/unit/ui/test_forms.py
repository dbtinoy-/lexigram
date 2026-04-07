from lexigram.ui.atoms.inputs import NumberInput, TextInput
from lexigram.ui.core.base import render_to_string
from lexigram.ui.molecules.form_actions import FormActions
from lexigram.ui.molecules.form_field import FieldSchema


def test_textinput_renders_label_error_and_passes_attrs():
    ti = TextInput(
        name="email",
        value="user@example.com",
        label="Email",
        placeholder="you@example.com",
        error="Invalid",
        hx_get="/search",
    )
    html = render_to_string(ti)
    assert 'name="email"' in html
    assert "Email" in html
    assert "Invalid" in html
    assert 'placeholder="you@example.com"' in html or "you@example.com" in html
    assert "hx-get" in html


def test_numberinput_renders_min_max_and_value():
    ni = NumberInput(name="age", value=30, label="Age", min_value=18, max_value=99, step=1)
    html = render_to_string(ni)
    assert 'type="number"' in html
    assert 'name="age"' in html
    assert 'min="18"' in html or "min=18" in html
    assert 'max="99"' in html or "max=99" in html


def test_formfield_wraps_input_and_shows_help_and_error():
    ti = TextInput(name="first_name", value="Alice")
    ff = FieldSchema(
        input_component=ti, label="First name", help_text="Enter your name",
    )
    html = render_to_string(ff)
    assert "First name" in html
    assert "Enter your name" in html
    # Check that the for attribute points to input id/name
    assert 'for="first_name"' in html or 'for="first_name"' in html

    # Error takes precedence over help text
    ff_err = FieldSchema(input_component=ti, label="First name", error="Required")
    html2 = render_to_string(ff_err)
    assert "Required" in html2
    assert "Enter your name" not in html2


def test_formactions_renders_submit_and_cancel_variants():
    # With cancel_url -> anchor link
    fa = FormActions(primary_text="Save", secondary_text="Cancel", cancel_url="/list")
    html = render_to_string(fa)
    assert "Save" in html
    assert "Cancel" in html
    assert 'href="/list"' in html or "href=/list" in html

    # Without cancel_url -> uses ActionButton (rendered as button) with history.back
    fa2 = FormActions(primary_text="Save", secondary_text="Cancel")
    html2 = render_to_string(fa2)
    assert "Save" in html2
    assert "Cancel" in html2
    assert "history.back" in html2 or "onclick" in html2
