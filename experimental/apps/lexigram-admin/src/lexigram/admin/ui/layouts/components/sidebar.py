"""Sidebar navigation component for admin layout.

Renders the sidebar with navigation items, groups, and collapse functionality.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from markupsafe import escape


@dataclass
class NavItem:
    """Single navigation item."""

    label: str
    url: str
    icon: str = "circle"
    badge: str | None = None
    badge_color: str = "blue"
    is_active: bool = False
    is_disabled: bool = False
    target: str = "_self"
    hx_attrs: dict[str, str] = field(default_factory=dict)
    children: list[NavItem] = field(default_factory=list)


@dataclass
class NavGroup:
    """Navigation group with optional header."""

    label: str | None = None
    items: list[NavItem] = field(default_factory=list)
    is_collapsible: bool = False
    is_collapsed: bool = False


@dataclass
class SidebarConfig:
    """Configuration for sidebar."""

    # Display
    width: str = "260px"
    collapsed_width: str = "64px"
    is_collapsible: bool = True
    default_collapsed: bool = False

    # Features
    show_footer: bool = True
    footer_text: str = ""

    # Styling
    bg_class: str = "bg-background"
    text_class: str = "text-foreground"

    # Branding (optional, if not in header)
    show_logo: bool = False
    logo_url: str | None = None
    site_name: str = "Admin"


class SidebarRenderer:
    """Renders the sidebar navigation."""

    def __init__(
        self,
        config: SidebarConfig | None = None,
        groups: list[NavGroup] | None = None,
    ):
        """Initialize the renderer.

        Args:
            config: Sidebar configuration
            groups: Navigation groups
        """
        self.config = config or SidebarConfig()
        self.groups = groups or []

    def render(self, current_path: str = "/") -> str:
        """Render the sidebar.

        Args:
            current_path: Current request path for highlighting active item

        Returns:
            HTML string for sidebar
        """
        parts: list[str] = []

        collapsed_class = "sidebar-collapsed" if self.config.default_collapsed else ""

        parts.append(
            f'<aside class="admin-sidebar {collapsed_class}" id="admin-sidebar">',
        )

        # Mobile overlay
        parts.append(
            '<div class="sidebar-overlay lg:hidden" onclick="closeSidebar()"></div>',
        )

        # Sidebar content wrapper
        parts.append('<div class="sidebar-content">')

        # Optional logo section
        if self.config.show_logo:
            parts.append(self._render_logo())

        # Navigation
        parts.append('<nav class="sidebar-nav">')
        for group in self.groups:
            parts.append(self._render_nav_group(group, current_path))
        parts.append("</nav>")

        # Collapse toggle
        if self.config.is_collapsible:
            parts.append(self._render_collapse_toggle())

        # Footer
        if self.config.show_footer and self.config.footer_text:
            parts.append(self._render_footer())

        parts.append("</div>")  # sidebar-content
        parts.append("</aside>")

        return "\n".join(parts)

    def _render_logo(self) -> str:
        """Render sidebar logo section."""
        parts: list[str] = []

        parts.append('<div class="sidebar-logo">')

        if self.config.logo_url:
            parts.append(
                f'<img src="{escape(self.config.logo_url)}" alt="{escape(self.config.site_name)}" class="sidebar-logo-img">',
            )
        else:
            parts.append(
                f'<span class="sidebar-logo-text">{escape(self.config.site_name)}</span>',
            )

        parts.append("</div>")

        return "\n".join(parts)

    def _render_nav_group(self, group: NavGroup, current_path: str) -> str:
        """Render a navigation group."""
        parts: list[str] = []

        collapsed_class = "is-collapsed" if group.is_collapsed else ""
        parts.append(f'<div class="nav-group {collapsed_class}">')

        # Group header
        if group.label:
            if group.is_collapsible:
                parts.append(f"""
                <button type="button" class="nav-group-header nav-group-toggle"
                        onclick="this.parentElement.classList.toggle('is-collapsed')">
                    <span>{escape(group.label)}</span>
                    <i data-lucide="chevron-down" class="nav-group-arrow w-4 h-4"></i>
                </button>
                """)
            else:
                parts.append(
                    f'<div class="nav-group-header">{escape(group.label)}</div>',
                )

        # Group items
        parts.append('<ul class="nav-group-items">')
        for item in group.items:
            parts.append(self._render_nav_item(item, current_path))
        parts.append("</ul>")

        parts.append("</div>")

        return "\n".join(parts)

    def _render_nav_item(self, item: NavItem, current_path: str, level: int = 0) -> str:
        """Render a single navigation item."""
        # Check if active
        is_active = (
            item.is_active
            or current_path == item.url
            or current_path.startswith(item.url + "/")
        )

        # Check if has active child
        has_active_child = any(
            current_path == child.url or current_path.startswith(child.url + "/")
            for child in item.children
        )

        active_class = "is-active" if is_active else ""
        disabled_class = "is-disabled" if item.is_disabled else ""
        has_children_class = "has-children" if item.children else ""
        expanded_class = "is-expanded" if has_active_child else ""
        level_class = f"nav-level-{level}"

        # Build hx-* attributes
        hx_attrs_str = ""
        for key, value in item.hx_attrs.items():
            hx_attrs_str += f' hx-{escape(key)}="{escape(value)}"'

        # Badge
        badge = ""
        if item.badge:
            badge = f'<span class="nav-badge badge-{escape(item.badge_color)}">{escape(item.badge)}</span>'

        parts: list[str] = []
        parts.append(
            f'<li class="nav-item {active_class} {disabled_class} {has_children_class} {expanded_class} {level_class}">',
        )

        if item.children:
            # Has submenu
            parts.append(f"""
            <button type="button" class="nav-link nav-link-toggle"
                    onclick="this.parentElement.classList.toggle('is-expanded')">
                <i data-lucide="{escape(item.icon)}" class="nav-icon w-5 h-5"></i>
                <span class="nav-label">{escape(item.label)}</span>
                {badge}
                <i data-lucide="chevron-right" class="nav-arrow w-4 h-4"></i>
            </button>
            """)

            # Submenu
            parts.append('<ul class="nav-submenu">')
            for child in item.children:
                parts.append(self._render_nav_item(child, current_path, level + 1))
            parts.append("</ul>")
        else:
            # Regular link
            parts.append(f"""
            <a href="{escape(item.url)}"
               class="nav-link"
               target="{escape(item.target)}"
               {hx_attrs_str}>
                <i data-lucide="{escape(item.icon)}" class="nav-icon w-5 h-5"></i>
                <span class="nav-label">{escape(item.label)}</span>
                {badge}
            </a>
            """)

        parts.append("</li>")

        return "\n".join(parts)

    def _render_collapse_toggle(self) -> str:
        """Render sidebar collapse toggle button."""
        return """
        <button type="button" class="sidebar-collapse-btn"
                onclick="toggleSidebar()"
                title="Toggle sidebar">
            <i data-lucide="panel-left-close" class="w-5 h-5 sidebar-expanded-icon"></i>
            <i data-lucide="panel-left-open" class="w-5 h-5 sidebar-collapsed-icon"></i>
        </button>
        """

    def _render_footer(self) -> str:
        """Render sidebar footer."""
        return f"""
        <div class="sidebar-footer">
            {self.config.footer_text}
        </div>
        """


def build_nav_from_resources(
    resources: list[Any],
    current_path: str = "/",
    base_url: str = "/admin",
) -> list[NavGroup]:
    """Build navigation groups from resource configuration.

    Args:
        resources: List of resource instances or configs
        current_path: Current path for active highlighting
        base_url: Base URL prefix

    Returns:
        List of NavGroup for sidebar
    """
    # Group items by category
    categories: dict[str, list[NavItem]] = {}

    for resource in resources:
        # Extract resource info
        name = getattr(resource, "name", str(resource))
        label = getattr(resource, "label", name.replace("_", " ").title())
        icon = getattr(resource, "icon", "file")
        category = getattr(resource, "category", "General")
        url = f"{base_url}/{name}"

        item = NavItem(
            label=label,
            url=url,
            icon=icon,
            is_active=current_path.startswith(url),
        )

        if category not in categories:
            categories[category] = []
        categories[category].append(item)

    # Convert to groups
    groups: list[NavGroup] = []
    for category_name, items in categories.items():
        groups.append(
            NavGroup(
                label=category_name,
                items=items,
                is_collapsible=True,
            ),
        )

    return groups


__all__ = [
    "NavGroup",
    "NavItem",
    "SidebarConfig",
    "SidebarRenderer",
    "build_nav_from_resources",
]
