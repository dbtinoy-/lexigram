from lexigram.ui.core.base import render_to_string
from lexigram.ui.molecules.action_button import ActionButton


def test_action_button_renders_label_variant_and_size():
    html = render_to_string(ActionButton("Edit", variant="ghost", size="sm"))
    assert "Edit" in html
    assert "hover:bg-accent" in html
    assert "h-8 px-3 text-xs" in html
    assert 'type="button"' in html


def test_action_button_with_icon_positions_and_icon_tag():
    html = render_to_string(
        ActionButton("Go", icon="search", icon_position="left", size="sm"),
    )
    # Icon span with mr-2 should be present
    assert "mr-2" in html
    # Icon should render as svg
    assert "<svg" in html


def test_action_button_with_href_renders_anchor():
    html = render_to_string(ActionButton("Link", href="/x"))
    assert html.startswith("<a")
    assert 'href="/x"' in html
