"""Tests for UserBox extraction and basic rendering."""

from pathlib import Path
import sys

# Ensure package src and sibling packages are importable in test environment

from lexigram.ui.core.base import render_to_string
from lexigram.admin.ui.organisms.userbox import UserBox


def test_userbox_renders_menu_items():
    user = {"name": "Bob"}
    ub = UserBox(
        "Bob",
        user_menu_items=[
            {
                "label": "Settings",
                "href": "/admin/settings",
                "attrs": {"data-test": "system-settings"},
            },
        ],
        user=user,
    )
    html = render_to_string(ub)

    assert "Settings" in html
    assert "/admin/settings" in html
    # HTMX-enabled anchor should be present
    assert 'hx-get="/admin/settings"' in html
    # Data-test attr should come from menu attrs
    assert 'data-test="system-settings"' in html
