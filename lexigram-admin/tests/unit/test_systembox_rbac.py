from pathlib import Path
import sys


from lexigram.ui.core.base import render_to_string
from lexigram.ui import SystemBox


class MockUser:
    def __init__(self, username, permissions=None):
        self.username = username
        self.id = "u1"
        self.permissions = set(permissions or [])

    def has_permission(self, permission):
        return permission in self.permissions


def test_systembox_hides_items_when_no_permission():
    items = [
        {
            "label": "Settings",
            "href": "/admin/settings",
            "render": "block",
            "permission": "manage_settings",
            "attrs": {"data-test": "system-settings"},
        },
    ]

    # user without privilege
    user = MockUser(username="guest", permissions=[])
    sb = SystemBox(system_menu_items=items, user=user)
    out = render_to_string(sb)

    assert 'hx-get="/admin/settings"' not in out
    assert 'data-test="system-settings"' not in out


def test_systembox_shows_items_with_permission():
    items = [
        {
            "label": "Settings",
            "href": "/admin/settings",
            "render": "block",
            "permission": "manage_settings",
            "attrs": {"data-test": "system-settings"},
        },
    ]

    user = MockUser(username="admin", permissions=["manage_settings"])
    sb = SystemBox(system_menu_items=items, user=user)
    out = render_to_string(sb)

    assert 'hx-get="/admin/settings"' in out
    assert 'data-test="system-settings"' in out
