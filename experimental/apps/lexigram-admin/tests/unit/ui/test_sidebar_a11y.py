"""Sidebar accessibility contract."""

from __future__ import annotations

from lexigram.admin.ui.organisms.sidebar import SidebarItem, SidebarSection
from lexigram.ui import render_to_string


class TestSidebarA11y:
    def test_inactive_item_omits_aria_current(self) -> None:
        html = render_to_string(SidebarItem("Users", "/admin/users"))
        assert 'aria-current="false"' not in html
        assert "aria-current" not in html

    def test_active_item_marks_aria_current_page(self) -> None:
        html = render_to_string(
            SidebarItem("Users", "/admin/users", active=True),
        )
        assert 'aria-current="page"' in html

    def test_section_header_links_to_items(self) -> None:
        section = SidebarSection(
            "People",
            [SidebarItem("Users", "/admin/users", active=True)],
        )
        html = render_to_string(section)
        assert 'aria-controls="section-people-items"' in html
        assert 'id="section-people-items"' in html

    def test_section_buttons_are_type_button_and_focusable(self) -> None:
        section = SidebarSection("People", [])
        html = render_to_string(section)
        assert 'type="button"' in html
        assert "focus-visible:ring-2" in html
