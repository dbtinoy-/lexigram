"""Ensure AdminShell passes system menu items into Sidebar without error."""

from pathlib import Path
import sys


from lexigram.ui.core.base import render_to_string
from lexigram.admin.ui.templates.shell import AdminShell


def test_adminshell_renders_with_system_menu():
    system = [{"label": "Sys", "href": "/admin/sys"}]
    shell = AdminShell(
        content="<div/>",
        title="T",
        user={},
        user_menu_items=[],
        system_menu_items=system,
    )
    html = render_to_string(shell)

    assert "Sys" in html
    assert "/admin/sys" in html
