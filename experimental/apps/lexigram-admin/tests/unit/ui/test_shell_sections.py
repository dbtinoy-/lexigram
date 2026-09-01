"""Unit tests for shell section builders (nav preparation, impersonation)."""

from __future__ import annotations

from lexigram.admin.auth.integration import AdminUser
from lexigram.admin.ui.templates.shell_sections import (
    _user_has_permission,
    build_impersonation_banner,
    prepare_navigation,
)
from lexigram.ui import render_to_string


class TestUserHasPermission:
    def test_admin_user_exact_permission(self) -> None:
        user = AdminUser(
            id=1, email="a@example.com", name="A", permissions={"users.read"}
        )
        assert _user_has_permission(user, "users.read") is True
        assert _user_has_permission(user, "users.delete") is False

    def test_admin_user_superuser_passes_all(self) -> None:
        user = AdminUser(
            id=1,
            email="a@example.com",
            name="A",
            is_superuser=True,
            permissions=set(),
        )
        assert _user_has_permission(user, "anything.read") is True

    def test_dict_with_permissions(self) -> None:
        assert _user_has_permission({"permissions": ["users.read"]}, "users.read")
        assert _user_has_permission({"permissions": ["*"]}, "users.read")

    def test_null_user_denies(self) -> None:
        assert _user_has_permission(None, "users.read") is False
        assert _user_has_permission({}, "users.read") is False


class TestPrepareNavigation:
    def test_infers_resource_permission_from_href(self) -> None:
        items = [{"label": "Users", "href": "/admin/users"}]
        user = AdminUser(
            id=1, email="a@example.com", name="A", permissions={"users.read"}
        )
        prepared = prepare_navigation(items, {}, user)
        assert len(prepared) == 1

        restricted = AdminUser(
            id=2, email="b@example.com", name="B", permissions=set()
        )
        assert prepare_navigation(items, {}, restricted) == []

    def test_inference_respects_custom_prefix(self) -> None:
        items = [{"label": "Users", "href": "/console/users"}]
        user = AdminUser(
            id=1, email="a@example.com", name="A", permissions={"users.read"}
        )
        prepared = prepare_navigation(items, {}, user, admin_prefix="/console")
        assert len(prepared) == 1

    def test_custom_prefix_href_not_matched_by_default_prefix(self) -> None:
        items = [{"label": "Users", "href": "/console/users"}]
        user = AdminUser(id=1, email="a@example.com", name="A", permissions=set())
        # Prefix mismatch → no permission inferred → item kept.
        prepared = prepare_navigation(items, {}, user, admin_prefix="/admin")
        assert len(prepared) == 1

    def test_explicit_permission_still_hides_when_missing(self) -> None:
        items = [
            {
                "label": "Settings",
                "href": "/admin/settings",
                "permission": "settings.read",
            }
        ]
        user = AdminUser(id=1, email="a@example.com", name="A", permissions=set())
        assert prepare_navigation(items, {}, user) == []


class TestImpersonationBanner:
    def test_banner_uses_configured_prefix(self) -> None:
        banner = build_impersonation_banner(
            True, "42", "tok", admin_prefix="/console"
        )
        html = render_to_string(banner)
        assert "/console/impersonate/stop" in html
        assert "/admin/impersonate/stop" not in html

    def test_banner_defaults_to_admin_prefix(self) -> None:
        banner = build_impersonation_banner(True, "42", "tok")
        html = render_to_string(banner)
        assert "/admin/impersonate/stop" in html

    def test_banner_inactive(self) -> None:
        assert build_impersonation_banner(False, "", "") == ""


class TestInferredPermissionSchemes:
    """Sidebar inference must accept both ``.view`` and ``.read`` grants.

    The authorization middleware checks ``{resource}.view`` while older
    permission sets grant ``{resource}.read`` — a user holding either must
    see the nav link.
    """

    def test_view_permission_shows_resource_link(self) -> None:
        items = [{"label": "Products", "href": "/admin/products"}]
        user = AdminUser(
            id=1, email="a@example.com", name="A", permissions={"products.view"}
        )
        assert len(prepare_navigation(items, {}, user)) == 1

    def test_read_permission_shows_resource_link(self) -> None:
        items = [{"label": "Products", "href": "/admin/products"}]
        user = AdminUser(
            id=1, email="a@example.com", name="A", permissions={"products.read"}
        )
        assert len(prepare_navigation(items, {}, user)) == 1

    def test_no_permission_hides_resource_link(self) -> None:
        items = [{"label": "Products", "href": "/admin/products"}]
        user = AdminUser(id=1, email="a@example.com", name="A", permissions=set())
        assert prepare_navigation(items, {}, user) == []

    def test_superuser_sees_all_resource_links(self) -> None:
        items = [
            {"label": "Products", "href": "/admin/products"},
            {"label": "Customers", "href": "/admin/customers"},
        ]
        user = AdminUser(
            id=1,
            email="a@example.com",
            name="A",
            is_superuser=True,
            permissions=set(),
        )
        assert len(prepare_navigation(items, {}, user)) == 2
