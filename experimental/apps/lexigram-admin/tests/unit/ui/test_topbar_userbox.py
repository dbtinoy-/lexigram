"""Regression tests for the topbar account control."""

from __future__ import annotations

from types import SimpleNamespace

from lexigram.admin.ui.organisms.topbar import TopBar
from lexigram.ui import render_to_string


def test_topbar_renders_personal_account_actions_without_sidebar_state() -> None:
    html = render_to_string(
        TopBar(
            user={"name": "Carol", "avatar_url": "", "roles": ["operator"]},
            user_menu_items=[
                {
                    "label": "Profile",
                    "href": "/backoffice/profile",
                    "icon": "user-circle",
                }
            ],
            admin_prefix="/backoffice",
        )
    )

    assert "Carol" in html
    assert "Profile" in html
    assert 'href="/backoffice/profile"' in html
    assert 'href="/backoffice/logout"' in html
    assert 'aria-label="Open account menu for Carol"' in html
    assert "admin-topbar-user" in html
    # The topbar account control must not be coupled to sidebar collapse state.
    assert "sidebarMini" not in html


def test_topbar_accepts_protocol_shaped_user_objects() -> None:
    html = render_to_string(
        TopBar(
            user=SimpleNamespace(name="Dana", roles=("operator",)),
            user_menu_items=[],
        )
    )

    assert "Dana" in html
    assert 'href="/admin/logout"' in html


def test_topbar_without_user_does_not_render_empty_account_control() -> None:
    html = render_to_string(TopBar(user=None))

    assert "admin-topbar-user" not in html
    assert "Open account menu" not in html
