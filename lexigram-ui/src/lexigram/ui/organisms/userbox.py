from __future__ import annotations

from typing import Any

from lexigram.ui import Component, el


class UserBox(Component):
    """
    A compact user profile display for headers or sidebars.
    """

    def __init__(
        self,
        username: str,
        avatar_url: str | None = None,
        direction: str = "down",
        position: str = "right",
        roles: list[str] | None = None,
        user_menu_items: list[dict] | None = None,
        user: Any | None = None,
        **props,
    ) -> None:
        super().__init__(
            username=username,
            avatar_url=avatar_url,
            direction=direction,
            position=position,
            roles=roles,
            user_menu_items=user_menu_items,
            user=user,
            **props,
        )
        self.username = username
        self.avatar_url = avatar_url
        self.direction = direction
        self.position = position
        self.roles = roles or []
        self.user_menu_items = user_menu_items or []
        self.user = user

    def render(self) -> Any:
        from lexigram.ui import Dropdown

        if not self.avatar_url:
            avatar = el(
                "div",
                self.username[0].upper(),
                class_="w-8 h-8 rounded-full bg-primary-100 text-primary-600 flex items-center justify-center font-bold text-sm dark:bg-primary-900/30 dark:text-primary-400 border border-border",
            )
        else:
            avatar = el(
                "img",
                src=self.avatar_url,
                class_="w-8 h-8 rounded-full border border-border",
            )

        name = el(
            "div",
            self.username,
            class_="font-medium text-sm text-foreground truncate flex-1 text-left",
            x_show="!sidebarMini",
        )

        trigger = el(
            "div",
            avatar,
            name,
            el(
                "svg",
                el("path", d="M19 9l-7 7-7-7"),
                class_="ml-auto h-4 w-4 text-muted-foreground",
                fill="none",
                viewBox="0 0 24 24",
                stroke="currentColor",
                x_show="!sidebarMini",
            ),
            class_="flex items-center space-x-3 p-2 hover:bg-card transition-colors cursor-pointer w-full border border-transparent hover:border-border",
            **{"x-bind:class": "sidebarMini ? 'justify-center' : ''"},
        )

        # Dropdown Items
        items = []

        # RBACChecker logic removed

        for menu_item in self.user_menu_items:
            required_permission = menu_item.get("permission")
            if required_permission and self.user:
                try:
                    # Check permission using AuthenticatedUserProtocol.has_permission
                    has_perm = False
                    if hasattr(self.user, "has_permission"):
                        has_perm = self.user.has_permission(required_permission)
                    elif hasattr(self.user, "permissions"):
                        # Basic check
                        has_perm = required_permission in self.user.permissions

                    if not has_perm:
                        continue
                except (AttributeError, TypeError):
                    continue

            # Allow menu items to supply attributes (data-test hooks, etc.)
            attrs = dict(menu_item.get("attrs", {}))
            href = menu_item.get("href", "#")

            # By default render as a block item in dropdown and make it HTMX-enabled
            # so clicking updates the main content area (consistent with system menu)
            # Icon rendering
            icon_node: Any = ""
            if menu_item.get("icon"):
                from lexigram.ui import Icon

                icon_node = Icon(
                    menu_item["icon"],
                    class_name="w-4 h-4 mr-2 text-muted-foreground group-hover:text-muted-foreground dark:text-muted-foreground",
                )

            items.append(
                el(
                    "a",
                    icon_node,
                    menu_item.get("label", ""),
                    href=href,
                    class_="group flex items-center px-4 py-2 text-sm text-foreground hover:bg-muted dark:hover:bg-card rounded-md",
                    hx_get=href,
                    hx_target="#main-content",
                    hx_swap="innerHTML",
                    hx_push_url="true",
                    **attrs,
                ),
            )

        if items:
            items.append(el("div", class_="h-px my-1 bg-muted"))

        items.append(
            el(
                "a",
                "Sign out",
                href="/admin/logout",
                class_="block px-4 py-2 text-sm text-destructive hover:bg-destructive/10 rounded-md",
            ),
        )

        return Dropdown(
            trigger=trigger,
            items=items,
            direction=self.direction,
            position=self.position,
        )
