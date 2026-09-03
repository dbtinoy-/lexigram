"""Tests for system menu rendering in the sidebar footer."""

from pathlib import Path
import sys


from lexigram.ui.core.base import render_to_string
from lexigram.admin.ui.organisms.sidebar import Sidebar


def test_system_menu_renders_in_sidebar_utility_footer_without_account():
    user = {"name": "Carol", "id": "u3"}
    system_menu = [{"label": "System", "href": "/admin/system"}]
    sidebar = Sidebar(
        items=[],
        user=user,
        user_menu_items=[],
        system_menu_items=system_menu,
        logo_text="App",
    )
    html = render_to_string(sidebar)

    # System utilities remain in the sidebar footer, while identity/actions
    # are rendered by the topbar account control.
    assert "System" in html
    assert "admin-sidebar-footer" in html
    assert "Carol" not in html

    # Also ensure it's visible (not only sr-only)
    assert "sr-only" not in html or '<span class="sr-only">System</span>' not in html
