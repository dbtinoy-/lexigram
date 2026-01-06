"""Fluent builder for admin navigation configuration."""

from __future__ import annotations

from lexigram.admin.navigation.types import NavGroup, NavigationConfig, NavItem


class NavigationBuilder:
    """Fluent builder for navigation configuration.

    Example:
        >>> nav = (NavigationBuilder()
        ...     .prefix("/admin")
        ...     .group("main", "Main Menu", icon="home", order=0)
        ...         .item("dashboard", "Dashboard", "/admin/dashboard", icon="chart-pie")
        ...         .item("users", "Users", "/admin/users", icon="users", resource="users")
        ...     .end_group()
        ...     .group("content", "Content", icon="document", order=1)
        ...         .item("posts", "Posts", "/admin/posts", resource="posts")
        ...     .end_group()
        ...     .build())
    """

    def __init__(self) -> None:
        self._prefix = "/admin"
        self._groups: dict[str, NavGroup] = {}
        self._current_group: str | None = None
        self._default_icons: dict[str, str] = {}

    def prefix(self, prefix: str) -> NavigationBuilder:
        """Set URL prefix."""
        self._prefix = prefix
        return self

    def default_icon(self, resource: str, icon: str) -> NavigationBuilder:
        """Set default icon for a resource type."""
        self._default_icons[resource] = icon
        return self

    def group(
        self,
        name: str,
        label: str,
        *,
        icon: str | None = None,
        order: int = 0,
        collapsible: bool = True,
        permission: str | None = None,
        feature_flag: str | None = None,
    ) -> NavigationBuilder:
        """Start a new navigation group."""
        self._groups[name] = NavGroup(
            name=name,
            label=label,
            icon=icon,
            order=order,
            collapsible=collapsible,
            permission=permission,
            feature_flag=feature_flag,
            items=[],
        )
        self._current_group = name
        return self

    def item(
        self,
        name: str,
        label: str,
        url: str,
        *,
        icon: str | None = None,
        badge: str | None = None,
        resource: str | None = None,
        permission: str | None = None,
        external: bool = False,
    ) -> NavigationBuilder:
        """Add an item to the current group."""
        if not self._current_group:
            raise ValueError("Must call group() before adding items")

        self._groups[self._current_group].items.append(
            NavItem(
                name=name,
                label=label,
                url=url,
                icon=icon,
                badge=badge,
                resource_name=resource,
                permission=permission,
                external=external,
            ),
        )
        return self

    def end_group(self) -> NavigationBuilder:
        """End the current group."""
        self._current_group = None
        return self

    def build(self) -> NavigationConfig:
        """Build the navigation configuration."""
        return NavigationConfig(
            prefix=self._prefix,
            groups=self._groups,
            default_icons=self._default_icons,
        )


__all__ = ["NavigationBuilder"]
