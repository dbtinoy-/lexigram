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
        csrf_token: Optional token for the plain-form POST.
        **props: Extra HTML attributes forwarded to the wrapper element.
    """

    def __init__(
        self,
        locales: list[tuple[str, str]] | None = None,
        current_locale: str = "en",
        action_url: str = "/admin/set-locale",
        csrf_token: str | None = None,
        **props: Any,
    ) -> None:
        super().__init__(**props)
        self.locales = locales or [("en", "English")]
        self.current_locale = current_locale
        self.action_url = action_url
        self.csrf_token = csrf_token

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
        children: list[Any] = [select]
        if self.csrf_token:
            children.append(
                el(
                    "input",
                    type_="hidden",
                    name="csrf_token",
                    value=self.csrf_token,
                )
            )
        return el(
            "form",
            *children,
            method="POST",
            action=self.action_url,
            class_="inline-block",
        )


class TenantSwitcher(Component):
    """Superadmin-only tenant switcher for the admin topbar.

    Mirrors ``LanguageSwitcher``'s plain ``<select>``-in-``<form>``
    auto-submit shape (there is no dropdown-menu precedent in this file
    to follow instead). Renders nothing when *tenants* is empty — callers
    (``TopBar``) are responsible for only constructing this with data
    when tenancy is enabled and the requesting user is a superadmin; an
    empty list is what makes this a no-op in every other case.

    Unlike ``LanguageSwitcher``, this form carries a CSRF hidden field:
    it is a genuine plain-form POST (not HTMX), so the shell's
    ``hx-headers`` CSRF injection does not apply, and
    ``request.state.csrf_token`` is not reliably populated on the pages
    this switcher appears on (see plan header for details).

    Args:
        tenants: Ordered list of ``(tenant_id, name)`` pairs.
        current_tenant_id: The currently active tenant id, pre-selected.
        csrf_token: CSRF token embedded as a hidden form field, if given.
        action_url: URL that accepts a ``POST`` with ``tenant_id=<id>``.
    """

    def __init__(
        self,
        tenants: list[tuple[str, str]] | None = None,
        current_tenant_id: str | None = None,
        csrf_token: str | None = None,
        action_url: str = "/admin/set-tenant",
        **props: Any,
    ) -> None:
        super().__init__(**props)
        self.tenants = tenants or []
        self.current_tenant_id = current_tenant_id
        self.csrf_token = csrf_token
        self.action_url = action_url

    def render(self) -> Any:
        if not self.tenants:
            return ""
        options = [
            el(
                "option",
                name,
                value=tenant_id,
                selected=(tenant_id == self.current_tenant_id) or None,
            )
            for tenant_id, name in self.tenants
        ]
        current_name = next(
            (name for tid, name in self.tenants if tid == self.current_tenant_id),
            None,
        )
        # Switching tenant changes which organisation's data every
        # subsequent page edits, so the control must say what it does. An
        # unlabelled select in the topbar is announced only as its selected
        # value, which is indistinguishable from a language or theme picker.
        select = el(
            "select",
            *options,
            id="admin-tenant-switcher",
            name="tenant_id",
            class_=(
                "text-sm bg-transparent border border-border "
                "rounded px-2 py-1 text-foreground "
                "focus:outline-none focus:ring-2 focus:ring-ring cursor-pointer"
            ),
            **{
                "x-on:change": "$el.form.submit()",
                "aria-label": "Active tenant",
                "aria-describedby": "admin-tenant-switcher-hint",
            },
        )
        children: list[Any] = [
            el(
                "label",
                "Tenant",
                for_="admin-tenant-switcher",
                class_="sr-only",
            ),
            select,
            el(
                "span",
                (
                    f"Currently viewing {current_name}. "
                    "Changing this switches the active tenant."
                    if current_name
                    else "Changing this switches the active tenant."
                ),
                id="admin-tenant-switcher-hint",
                class_="sr-only",
            ),
        ]
        if self.csrf_token:
            children.append(
                el(
                    "input",
                    type_="hidden",
                    name="csrf_token",
                    value=self.csrf_token,
                )
            )
        # Auto-submit is a JS enhancement. Without this fallback a scripting
        # failure leaves the select silently inert: it looks changed but the
        # tenant never switches, so the operator believes they are working
        # in a tenant they are not. The button is present by default and
        # hidden by CSS only once scripting is confirmed available, so the
        # no-JS path degrades to an ordinary form submit.
        children.append(
            el(
                "button",
                "Switch",
                type="submit",
                class_=(
                    "tenant-switch-fallback ml-1 text-xs px-2 py-1 rounded "
                    "border border-border text-foreground hover:bg-muted "
                    "focus-visible:outline-none focus-visible:ring-2 "
                    "focus-visible:ring-ring"
                ),
            )
        )
        return el(
            "form",
            *children,
            method="POST",
            action=self.action_url,
            class_="inline-flex items-center",
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
        current_tenant_id: str | None = None,
        current_tenant_name: str = "",
        tenant_list: list[tuple[str, str]] | None = None,
        tenant_csrf_token: str | None = None,
        csrf_token: str | None = None,
        admin_prefix: str = "/admin",
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
        self.current_tenant_id = current_tenant_id
        self.current_tenant_name = current_tenant_name
        self.tenant_list = tenant_list or []
        self.tenant_csrf_token = tenant_csrf_token
        self.csrf_token = csrf_token
        self.admin_prefix = admin_prefix.rstrip("/") or "/admin"

    @staticmethod
    def _user_value(user: Any, *keys: str, default: Any = None) -> Any:
        """Read a user value from dict- or protocol-shaped user objects."""
        for key in keys:
            if isinstance(user, dict):
                value = user.get(key)
            else:
                value = getattr(user, key, None)
            if value not in (None, ""):
                return value
        return default

    def _render_user_menu(self) -> Any:
        """Render the personal account control for the topbar."""
        if not self.user:
            return ""

        from lexigram.ui import UserBox

        username = str(
            self._user_value(self.user, "name", "username", default="Admin") or "Admin"
        )
        roles = self._user_value(self.user, "roles", default=[])
        if isinstance(roles, str):
            roles = [roles]
        if not isinstance(roles, list):
            roles = list(roles or [])

        return el(
            "div",
            UserBox(
                username,
                avatar_url=self._user_value(
                    self.user,
                    "avatar_url",
                    "avatar",
                ),
                direction="down",
                position="right",
                roles=roles,
                user_menu_items=self.user_menu_items or [],
                user=self.user,
                logout_url=f"{self.admin_prefix}/logout",
                variant="topbar",
                collapse_var=None,
            ),
            class_="admin-topbar-user shrink-0",
        )

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
                    "aria-label": "Open navigation",
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

        # Default Right: TenantSwitcher (superadmin only) + NotificationBell +
        # ThemeToggle + account menu. Application destinations stay in the
        # sidebar; the account control is reserved for personal actions.
        right_node = self.right
        if right_node is None:
            from lexigram.ui import NotificationBell

            right_elements: list[Any] = []
            if self.current_tenant_id is not None:
                right_elements.append(
                    TenantSwitcher(
                        tenants=self.tenant_list,
                        current_tenant_id=self.current_tenant_id,
                        csrf_token=self.tenant_csrf_token,
                        action_url=f"{self.admin_prefix}/set-tenant",
                    )
                )
            right_elements.append(
                NotificationBell(
                    inbox_url=f"{self.admin_prefix}/notifications",
                    inbox_api_url=f"{self.admin_prefix}/notifications/inbox",
                    mark_read_url=f"{self.admin_prefix}/notifications/read/{{message_id}}",
                    mark_all_read_url=f"{self.admin_prefix}/notifications/read-all",
                    sse_url=f"{self.admin_prefix}/_sse/widgets",
                    csrf_token=self.csrf_token,
                ).render()
            )
            right_elements.append(ThemeToggle())
            account_menu = self._render_user_menu()
            if account_menu:
                right_elements.append(account_menu)
            right_node = el(
                "div",
                *right_elements,
                class_="admin-topbar-actions flex items-center space-x-3",
            )

        center_node = self.center or ""
        if not center_node:
            center_node = el(
                "div",
                el(
                    "button",
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
                        aria_hidden="true",
                        focusable="false",
                    ),
                    el(
                        "span",
                        "Search (Cmd+K)",
                        class_="ml-3 text-muted-foreground text-sm hidden sm:block",
                    ),
                    type="button",
                    aria_label="Open command palette",
                    class_="admin-command-trigger flex items-center w-full max-w-md px-4 py-2 bg-muted rounded-lg cursor-pointer hover:bg-muted/80 transition-colors",
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
            class_="admin-topbar bg-background/80 backdrop-blur-md border-b border-border sticky top-0 z-20 shadow-sm transition-colors duration-300",
        )
