from __future__ import annotations

from typing import Any

from lexigram.admin.ui.organisms.command_palette import CommandPalette
from lexigram.admin.ui.organisms.sidebar import Sidebar
from lexigram.admin.ui.organisms.topbar import TopBar
from lexigram.admin.ui.templates.shell_scripts import (
    dark_mode_expr,
    loading_bar_script,
    search_overlay_markup,
)
from lexigram.admin.ui.templates.shell_sections import (
    build_impersonation_banner,
    build_main_area,
    build_root_data_attrs,
    build_sidebar_container,
    prepare_navigation,
)
from lexigram.ui import Component, InlineToast, Zones, el, raw, render_to_string


class AdminShell(Component):
    """
    Main responsive shell for Lexigram Admin.
    Stitches together the Sidebar, TopBar and content area.
    """

    def __init__(
        self,
        content: Any,
        title: str = "Admin",
        user: Any | None = None,
        nav_items: list | None = None,
        user_menu_items: list | None = None,
        system_menu_items: list | None = None,
        sidebar: Sidebar | None = None,
        topbar: TopBar | None = None,
        flash_messages: list[dict[str, str]] | None = None,
        breadcrumbs: list[dict[str, Any]] | None = None,
        commands: list[dict[str, str]] | None = None,
        features: dict[str, bool] | None = None,
        theme_css: str = "",
        site_name: str = "",
        logo_url: str = "",
        dark_mode: str = "",
        current_tenant_id: str | None = None,
        current_tenant_name: str = "",
        tenant_list: list[tuple[str, str]] | None = None,
        tenant_csrf_token: str | None = None,
        impersonation_active: bool = False,
        impersonation_target_id: str = "",
        csrf_token: str = "",
        admin_prefix: str = "/admin",
        **props: Any,
    ) -> None:
        super().__init__(**props)
        self.admin_prefix = admin_prefix.rstrip("/") or "/admin"
        self.content = content
        self.title = title
        self.user = user or {}
        self.commands = commands or []
        self.features = features or {}
        self.theme_css = theme_css
        self.site_name = site_name
        self.logo_url = logo_url
        self.dark_mode = dark_mode
        self.current_tenant_id = current_tenant_id
        self.current_tenant_name = current_tenant_name
        self.tenant_list = tenant_list or []
        self.tenant_csrf_token = tenant_csrf_token
        self.impersonation_active = impersonation_active
        self.impersonation_target_id = impersonation_target_id
        self.csrf_token = csrf_token

        # Standardize user as a dict for components
        self.user_dict = props.pop("user_dict", {})
        if not self.user_dict and user:
            if isinstance(user, dict):
                self.user_dict = user
            elif hasattr(user, "model_dump"):
                self.user_dict = user.model_dump()
            elif hasattr(user, "dict"):
                self.user_dict = user.dict()
            elif hasattr(user, "__dict__"):
                self.user_dict = user.__dict__

        self.nav_items = nav_items or []
        self.user_menu_items = user_menu_items or []
        self.system_menu_items = system_menu_items or []
        self.sidebar_instance = sidebar
        self.topbar_instance = topbar
        self.flash_messages = flash_messages or []
        if breadcrumbs is None:
            breadcrumbs = [
                {"label": "Home", "url": f"{self.admin_prefix}/"},
                {"label": title, "url": ""},
            ]
        self.breadcrumbs = breadcrumbs

    def _prepare_navigation(self) -> Any:
        """Transform raw nav_items into SidebarItem and SidebarSection instances."""
        return prepare_navigation(
            self.nav_items,
            self.features,
            self.user,
            admin_prefix=self.admin_prefix,
        )

    def render(self) -> Any:
        # 1. Prepare Sidebar
        sidebar = self.sidebar_instance
        if sidebar is None:
            items = self._prepare_navigation()
            sidebar = Sidebar(
                items=items,
                user=self.user_dict,
                user_menu_items=self.user_menu_items,
                system_menu_items=self.system_menu_items,
                raw_user=self.user,
                logo_url=self.logo_url,
            )

        # 2. Prepare TopBar
        topbar = self.topbar_instance
        if topbar is None:
            topbar = TopBar(
                title=self.title,
                site_name=self.site_name,
                user=self.user,
                user_menu_items=self.user_menu_items,
                current_tenant_id=self.current_tenant_id,
                current_tenant_name=self.current_tenant_name,
                tenant_list=self.tenant_list,
                tenant_csrf_token=self.tenant_csrf_token,
            )

        # 3. Theme styles (injected as inline style for runtime primary color)
        theme_style = (
            raw(f"<style id='admin-theme-css'>{self.theme_css}</style>")
            if self.theme_css
            else ""
        )

        search_overlay = search_overlay_markup()

        sidebar_html = raw(render_to_string(sidebar))
        topbar_html = raw(render_to_string(topbar))

        # Normalize content to an HTML string so the shell always exposes a
        # stable `#main-content` element (with constant classes) for HTMX
        # targets. Cluster centers render their sidebar inside the content
        # and own their layout.
        content_inner = raw(render_to_string(self.content))

        # 4. Handle Notifications (Toast)
        # We wrap in a container to allow OOB swaps
        toasts = ""
        for msg in self.flash_messages:
            toasts += render_to_string(
                InlineToast(
                    msg.get("message", ""), toast_type=msg.get("category", "info")
                ),
            )
        toast_node = raw(toasts) if toasts else ""

        flash_container = el("div", toast_node, id=Zones.FLASH.id)

        sidebar_container = build_sidebar_container(sidebar_html)

        impersonation_banner = build_impersonation_banner(
            self.impersonation_active,
            self.impersonation_target_id,
            self.csrf_token,
            admin_prefix=self.admin_prefix,
        )

        main_area = build_main_area(
            topbar_html,
            impersonation_banner,
            self.breadcrumbs,
            content_inner,
        )

        # Global HTMX loading indicator and error handling
        loading_bar = loading_bar_script(Zones.FLASH.id)

        dm_expr = dark_mode_expr(self.dark_mode)

        return el(
            "div",
            build_root_data_attrs(dm_expr),
            loading_bar,
            theme_style,
            search_overlay,
            sidebar_container,
            main_area,
            el("div", id="search-results"),
            flash_container,
            # Modal container for HTMX modals
            el("div", id=Zones.MODAL.id, class_="absolute z-[100]"),
            # Slide-over container for side panels
            el(
                "div",
                id=Zones.SLIDE_OVER.id,
                class_="fixed inset-0 z-[100] pointer-events-none",
            ),
            CommandPalette(commands=self.commands),
        )
