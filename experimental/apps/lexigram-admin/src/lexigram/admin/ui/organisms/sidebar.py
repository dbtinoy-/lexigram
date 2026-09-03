from __future__ import annotations

from typing import Any

from lexigram.ui import Badge, Component, el


class SidebarItem(Component):
    """
    Individual navigation item for the sidebar.
    Supports icons, badges, and active state detection.
    """

    def __init__(
        self,
        label: str,
        href: str,
        icon: str | Any = None,
        badge: str | int | None = None,
        active: bool = False,
        **props,
    ) -> None:
        super().__init__(
            label=label,
            href=href,
            icon=icon,
            badge=badge,
            active=active,
            **props,
        )
        self.label = label
        self.href = href
        self.icon = icon
        self.badge = badge
        self.active = active

    def render(self) -> Any:
        # Determine base classes based on active state
        if self.active:
            bg_cls = "bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-400"
            icon_cls = "text-primary-600 dark:text-primary-400"
        else:
            bg_cls = "text-muted-foreground dark:text-muted-foreground hover:bg-muted dark:hover:bg-card/50 hover:text-primary-600 dark:hover:text-primary-400"
            icon_cls = "text-muted-foreground group-hover:text-primary-600 dark:group-hover:text-primary-400"

        # Icon rendering
        icon_node = ""
        has_icon = bool(self.icon)

        if has_icon:
            if hasattr(self.icon, "__html__") or isinstance(self.icon, Component):
                icon = self.icon
            else:
                from lexigram.ui import get_icon

                icon = get_icon(self.icon, class_name=icon_cls)

            # Icon Container: Show in both modes. Handle margin dynamically.
            # In wide mode (!mini): mr-3. In mini mode: mr-0 (centered by parent justify-center).
            icon_node = el(
                "div",
                icon,
                class_="transition-all duration-200",
                **{"x-bind:class": "sidebarMini ? 'mr-0' : 'mr-3'"},
            )

        # Badge rendering
        badge_node: Any = ""
        if self.badge is not None:
            badge_node = Badge(
                str(self.badge),
                variant="primary",
                class_="ml-auto",
                # Hidden in mini mode: there is no room for it beside the
                # icon, and it would wrap the row.
                x_show="!sidebarMini",
            )

        # Labels
        label_text = self.label.replace("_", " ").title()
        first_letter = label_text[0] if label_text else ""

        # Mini Label (First Letter) logic:
        # If has_icon: First Letter is NEVER shown (Icon takes precedence).
        # If !has_icon: First Letter is SHOWN in mini mode only.

        first_letter_node = ""
        if not has_icon:
            # Use x-bind:class for visibility keying off sidebarMini.
            # Note: We need 'flex' when visible. 'hidden' when not.
            # x-show works but manual class toggle is sometimes more robust in complex layouts.
            first_letter_node = el(
                "span",
                first_letter,
                class_="font-bold text-xs w-6 h-6 items-center justify-center shrink-0 rounded-lg bg-primary-100 dark:bg-primary-900 text-primary-600 dark:text-primary-300 border border-primary-200 dark:border-primary-800",
                **{"x-bind:class": "sidebarMini ? 'flex' : 'hidden'"},
            )

        return el(
            "a",
            icon_node,
            # Full Label
            el(
                "span",
                label_text,
                class_="truncate whitespace-nowrap",
                x_show="!sidebarMini",
            ),
            # Mini Label (First Letter)
            first_letter_node,
            badge_node,
            href=self.href,
            class_=(
                "group flex items-center px-3 py-2 text-sm font-medium rounded-xl "
                "transition-all duration-200 "
                "focus-visible:outline-none focus-visible:ring-2 "
                "focus-visible:ring-ring focus-visible:ring-offset-1 "
                f"{bg_cls}"
            ),
            # Use Alpine dict syntax for directives
            **{
                "x-bind:class": "sidebarMini ? 'justify-center' : ''",
                **({"aria-current": "page"} if self.active else {}),
            },
            title=self.label,
        )


