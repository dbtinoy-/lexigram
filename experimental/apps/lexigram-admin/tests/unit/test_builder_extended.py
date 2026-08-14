"""Tests for builders/builder.py — AdminBuilder fluent interface."""

from __future__ import annotations

import pytest

try:
    from lexigram.admin.builders.builder import AdminBuilder

    _BUILDER_AVAILABLE = True
except ImportError:
    _BUILDER_AVAILABLE = False

from lexigram.admin.config import AdminConfig, AdminNavigationGroup

pytestmark = pytest.mark.skipif(
    not _BUILDER_AVAILABLE,
    reason="AdminBuilder unavailable (lexigram.primitives.builder.BaseBuilder missing)",
)


class TestAdminBuilderCreate:
    """Tests for AdminBuilder.create() and default state."""

    def test_create_returns_builder(self) -> None:
        b = AdminBuilder.create()
        assert isinstance(b, AdminBuilder)

    def test_default_title(self) -> None:
        b = AdminBuilder()
        assert b._title == "Admin"

    def test_default_prefix(self) -> None:
        b = AdminBuilder()
        assert b._prefix == "/admin"

    def test_default_require_auth(self) -> None:
        b = AdminBuilder()
        assert b._require_auth is True

    def test_default_theme(self) -> None:
        b = AdminBuilder()
        assert b._theme == "system"

    def test_default_debug(self) -> None:
        b = AdminBuilder()
        assert b._debug is False


class TestAdminBuilderFluent:
    """Tests for AdminBuilder fluent setter methods."""

    def test_title_sets_and_returns_self(self) -> None:
        b = AdminBuilder()
        result = b.title("My Admin Panel")
        assert result is b
        assert b._title == "My Admin Panel"

    def test_prefix_sets_and_returns_self(self) -> None:
        b = AdminBuilder()
        result = b.prefix("/dashboard")
        assert result is b
        assert b._prefix == "/dashboard"

    def test_require_auth_false(self) -> None:
        b = AdminBuilder()
        result = b.require_auth(False)
        assert result is b
        assert b._require_auth is False

    def test_theme_light(self) -> None:
        b = AdminBuilder()
        result = b.theme("light")
        assert result is b
        assert b._theme == "light"

    def test_theme_dark(self) -> None:
        b = AdminBuilder()
        b.theme("dark")
        assert b._theme == "dark"

    def test_debug_enabled(self) -> None:
        b = AdminBuilder()
        result = b.debug()
        assert result is b
        assert b._debug is True

    def test_debug_explicit_false(self) -> None:
        b = AdminBuilder()
        b.debug(True)
        result = b.debug(False)
        assert result is b
        assert b._debug is False

    def test_features_updates_dict(self) -> None:
        b = AdminBuilder()
        result = b.features({"bulk_actions": True, "export": False})
        assert result is b
        assert b._features["bulk_actions"] is True
        assert b._features["export"] is False

    def test_feature_single(self) -> None:
        b = AdminBuilder()
        result = b.feature("dark_mode", True)
        assert result is b
        assert b._features["dark_mode"] is True

    def test_feature_default_enabled(self) -> None:
        b = AdminBuilder()
        b.feature("audit_log")
        assert b._features["audit_log"] is True

    def test_extension(self) -> None:
        b = AdminBuilder()
        result = b.extension("charts", enabled=True, theme="dark")
        assert result is b
        assert b._extensions["charts"]["enabled"] is True
        assert b._extensions["charts"]["theme"] == "dark"

    def test_resources_extend(self) -> None:
        b = AdminBuilder()
        result = b.resources(["UserResource", "PostResource"])
        assert result is b
        assert "UserResource" in b._resources
        assert "PostResource" in b._resources

    def test_resource_appends(self) -> None:
        b = AdminBuilder()
        result = b.resource("CommentResource")
        assert result is b
        assert ("CommentResource", None, None) in b._resources

    def test_controller_appends(self) -> None:
        b = AdminBuilder()
        result = b.controller("MyController")
        assert result is b
        assert "MyController" in b._controllers

    def test_navigation_groups_updates(self) -> None:
        b = AdminBuilder()
        group = AdminNavigationGroup(label="Content", icon="folder")
        result = b.navigation_groups({"content": group})
        assert result is b
        assert "content" in b._navigation_groups

    def test_navigation_group_single(self) -> None:
        b = AdminBuilder()
        group = AdminNavigationGroup(label="Settings", icon="gear")
        result = b.navigation_group("settings", group)
        assert result is b
        assert b._navigation_groups["settings"] is group

    def test_commands_extend(self) -> None:
        b = AdminBuilder()
        result = b.commands([{"label": "Export", "href": "/export"}])
        assert result is b
        assert len(b._commands) == 1

    def test_command_appends(self) -> None:
        b = AdminBuilder()
        result = b.command("Export", "/export", icon="download", shortcut="E")
        assert result is b
        cmd = b._commands[0]
        assert cmd["label"] == "Export"
        assert cmd["href"] == "/export"
        assert cmd["icon"] == "download"
        assert cmd["shortcut"] == "E"

    def test_command_defaults(self) -> None:
        b = AdminBuilder()
        b.command("Home", "/")
        cmd = b._commands[0]
        assert cmd["icon"] == ""
        assert cmd["shortcut"] == ""

    def test_service_registers_factory(self) -> None:
        b = AdminBuilder()
        factory = lambda: "service_instance"  # noqa: E731
        result = b.service(str, factory)
        assert result is b
        assert b._service_factories[str] is factory

    def test_chaining(self) -> None:
        b = (
            AdminBuilder.create()
            .title("Test Admin")
            .prefix("/test")
            .require_auth(False)
            .debug()
            .feature("charts")
        )
        assert b._title == "Test Admin"
        assert b._prefix == "/test"
        assert b._require_auth is False
        assert b._debug is True
        assert b._features["charts"] is True


class TestAdminBuilderFromConfig:
    """Tests for AdminBuilder.from_config()."""

    def test_from_config_copies_title(self) -> None:
        config = AdminConfig(title="My App Admin")
        b = AdminBuilder.from_config(config)
        assert b._title == "My App Admin"

    def test_from_config_copies_prefix(self) -> None:
        config = AdminConfig(prefix="/control")
        b = AdminBuilder.from_config(config)
        assert b._prefix == "/control"

    def test_from_config_copies_debug(self) -> None:
        config = AdminConfig(debug=True)
        b = AdminBuilder.from_config(config)
        assert b._debug is True

    def test_from_config_copies_require_auth(self) -> None:
        config = AdminConfig(require_auth=False)
        b = AdminBuilder.from_config(config)
        assert b._require_auth is False

    def test_from_config_stores_base_config(self) -> None:
        config = AdminConfig()
        b = AdminBuilder.from_config(config)
        assert b._base_config is config
