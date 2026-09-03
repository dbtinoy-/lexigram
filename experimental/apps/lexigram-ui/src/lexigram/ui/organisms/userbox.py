from __future__ import annotations

from typing import Any

from lexigram.ui import Component, el


class UserBox(Component):
    """Compact account control for a sidebar or topbar.

    The sidebar variant can react to the shell's ``sidebarMini`` state. The
    topbar variant deliberately does not depend on sidebar state, so a user
    identity remains visible when the primary navigation is collapsed.
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
        logout_url: str = "/admin/logout",
        variant: str = "sidebar",
        collapse_var: str | None = "sidebarMini",
        **props: Any,
    ) -> None:
        super().__init__(
            username=username,
            avatar_url=avatar_url,
            direction=direction,
            position=position,
            roles=roles,
            user_menu_items=user_menu_items,
            user=user,
            logout_url=logout_url,
            variant=variant,
            collapse_var=collapse_var,
            **props,
        )
        self.username = username
        self.avatar_url = avatar_url
        self.direction = direction
        self.position = position
        self.roles = roles or []
        self.user_menu_items = user_menu_items or []
        self.user = user
        self.logout_url = logout_url
        self.variant = variant
        self.collapse_var = collapse_var

    def render(self) -> Any:
        from lexigram.ui import Dropdown

        expanded_visibility = f"!{self.collapse_var}" if self.collapse_var else None
        if not self.avatar_url:
            avatar = el(
                "div",
                self.username[:1].upper() or "U",
                class_="w-8 h-8 rounded-full bg-primary-100 text-primary-600 flex items-center justify-center font-bold text-sm dark:bg-primary-900/30 dark:text-primary-400 border border-border",
                aria_hidden="true",
            )
        else:
            avatar = el(
                "img",
                src=self.avatar_url,
                alt="",
                class_="w-8 h-8 rounded-full border border-border",
            )

        name_class = "font-medium text-sm text-foreground truncate flex-1 text-left"
        if self.variant == "topbar":
            name_class += " admin-topbar-user-name hidden sm:block max-w-[10rem]"
        name = el(
            "div",
            self.username,
            class_=name_class,
            x_show=expanded_visibility,
        )

        chevron = el(
            "svg",
            el("path", d="M19 9l-7 7-7-7"),
            class_="ml-auto h-4 w-4 text-muted-foreground",
            fill="none",
            viewBox="0 0 24 24",
            stroke="currentColor",
            x_show=expanded_visibility,
            aria_hidden="true",
            focusable="false",
        )
        dropdown_trigger_attrs: dict[str, Any] = {}
        if self.variant == "topbar":
            trigger_class = (
                "flex items-center gap-2 rounded-xl px-2 py-1.5 "
                "hover:bg-muted dark:hover:bg-card transition-colors "
                "cursor-pointer border border-transparent hover:border-border"
            )
            dropdown_trigger_attrs["aria-label"] = (
                f"Open account menu for {self.username}"
            )
            trigger_attrs: dict[str, Any] = {}
        else:
            trigger_class = (
                "flex items-center space-x-3 p-2 hover:bg-card transition-colors "
                "cursor-pointer w-full border border-transparent hover:border-border"
            )
            trigger_attrs = {}
            if self.collapse_var:
                trigger_attrs["x-bind:class"] = (
                    f"{self.collapse_var} ? 'justify-center' : ''"
                )

        trigger = el(
            "div",
            avatar,
            name,
            chevron,
            class_=trigger_class,
            **trigger_attrs,
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

            item_content = (
                icon_node,
                menu_item.get("label", ""),
            )
            item_classes = "group flex items-center px-4 py-2 text-sm text-foreground hover:bg-muted dark:hover:bg-card rounded-md"
            items.append(
                el(
                    "a",
                    *item_content,
                    href=href,
                    class_=item_classes,
                    **attrs,
                )
                if href and href != "#"
                else el(
                    "span",
                    *item_content,
                    class_=item_classes,
                    **attrs,
                )
            )

        if items:
            items.append(el("div", class_="h-px my-1 bg-muted"))

        items.append(
            el(
                "a",
                "Sign out",
                href=self.logout_url,
                class_="block px-4 py-2 text-sm text-destructive hover:bg-destructive/10 rounded-md",
            ),
        )

        return Dropdown(
            trigger=trigger,
            items=items,
            direction=self.direction,
            position=self.position,
            class_=(
                "admin-topbar-user-dropdown relative inline-block text-left"
                if self.variant == "topbar"
                else "relative inline-block text-left w-full"
            ),
            trigger_attrs=dropdown_trigger_attrs,
        )
