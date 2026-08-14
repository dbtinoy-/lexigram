

from lexigram.ui import SystemBox
from lexigram.ui.core.base import render_to_string


def test_systembox_renders_compact_and_block():
    items = [
        {
            "label": "Settings",
            "href": "/admin/settings",
            "render": "block",
            "attrs": {"data-test": "system-settings"},
        },
        {"label": "System", "href": "/admin/system", "icon": "cog"},
    ]
    sb = SystemBox(system_menu_items=items)
    out = render_to_string(sb)

    # Compact icon should be present
    assert "cog" in out or "System" in out
    # Block item should render via plain anchor in dropdown content
    assert 'href="/admin/settings"' in out
    # Data-test hook for settings should be present
    assert 'data-test="system-settings"' in out