class SidebarSection(Component):
    """
    A labeled group of sidebar items.
    """

    def __init__(self, title: str, items: list[SidebarItem], **props) -> None:
        super().__init__(title=title, items=items, **props)
        self.title = title
        self.items = items

    def render(self) -> Any:
        from lexigram.ui import get_icon

        # Group Icon Logic
        # If group has an icon, use it. If not, use a dot.
        group_icon_node = ""
        bool(
            self.items and hasattr(self, "icon") and self.icon,
        )  # Check if passed in init? SidebarSection doesn't capture icon in init explicitly in previous code, let's fix that or assume it might be in props

        # The provider passes 'icon' in props usually.
        # Let's check props for icon
        icon_name = getattr(self, "icon", None) or self.props.get("icon")

        if icon_name:
            # Remove mr-2 from icon itself, wrapper handles spacing
            group_icon_node = get_icon(
                icon_name,
                class_name="w-5 h-5 text-muted-foreground transition-colors group-hover:text-foreground dark:text-muted-foreground dark:group-hover:text-foreground",
            )
        else:
            # Dot icon
            group_icon_node = el(
                "div", class_="w-1.5 h-1.5 rounded-full bg-muted-foreground/40"
            )

        section_key = self.title.lower().replace(" ", "-").replace("/", "-")

        # Collapsible Header
        header = el(
            "button",
            # Icon / Dot Wrapper - Fixed width to align with tree border
            # px-3 (12px) + w-5 (20px)/2 = 22px center
            el(
                "div",
                group_icon_node,
                class_="w-5 h-5 flex items-center justify-center transition-all duration-200",
                **{"x-bind:class": "sidebarMini ? 'mr-0' : 'mr-3'"},
            ),
            # Title
            el(
                "span",
                self.title,
                class_="flex-1 text-left text-xs font-semibold uppercase tracking-wider whitespace-nowrap",
                x_show="!sidebarMini",
            ),
            # Chevron
            el(
                "div",
                get_icon("chevron-down", class_name="w-4 h-4"),
                class_="text-muted-foreground transition-transform duration-200",
                **{
                    "x-bind:class": "expanded ? 'rotate-0' : '-rotate-90'",
                    "x-show": "!sidebarMini",
                },
            ),
            type="button",
            class_=(
                "w-full flex items-center px-3 mt-4 mb-2 text-muted-foreground "
                "hover:text-foreground transition-colors "
                "focus-visible:outline-none focus-visible:ring-2 "
                "focus-visible:ring-ring focus-visible:ring-offset-1 rounded-lg group"
            ),
            title=self.title,
            **{
                "x-on:click": "expanded = !expanded",
                "x-bind:class": "sidebarMini ? 'justify-center' : ''",
                "x-bind:aria-expanded": "expanded ? 'true' : 'false'",
                "aria-controls": f"section-{section_key}-items",
            },
        )

        # Items Container
        # Tree border alignment:
        # Header Button px-3 (12px)
        # Icon Wrapper w-5 (20px). Center is 12 + 10 = 22px.
        # Border-l should be at 22px.
        # ml-[1.35rem] is roughly 22px (0.35rem = 5.6px? No. 1.375rem = 22px).
        items_container = el(
            "div",
            *self.items,
            id=f"section-{section_key}-items",
            class_="space-y-1 relative ml-[1.375rem] pl-3 border-l border-border",
            # Hide border in mini mode
            **{
                "x-show": "expanded || sidebarMini",
                # Use inline styles for layout reset to ensure they apply regardless of Tailwind scanning
                "x-bind:style": "sidebarMini ? { marginLeft: '0', paddingLeft: '0', borderLeft: '0' } : {}",
            },
        )

        return el(
            "div",
            header,
            items_container,
            class_="sidebar-section",
            **{
                "x-data": "{ expanded: localStorage.getItem('section-"
                + section_key
                + "') === 'true' }",
                "x-init": "$watch('expanded', val => localStorage.setItem('section-"
                + section_key
                + "', val))",
            },
        )


