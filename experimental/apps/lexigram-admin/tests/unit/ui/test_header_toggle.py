from lexigram.ui.core.base import render_to_string
from lexigram.admin.ui.organisms.topbar import ThemeToggle, TopBar


def test_theme_toggle_renders_toggleicon_in_topbar():
    html = render_to_string(TopBar())
    # ToggleIcon should render an accessible label and wire up state toggle
    assert "Toggle theme" in html or 'aria_label="Toggle theme"' in html
    assert "x-on:click" in html or "darkMode" in html


def test_theme_toggle_component_direct_render():
    html = render_to_string(ThemeToggle())
    assert "Toggle theme" in html or 'aria_label="Toggle theme"' in html
    assert "x-on:click" in html or "darkMode" in html
