from lexigram.ui.atoms.switch import Switch
from lexigram.ui.core.base import render_to_string
from lexigram.ui.molecules.toggle import ToggleIcon


def test_toggle_icon_renders_with_icons_and_click():
    html = render_to_string(
        ToggleIcon(
            icon_on="sun",
            icon_off="moon",
            state_var="darkMode",
            aria_label="Toggle theme",
        ),
    )
    # Both icon svgs should be present (icons return svg markup)
    assert "svg" in html
    # ToggleIcon should wire up the state toggle click
    assert "x-on:click" in html
    assert "darkMode" in html


def test_switch_delegates_to_toggle_and_has_hidden_input():
    html = render_to_string(Switch(label="Notify me", name="notify", value=True))
    # Contains the hidden checkbox input for form submission
    assert 'type="checkbox"' in html
    assert 'name="notify"' in html
    # Role switch is present on the button
    assert 'role="switch"' in html
