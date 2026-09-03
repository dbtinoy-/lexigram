"""Settings-panel navigation contracts (R52, docs/09-01-2026/48).

The panel sidebar must retain a stable content target, and the shell's
history-aware script must be present to keep active styling and ARIA state
truthful after an in-place HTMX swap.
"""

from __future__ import annotations

from lexigram.admin.ui.templates.shell_scripts import search_overlay_markup
from lexigram.ui import render_to_string


def test_shell_script_syncs_settings_panel_state_after_history_navigation() -> None:
    html = render_to_string(search_overlay_markup())

    assert "syncSettingsPanelNavigation" in html
    assert "htmx:pushedIntoHistory" in html
    assert "htmx:historyRestore" in html
    assert "data-settings-panel-nav" in html
    assert "setAttribute('aria-current', 'page')" in html
    assert "dark:bg-primary-900/30" in html


def test_shell_script_handles_browser_back_forward_for_panel_state() -> None:
    html = render_to_string(search_overlay_markup())

    assert "window.addEventListener('popstate'" in html
    assert "new URL(path || location.href, location.href).pathname" in html
    assert "removeAttribute('aria-current')" in html