class Sidebar(Component):
    """
    Main Sidebar container with Logo, Navigation Sections, and utilities.

    Account identity and account actions are rendered by the topbar; the
    footer remains dedicated to application utilities and the collapse
    control.
    """

    def __init__(
        self,
        items: list[SidebarItem | SidebarSection],
        user: Any | None = None,
        logo_text: str = "Lexigram",
        logo_url: str = "",
        user_menu_items: list[dict] | None = None,
        system_menu_items: list[dict] | None = None,
        raw_user: Any | None = None,
        admin_prefix: str = "/admin",
        **props,
    ) -> None:
        # Standardize user as a dict for easier access
        user_dict = {}
        if user:
            if isinstance(user, dict):
                user_dict = user
            elif hasattr(user, "model_dump"):  # Pydantic v2
                user_dict = user.model_dump()
            elif hasattr(user, "dict"):  # Pydantic v1
                user_dict = user.dict()
            elif hasattr(user, "__dict__"):
                user_dict = user.__dict__
            else:
                # Fallback: try to convert via dict() or just store as is if it supports get
                try:
                    user_dict = dict(user)
                except (TypeError, ValueError):
                    pass
        super().__init__(
            items=items,
            user=user_dict,
            logo_text=logo_text,
            logo_url=logo_url,
            user_menu_items=user_menu_items,
            raw_user=raw_user,
            **props,
        )
        self.items = items
        self.user = user_dict
        self.logo_text = logo_text
        self.logo_url = logo_url
        self.user_menu_items = user_menu_items or []
        self.system_menu_items = system_menu_items or []
        self.raw_user = raw_user
        self.admin_prefix = admin_prefix.rstrip("/") or "/admin"

    def render(self) -> Any:
        from lexigram.ui import SystemBox

        # Logo Icon - Navigates to /admin dashboard
        if self.logo_url:
            logo_icon = el(
                "a",
                el(
                    "img",
                    src=self.logo_url,
                    alt=self.logo_text,
                    class_="w-10 h-10 rounded-xl object-contain flex-shrink-0",
                ),
                class_="block flex-shrink-0",
                href=self.admin_prefix,
            )
        else:
            logo_icon = el(
                "a",
                el("span", self.logo_text[0].upper(), class_="text-white"),
                class_="w-10 h-10 bg-primary-600 rounded-xl flex items-center justify-center shadow-lg shadow-primary-500/20 flex-shrink-0 cursor-pointer hover:bg-primary-700 transition-colors",
                href=self.admin_prefix,
            )

        # Toggle Button - chevron to collapse/expand sidebar
        from lexigram.ui import get_icon

        toggle_btn = el(
            "button",
            get_icon(
                "chevron-left",
                class_name="w-4 h-4 text-muted-foreground hover:text-muted-foreground dark:hover:text-foreground transition-colors",
            ),
            type="button",
            class_="p-1 rounded-full border border-border hover:bg-muted dark:hover:bg-card transition-colors focus:outline-none focus:ring-0",
            **{
                "x-on:click": "sidebarMini = !sidebarMini",
                "x-bind:class": "sidebarMini ? 'rotate-180' : ''",
                "aria-label": "Toggle sidebar",
            },
        )

        header = el(
            "div",
            # Icon Area
            logo_icon,
            # Text (Hidden in mini)
            el(
                "span",
                self.logo_text,
                class_="font-bold text-xl text-foreground tracking-tight ml-3 whitespace-nowrap",
                x_show="!sidebarMini",
            ),
            class_="p-4 flex items-center h-16 border-b border-border",
        )

        # Navigation Area
        nav = el(
            "nav",
            *self.items,
            class_="flex-1 px-3 py-4 space-y-1 overflow-y-auto custom-scrollbar",
            role="navigation",
            aria_label="Main navigation",
        )

        # Footer utilities. Account identity/actions live in the topbar so
        # this region stays reserved for persistent application utilities and
        # the sidebar affordance itself.
        system_menu_bar = SystemBox(
            system_menu_items=self.system_menu_items,
            direction="up",
            user=self.raw_user,
        )
        footer = el(
            "div",
            system_menu_bar,
            el(
                "div",
                toggle_btn,
                class_="flex items-center justify-end gap-1 px-2 py-2",
            ),
            class_="admin-sidebar-footer mt-auto border-t border-border dark:border-border",
        )

        return el(
            "aside",
            header,
            nav,
            footer,
            class_="admin-modern-sidebar relative flex flex-col h-full bg-card dark:bg-background border-r border-border transition-all duration-300 ease-in-out",
            **{"id": "main-sidebar", "x-bind:class": "sidebarMini ? 'w-24' : 'w-72'"},
            role="complementary",
            aria_label="Sidebar navigation",
        )
