"""Tests for admin types."""

import pytest
from lexigram.admin.types import (
    AdminStatus,
    AdminUser,
    ExtensionConfig,
    MiddlewareOptions,
    NavigationItem,
    TemplateContext,
)


class TestAdminStatus:
    """Tests for AdminStatus enum."""

    def test_pending(self) -> None:
        assert AdminStatus.PENDING.value == "pending"

    def test_active(self) -> None:
        assert AdminStatus.ACTIVE.value == "active"

    def test_inactive(self) -> None:
        assert AdminStatus.INACTIVE.value == "inactive"

    def test_enum_is_str(self) -> None:
        assert isinstance(AdminStatus.PENDING, str)

    def test_all_values(self) -> None:
        values = {s.value for s in AdminStatus}
        assert values == {"pending", "active", "inactive"}


class TestExtensionConfig:
    """Tests for ExtensionConfig dataclass."""

    def test_defaults(self) -> None:
        config = ExtensionConfig()
        assert config.enabled is True
        assert config.nav_label is None
        assert config.nav_icon is None
        assert config.nav_location == "sidebar"
        assert config.nav_order == 100
        assert config.nav_permission is None
        assert config.options == {}

    def test_custom_values(self) -> None:
        config = ExtensionConfig(
            enabled=False,
            nav_label="Custom",
            nav_icon="icon",
            nav_location="top_nav",
            nav_order=50,
            nav_permission="admin",
            options={"key": "value"},
        )
        assert config.enabled is False
        assert config.nav_label == "Custom"
        assert config.nav_icon == "icon"
        assert config.nav_location == "top_nav"
        assert config.nav_order == 50
        assert config.nav_permission == "admin"
        assert config.options == {"key": "value"}


class TestAdminUser:
    """Tests for AdminUser dataclass."""

    def test_required_fields(self) -> None:
        user = AdminUser(id="1", username="admin", email="admin@test.com")
        assert user.id == "1"
        assert user.username == "admin"
        assert user.email == "admin@test.com"
        assert user.roles == []
        assert user.permissions == []

    def test_with_roles_and_permissions(self) -> None:
        user = AdminUser(
            id="2",
            username="user",
            email="user@test.com",
            roles=["editor"],
            permissions=["view", "edit"],
        )
        assert user.roles == ["editor"]
        assert user.permissions == ["view", "edit"]


class TestNavigationItem:
    """Tests for NavigationItem TypedDict."""

    def test_minimal_item(self) -> None:
        item: NavigationItem = {"label": "Home", "url": "/", "icon": "home"}
        assert item["label"] == "Home"
        assert item["url"] == "/"

    def test_full_item(self) -> None:
        item: NavigationItem = {
            "label": "Settings",
            "url": "/settings",
            "icon": "cog",
            "group": "System",
            "permission": "admin",
            "children": [],
            "active": False,
        }
        assert item["group"] == "System"
        assert item["active"] is False


class TestMiddlewareOptions:
    """Tests for MiddlewareOptions TypedDict."""

    def test_partial_options(self) -> None:
        opts: MiddlewareOptions = {"debug": True}
        assert opts["debug"] is True

    def test_full_options(self) -> None:
        opts: MiddlewareOptions = {
            "debug": False,
            "timeout": 30.0,
            "exclude_paths": ["/health", "/metrics"],
        }
        assert opts["timeout"] == 30.0
        assert len(opts["exclude_paths"]) == 2


class TestTemplateContext:
    """Tests for TemplateContext TypedDict."""

    def test_minimal_context(self) -> None:
        ctx: TemplateContext = {"title": "Page", "content": "Hello"}
        assert ctx["title"] == "Page"

    def test_full_context(self) -> None:
        ctx: TemplateContext = {
            "title": "Admin",
            "user": object(),
            "nav_items": [],
            "breadcrumbs": [{"label": "Home", "url": "/"}],
            "request": object(),
            "content": "<p>Content</p>",
            "error": None,
            "flash": "Success",
        }
        assert ctx["breadcrumbs"][0]["label"] == "Home"
        assert ctx["error"] is None
        assert ctx["flash"] == "Success"
