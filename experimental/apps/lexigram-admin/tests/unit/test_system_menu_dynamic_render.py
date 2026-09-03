

from lexigram.admin.ui.organisms.sidebar import Sidebar
from lexigram.ui.core.base import render_to_string


def test_settings_renders_as_block_when_flagged():
    user = {"name": "Carol", "id": "u3"}
    system_menu = [
        {
            "label": "Settings",
            "href": "/admin/settings",
            "render": "block",
            "attrs": {"data-test": "system-settings"},
        },
    ]

    sidebar = Sidebar(
        items=[],
        user=user,
        user_menu_items=[],
        system_menu_items=system_menu,
        logo_text="App",
    )
    html = render_to_string(sidebar)

    # Block-style items are rendered inside the system dropdown; assert the
    # anchor and data-test attribute are present in the rendered output
    assert 'href="/admin/settings"' in html
    # Data-test hook should come from the nav attrs
    assert 'data-test="system-settings"' in html
    # The block item should be rendered directly as a stacked list
    assert "block px-4 py-2" in html
