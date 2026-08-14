from __future__ import annotations

from typing import Any

from lexigram.ui import Component, el


class LanguageSwitcher(Component):
    """Dropdown language switcher for the admin UI.

    Renders as a ``<select>`` that posts the chosen locale to *action_url*
    (default ``/admin/set-locale``).  On change it submits the wrapping form
    automatically via Alpine.js ``x-on:change``.

    Args:
        locales: Ordered list of ``(code, label)`` pairs,
            e.g. ``[("en", "English"), ("fr", "Français")]``.
        current_locale: The currently active locale code.
        action_url: URL that accepts a ``POST`` with ``locale=<code>``.
        **props: Extra HTML attributes forwarded to the wrapper element.
    """

    def __init__(
        self,
        locales: list[tuple[str, str]] | None = None,
        current_locale: str = "en",
        action_url: str = "/admin/set-locale",
        **props: Any,
    ) -> None:
        super().__init__(**props)
        self.locales = locales or [("en", "English")]
        self.current_locale = current_locale
        self.action_url = action_url

    def render(self) -> Any:
        options = [
            el(
                "option",
                label,
                value=code,
                selected=(code == self.current_locale) or None,
            )
            for code, label in self.locales
        ]
        select = el(
            "select",
            *options,
            name="locale",
            class_=(
                "text-sm bg-transparent border border-border "
                "rounded px-2 py-1 text-foreground "
                "focus:outline-none focus:ring-2 focus:ring-ring cursor-pointer"
            ),
            **{"x-on:change": "$el.form.submit()"},
        )
        return el(
            "form",
            select,
            method="POST",
            action=self.action_url,
            class_="inline-block",
        )


class ThemeToggle(Component):
    """
    Client-side theme toggle powered by Alpine.js and localStorage.
    """

    def render(self) -> Any:
        from lexigram.ui import ToggleIcon

        return ToggleIcon(
            icon_on="moon",
            icon_off="sun",
            state_var="darkMode",
            aria_label="Toggle theme",
            size="sm",
        ).render()


# UserBox has been moved to its own module for clarity and reusability.


class TopBar(Component):
    """
    Evolution of TopBar with extensible slots and refined aesthetics.
    """

    def __init__(
        self,
        title: str = "Admin",
        user: Any | None = None,
        user_menu_items: list[dict[str, Any]] | None = None,
        left: Any | None = None,
        center: Any | None = None,
        right: Any | None = None,
        site_name: str = "",
        **props: Any,
    ) -> None:
        super().__init__(**props)
        self.title_val = title
        self.site_name = site_name
        self.left = left
        self.center = center
        self.right = right
        self.user = user
        self.user_menu_items = user_menu_items

    def render(self) -> Any:
        # Default Left: Mobile toggle + Title
        left_node = self.left
        if left_node is None:
            from lexigram.ui import ActionButton

            toggle = ActionButton(
                label="",
                color="ghost",
                icon="menu",
                size="sm",
                **{  # type: ignore[arg-type]
                    "x-on:click": "sidebarOpen = !sidebarOpen",
                    "class_": "mr-4 lg:hidden",
                },
            ).render()

            title_text = self.title_val or "Admin"
            site_elements = []
            if self.site_name:
                site_elements.append(
                    el(
                        "span",
                        self.site_name,
                        class_="text-xs text-muted-foreground uppercase tracking-wider",
                    ),
                )
            site_elements.append(
                el(
                    "span",
                    title_text,
                    class_="text-lg font-bold text-foreground tracking-tight",
                ),
            )
            left_node = el(
                "div",
                toggle,
                el("div", *site_elements, class_="flex flex-col"),
                class_="flex items-center",
            )

        # Default Right: NotificationBell + ThemeToggle in header (UserBox is sidebar-only)
        right_node = self.right
        if right_node is None:
            from lexigram.ui import NotificationBell

            right_elements = []
            right_elements.append(
                NotificationBell(inbox_url="/admin/notifications").render()
            )
            right_elements.append(ThemeToggle())
            right_node = el(
                "div",
                *right_elements,
                class_="flex items-center space-x-3",
            )

        center_node = self.center or ""
        if not center_node:
            center_node = el(
                "div",
                el(
                    "div",
                    el(
                        "svg",
                        el(
                            "path",
                            stroke_linecap="round",
                            stroke_linejoin="round",
                            stroke_width="2",
                            d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z",
                        ),
                        class_="w-5 h-5 text-muted-foreground",
                        fill="none",
                        viewBox="0 0 24 24",
                        stroke="currentColor",
                    ),
                    el(
                        "span",
                        "Search (Cmd+K)",
                        class_="ml-3 text-muted-foreground text-sm hidden sm:block",
                    ),
                    class_="flex items-center w-full max-w-md px-4 py-2 bg-muted rounded-lg cursor-pointer hover:bg-muted/80 transition-colors",
                    **{"x-on:click": "$dispatch('open-command-palette')"},
                ),
                class_="flex-1 flex justify-center max-w-2xl",
            )

        return el(
            "header",
            el(
                "div",
                el("div", left_node, class_="flex-shrink-0"),
                el("div", center_node, class_="flex-1 flex justify-center px-4"),
                el("div", right_node, class_="flex-shrink-0"),
                class_="px-4 h-16 flex items-center justify-between",
            ),
            class_="bg-background/80 backdrop-blur-md border-b border-border sticky top-0 z-20 shadow-sm transition-colors duration-300",
        )
