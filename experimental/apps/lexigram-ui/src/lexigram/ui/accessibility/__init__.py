"""
Accessibility utilities for Lexigram Admin UI.

Provides ARIA attributes, live region announcements, and keyboard
navigation helpers for HTMX-powered components.
"""

from __future__ import annotations

from lexigram.ui.accessibility._aria_functions import (
    SkipLink,
    announce,
    announce_action_complete,
    announce_selection_change,
    announce_table_update,
    button_aria,
    cell_aria,
    dialog_aria,
    header_aria,
    keyboard_navigation_script,
    live_region_aria,
    row_aria,
    search_aria,
    tab_aria,
    table_aria,
    tabpanel_aria,
)
from lexigram.ui.accessibility._aria_types import AriaAttrs, AriaLive, AriaRole

__all__ = [
    "AriaAttrs",
    "AriaLive",
    "AriaRole",
    "SkipLink",
    "announce",
    "announce_action_complete",
    "announce_selection_change",
    "announce_table_update",
    "button_aria",
    "cell_aria",
    "dialog_aria",
    "header_aria",
    "keyboard_navigation_script",
    "live_region_aria",
    "row_aria",
    "search_aria",
    "tab_aria",
    "table_aria",
    "tabpanel_aria",
]
