"""Dark mode theme toggle component."""

from __future__ import annotations

from typing import Any

from lexigram.ui.core.base import Component, el


class ThemeToggle(Component):
    """Theme toggle with light/dark/system modes.

    Persists preference in localStorage. Falls back to system
    ``prefers-color-scheme`` when no preference is stored.
    Renders as an icon button that cycles through modes.
    """

    def render(self) -> Any:
        return el(
            "button",
            {"x-on:click": "cycleTheme()"},
            el(
                "svg",
                el(
                    "path",
                    d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z",
                ),
                aria_hidden="true",
                fill="none",
                viewBox="0 0 24 24",
                stroke="currentColor",
                stroke_width="2",
                x_show="theme === 'light'",
                class_="h-5 w-5",
            ),
            el(
                "svg",
                el("path", d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"),
                aria_hidden="true",
                fill="currentColor",
                viewBox="0 0 24 24",
                x_show="theme === 'dark'",
                class_="h-5 w-5",
            ),
            el(
                "svg",
                el(
                    "path",
                    d="M3 5a2 2 0 012-2h14a2 2 0 012 2v10a2 2 0 01-2 2h-3l-1 3H9l-1-3H5a2 2 0 01-2-2V5z",
                ),
                aria_hidden="true",
                fill="none",
                viewBox="0 0 24 24",
                stroke="currentColor",
                stroke_width="2",
                x_show="theme === 'system'",
                class_="h-5 w-5 opacity-50",
            ),
            type="button",
            class_="inline-flex items-center justify-center rounded-md p-2 text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
            aria_label="Toggle theme",
            x_data="themeToggle()",
            x_init="$store.theme = localStorage.getItem('theme')",
        )
