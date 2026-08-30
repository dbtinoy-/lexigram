"""Form Tabs layout — accessible tab pattern.

Tab headers must be ``type="button"`` (inside a form a plain button
defaults to ``type="submit"`` and would submit the form on every tab
click), announce selection state, and drive Alpine visibility so only the
active pane is shown.
"""

from __future__ import annotations

import re

from lexigram.admin.forms import FormBase, FormLayoutBuilder
from lexigram.admin.schema import TextField


class _TabsForm(FormBase):
    name = TextField(name="name", label="Name")
    email = TextField(name="email", label="Email")
    layout = FormLayoutBuilder.create().tabs(
        {"General": ["name"], "Contact": ["email"]},
    ).build()


class TestFormTabsAccessibility:
    def test_tab_headers_do_not_submit_form(self) -> None:
        html = str(_TabsForm(form_id="user-form").render())
        tabs = re.findall(r"<button[^>]*role=\"tab\"[^>]*>.*?</button>", html, re.S)
        assert len(tabs) == 2
        assert all('type="button"' in t for t in tabs)

    def test_tab_aria_contract(self) -> None:
        html = str(_TabsForm(form_id="user-form").render())
        assert 'role="tablist"' in html
        assert ':aria-selected="activeTab === 0"' in html
        assert ':aria-selected="activeTab === 1"' in html
        assert 'aria-controls="user-form-tab-panel-0"' in html
        assert 'id="user-form-tab-0"' in html
        assert 'aria-labelledby="user-form-tab-0"' in html

    def test_only_active_pane_visible(self) -> None:
        html = str(_TabsForm(form_id="user-form").render())
        assert 'x-show="activeTab === 0"' in html
        assert 'x-show="activeTab === 1"' in html
        assert 'role="tabpanel"' in html

    def test_keyboard_navigation_handlers(self) -> None:
        html = str(_TabsForm(form_id="user-form").render())
        assert "@keydown.arrow-right.prevent" in html
        assert "@keydown.arrow-left.prevent" in html
        assert "@keydown.home.prevent" in html
        assert "@keydown.end.prevent" in html
