"""Header component for admin layout.

Renders the top header bar with logo, search, notifications, and user menu.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from markupsafe import escape


@dataclass
class HeaderConfig:
    """Configuration for header."""

    # Branding
    site_name: str = "Admin"
    logo_url: str | None = None
    logo_alt: str = "Logo"

    # Features
    show_search: bool = True
    show_notifications: bool = True
    show_user_menu: bool = True
    show_theme_toggle: bool = True

    # Search
    search_placeholder: str = "Search..."
    search_url: str = "/admin/search"
    search_hotkey: str = "/"

    # URLs
    home_url: str = "/admin/"
    profile_url: str = "/admin/profile"
    settings_url: str = "/admin/settings"
    logout_url: str = "/admin/logout"

    # Custom
    extra_items: list[dict[str, str]] = field(default_factory=list)


@dataclass
class UserInfo:
    """User information for header."""

    name: str = "User"
    email: str = ""
    avatar_url: str | None = None
    role: str | None = None


class HeaderRenderer:
    """Renders the admin header bar."""

    def __init__(
        self,
        config: HeaderConfig | None = None,
        user: UserInfo | None = None,
    ):
        """Initialize the renderer.

        Args:
            config: Header configuration
            user: Current user info
        """
        self.config = config or HeaderConfig()
        self.user = user

    def render(
        self,
        notifications: list[dict[str, Any]] | None = None,
        unread_count: int = 0,
    ) -> str:
        """Render the header bar.

        Args:
            notifications: List of notification dicts
            unread_count: Count of unread notifications

        Returns:
            HTML string for header
        """
        parts: list[str] = []

        parts.append('<header class="admin-header">')

        # Left section (logo, mobile menu toggle)
        parts.append(self._render_left_section())

        # Center section (search)
        if self.config.show_search:
            parts.append(self._render_search())

        # Right section (notifications, user menu)
        parts.append(self._render_right_section(notifications, unread_count))

        parts.append("</header>")

        return "\n".join(parts)

    def _render_left_section(self) -> str:
        """Render left section with logo."""
        parts: list[str] = []

        parts.append('<div class="header-left">')

        # Mobile menu toggle
        parts.append("""
            <button type="button" class="mobile-menu-btn lg:hidden"
                    onclick="document.body.classList.toggle('sidebar-open')">
                <i data-lucide="menu" class="w-5 h-5"></i>
            </button>
        """)

        # Logo
        parts.append(f'<a href="{escape(self.config.home_url)}" class="header-logo">')
        if self.config.logo_url:
            parts.append(
                f'<img src="{escape(self.config.logo_url)}" alt="{escape(self.config.logo_alt)}" class="h-8">',
            )
        else:
            parts.append(
                f'<span class="font-bold text-xl">{escape(self.config.site_name)}</span>',
            )
        parts.append("</a>")

        parts.append("</div>")

        return "\n".join(parts)

    def _render_search(self) -> str:
        """Render search box."""
        return f"""
        <div class="header-search">
            <div class="relative">
                <input type="search"
                       name="q"
                       placeholder="{escape(self.config.search_placeholder)}"
                       class="search-input"
                       hx-get="{escape(self.config.search_url)}"
                       hx-trigger="keyup changed delay:300ms"
                       hx-target="#search-results"
                       autocomplete="off">
                <div class="search-icon">
                    <i data-lucide="search" class="w-4 h-4"></i>
                </div>
                <kbd class="search-shortcut hidden sm:block">{escape(self.config.search_hotkey)}</kbd>
            </div>
            </div>
        </div>
        """

    def _render_right_section(
        self,
        notifications: list[dict[str, Any]] | None,
        unread_count: int,
    ) -> str:
        """Render right section with notifications and user menu."""
        parts: list[str] = []

        parts.append('<div class="header-right">')

        # Theme toggle
        if self.config.show_theme_toggle:
            parts.append(self._render_theme_toggle())

        # Notifications
        if self.config.show_notifications:
            parts.append(self._render_notifications(notifications, unread_count))

        # User menu
        if self.config.show_user_menu and self.user:
            parts.append(self._render_user_menu())

        parts.append("</div>")

        return "\n".join(parts)

    def _render_theme_toggle(self) -> str:
        """Render theme toggle button."""
        return """
        <button type="button" class="theme-toggle-btn"
                onclick="toggleTheme()"
                title="Toggle theme">
            <i data-lucide="sun" class="w-5 h-5 dark:hidden"></i>
            <i data-lucide="moon" class="w-5 h-5 hidden dark:block"></i>
        </button>
        """

    def _render_notifications(
        self,
        notifications: list[dict[str, Any]] | None,
        unread_count: int,
    ) -> str:
        """Render notifications dropdown."""
        badge = ""
        if unread_count > 0:
            badge = f'<span class="notification-badge">{unread_count}</span>'

        items = ""
        if notifications:
            for n in notifications[:5]:
                items += f"""
                <a href="{escape(n.get("url", "#"))}" class="notification-item">
                    <span class="notification-title">{escape(n.get("title", ""))}</span>
                    <span class="notification-time">{escape(n.get("time", ""))}</span>
                </a>
                """
        else:
            items = '<p class="notification-empty">No new notifications</p>'

        return f"""
        <div class="notifications-dropdown" x-data="{{open: false}}">
            <button type="button" @click="open = !open" class="notification-btn">
                <i data-lucide="bell" class="w-5 h-5"></i>
                {badge}
            </button>
            <div x-show="open" @click.away="open = false" class="notifications-panel">
                <div class="notifications-header">Notifications</div>
                <div class="notifications-list">
                    {items}
                </div>
                <a href="/admin/notifications" class="notifications-footer">View all</a>
            </div>
        </div>
        """

    def _render_user_menu(self) -> str:
        """Render user dropdown menu."""
        if not self.user:
            return ""

        avatar = ""
        if self.user.avatar_url:
            avatar = (
                f'<img src="{escape(self.user.avatar_url)}" alt="" class="user-avatar">'
            )
        else:
            initial = self.user.name[0].upper() if self.user.name else "U"
            avatar = f'<span class="user-avatar-placeholder">{escape(initial)}</span>'

        role_badge = ""
        if self.user.role:
            role_badge = (
                f'<span class="user-role-badge">{escape(self.user.role)}</span>'
            )

        return f"""
        <div class="user-dropdown" x-data="{{open: false}}">
            <button type="button" @click="open = !open" class="user-btn">
                {avatar}
                <span class="user-name hidden md:block">{escape(self.user.name)}</span>
                <i data-lucide="chevron-down" class="w-4 h-4 hidden md:block"></i>
            </button>
            <div x-show="open" @click.away="open = false" class="user-panel">
                <div class="user-info">
                    <div class="font-medium">{escape(self.user.name)}</div>
                    <div class="text-sm text-gray-500">{escape(self.user.email)}</div>
                    {role_badge}
                </div>
                <div class="user-menu-items">
                    <a href="{escape(self.config.profile_url)}" class="user-menu-item">
                        <i data-lucide="user" class="w-4 h-4"></i> Profile
                    </a>
                    <a href="{escape(self.config.settings_url)}" class="user-menu-item">
                        <i data-lucide="settings" class="w-4 h-4"></i> Settings
                    </a>
                    <hr class="my-1">
                    <a href="{escape(self.config.logout_url)}" class="user-menu-item text-red-600">
                        <i data-lucide="log-out" class="w-4 h-4"></i> Logout
                    </a>
                </div>
            </div>
        </div>
        """


__all__ = ["HeaderConfig", "HeaderRenderer", "UserInfo"]
