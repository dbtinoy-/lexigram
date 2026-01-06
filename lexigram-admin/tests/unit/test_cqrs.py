"""Tests for the CQRS message types (commands and queries).

Admin buses are the framework buses from lexigram-events (CommandBusImpl /
QueryBusImpl).  There are no admin-specific bus reimplementations.
"""

from __future__ import annotations

from lexigram.admin.cqrs.queries import (
    AdminQuery,
    GetAdminUser,
    GetAuditLog,
    GetDashboardStats,
    GetResource,
    ListAdminUsers,
    ListResources,
    SearchResources,
)
from lexigram.admin.cqrs.commands import (
    AdminCommand,
    BulkDeleteResources,
    CreateAdminUser,
    CreateResource,
    DeleteResource,
    UpdateAdminUser,
    UpdateResource,
)


# ---------------------------------------------------------------------------
# Command dataclasses
# ---------------------------------------------------------------------------


class TestCommandDataclasses:
    def test_create_admin_user_defaults(self) -> None:
        cmd = CreateAdminUser(username="alice", email="a@b.com")
        assert cmd.username == "alice"
        assert cmd.roles == []

    def test_update_admin_user(self) -> None:
        cmd = UpdateAdminUser(user_id="u1", data={"email": "new@b.com"})
        assert cmd.user_id == "u1"

    def test_create_resource(self) -> None:
        cmd = CreateResource(resource_type="Product", data={"name": "Widget"})
        assert cmd.resource_type == "Product"

    def test_update_resource(self) -> None:
        cmd = UpdateResource(resource_type="Product", resource_id=1, data={"name": "v2"})
        assert cmd.resource_id == 1

    def test_delete_resource(self) -> None:
        cmd = DeleteResource(resource_type="Product", resource_id=1)
        assert cmd.soft_delete is True

    def test_bulk_delete_resources(self) -> None:
        cmd = BulkDeleteResources(resource_type="Product", resource_ids=[1, 2, 3])
        assert len(cmd.resource_ids) == 3

    def test_command_has_unique_id(self) -> None:
        c1 = CreateAdminUser()
        c2 = CreateAdminUser()
        assert c1.command_id != c2.command_id

    def test_admin_command_name(self) -> None:
        cmd = AdminCommand()
        assert cmd.name == "AdminCommand"

    def test_cqrs_init_re_exports_admin_command(self) -> None:
        """AdminCommand re-exported via cqrs package resolves to events.commands."""
        from lexigram.admin.cqrs import AdminCommand as CqrsCommand

        assert CqrsCommand is AdminCommand


# ---------------------------------------------------------------------------
# Query dataclasses
# ---------------------------------------------------------------------------


class TestQueryDataclasses:
    def test_get_admin_user(self) -> None:
        q = GetAdminUser(user_id="u1")
        assert q.user_id == "u1"
        assert q.name == "GetAdminUser"

    def test_list_admin_users_defaults(self) -> None:
        q = ListAdminUsers()
        assert q.page == 1
        assert q.page_size == 20

    def test_get_resource(self) -> None:
        q = GetResource(resource_type="Product", resource_id=1)
        assert q.resource_type == "Product"

    def test_list_resources(self) -> None:
        q = ListResources(resource_type="Product", filters={"active": True})
        assert q.filters["active"] is True

    def test_search_resources(self) -> None:
        q = SearchResources(resource_type="Product", query="widget")
        assert q.query == "widget"

    def test_get_dashboard_stats(self) -> None:
        q = GetDashboardStats(resource_types=["User", "Product"])
        assert "User" in q.resource_types

    def test_get_audit_log(self) -> None:
        q = GetAuditLog(page=2, action="delete")
        assert q.page == 2

    def test_query_has_unique_id(self) -> None:
        q1 = GetResource()
        q2 = GetResource()
        assert q1.query_id != q2.query_id

    def test_admin_query_re_exported_via_cqrs(self) -> None:
        """AdminQuery re-exported via cqrs package resolves to cqrs.queries."""
        from lexigram.admin.cqrs import AdminQuery as CqrsQuery

        assert CqrsQuery is AdminQuery

