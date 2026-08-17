"""Tests for AdminCard and PageLayout organisms (E9)."""

from __future__ import annotations


# ---------------------------------------------------------------------------
# AdminCard
# ---------------------------------------------------------------------------


def test_admin_card_renders_title() -> None:
    from lexigram.ui.organisms.admin import AdminCard

    html = str(AdminCard(title="Users", content="Body text"))
    assert "Users" in html


def test_admin_card_renders_content() -> None:
    from lexigram.ui.organisms.admin import AdminCard

    html = str(AdminCard(title="Stats", content="42 active users"))
    assert "42 active users" in html


def test_admin_card_has_card_classes() -> None:
    from lexigram.ui.organisms.admin import AdminCard

    html = str(AdminCard(title="Pets", content="list"))
    assert "bg-card" in html
    assert "border" in html
    assert "rounded" in html


def test_admin_card_title_in_header_section() -> None:
    from lexigram.ui.organisms.admin import AdminCard

    html = str(AdminCard(title="Section", content=""))
    title_pos = html.find("Section")
    assert title_pos != -1


def test_admin_card_no_title() -> None:
    from lexigram.ui.organisms.admin import AdminCard

    html = str(AdminCard(content="Just content"))
    assert "Just content" in html


def test_admin_card_accepts_html_content() -> None:
    from lexigram.ui.core.base import el
    from lexigram.ui.organisms.admin import AdminCard

    inner = el("p", "Paragraph inside card")
    html = str(AdminCard(title="Rich", content=inner))
    assert "Paragraph inside card" in html


def test_admin_card_importable_from_public_api() -> None:
    from lexigram.ui import AdminCard

    assert AdminCard is not None


# ---------------------------------------------------------------------------
# PageLayout
# ---------------------------------------------------------------------------


def test_page_layout_renders_title() -> None:
    from lexigram.ui.organisms.admin import PageLayout

    html = str(PageLayout(title="Dashboard", children="Content here"))
    assert "Dashboard" in html


def test_page_layout_renders_children() -> None:
    from lexigram.ui.organisms.admin import PageLayout

    html = str(PageLayout(title="Users", children="User list goes here"))
    assert "User list goes here" in html


def test_page_layout_renders_actions() -> None:
    from lexigram.ui.atoms.button import Button
    from lexigram.ui.organisms.admin import PageLayout

    action = Button("Add User")
    html = str(PageLayout(title="Users", children="list", actions=[action]))
    assert "Add User" in html


def test_page_layout_no_actions_when_none() -> None:
    from lexigram.ui.organisms.admin import PageLayout

    html = str(PageLayout(title="Empty", children="body"))
    assert "body" in html
    assert "Empty" in html


def test_page_layout_has_layout_structure() -> None:
    from lexigram.ui.organisms.admin import PageLayout

    html = str(PageLayout(title="Settings", children="form"))
    title_pos = html.find("Settings")
    content_pos = html.find("form")
    assert title_pos != -1 and content_pos != -1
    assert title_pos < content_pos


def test_page_layout_accepts_component_children() -> None:
    from lexigram.ui.organisms.admin import AdminCard, PageLayout

    card = AdminCard(title="Stats", content="123")
    html = str(PageLayout(title="Overview", children=card))
    assert "Stats" in html
    assert "123" in html


def test_page_layout_importable_from_public_api() -> None:
    from lexigram.ui import PageLayout

    assert PageLayout is not None
