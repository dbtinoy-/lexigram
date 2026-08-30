"""Regression tests for request isolation and canonical table state."""

from __future__ import annotations

from types import SimpleNamespace

from lexigram.admin.actions.standard import DeleteAction, DeleteBulkAction, EditAction
from lexigram.admin.resources.config import TableConfiguration
from lexigram.admin.resources.list_columns import get_bulk_actions
from lexigram.admin.resources.list_query import ListDataFetcher
from lexigram.admin.resources.list_renderer import ListRenderer
from lexigram.admin.ui.organisms.data_table import DataTable
from lexigram.admin.ui.organisms.data_table.actions import (
    normalize_action,
    render_bulk_action_button,
)
from lexigram.ui import TableState, render_to_string
from lexigram.ui.columns.types import TextColumn


class _Permissions:
    def __init__(self, values: set[str]) -> None:
        self.values = values

    def has(self, permission: str) -> bool:
        resource = permission.split(".", 1)[0]
        return permission in self.values or f"{resource}.*" in self.values


class _QueryParams:
    def __init__(self, values: dict[str, str]) -> None:
        self.values = values

    def get(self, key: str, default=None):
        return self.values.get(key, default)

    def getlist(self, key: str) -> list[str]:
        value = self.values.get(key)
        return [value] if value is not None else []

    def __iter__(self):
        return iter(self.values)


class _Request:
    def __init__(self, values: dict[str, str], tenant_id: str, user_id: str) -> None:
        self.query_params = _QueryParams(values)
        self.state = type(
            "State",
            (),
            {"tenant_id": tenant_id, "user": type("User", (), {"id": user_id})()},
        )()


def test_request_defaults_honor_resource_page_size_and_keep_cursor_out_of_filters():
    request = _Request({"cursor": "next-page"}, "acme", "u1")
    state = TableState.from_request(request, defaults={"per_page": 50})

    assert state.per_page == 50
    assert state.cursor == "next-page"
    assert state.filters == {}


def test_sort_transition_resets_offset_pagination():
    state = TableState(page=7, cursor="old", sort_by="name")

    updated = state.with_sort("email")

    assert updated.page == 1
    assert updated.cursor is None
    assert state.page == 7
    assert state.cursor == "old"


def test_rendering_does_not_mutate_shared_resource_configuration():
    columns = [TextColumn("name"), TextColumn("email")]
    config = TableConfiguration(
        columns=columns,
        actions=[],
        resource_prefix="/admin/users",
    )
    state = TableState(column_order=["email", "name"])

    render_to_string(DataTable(config=config, state=state, data=[{"id": "1"}]))

    assert config.actions == []
    assert [column.name for column in config.columns] == ["name", "email"]


def test_list_renderer_maps_request_permissions_to_table_capabilities():
    renderer = object.__new__(ListRenderer)
    renderer.resource_name = "users"
    request = SimpleNamespace(
        state=SimpleNamespace(
            permissions=_Permissions({"users.list", "users.edit"})
        )
    )

    assert renderer._permissions_for_request(request) == {
        "can_view": True,
        "can_create": False,
        "can_update": True,
        "can_delete": False,
    }


def test_url_sort_and_group_fields_are_whitelisted():
    renderer = object.__new__(ListRenderer)
    config = TableConfiguration(
        columns=[TextColumn("name")],
        default_sort_by="name",
        group_by="name",
    )
    state = TableState(sort_by="__class__", group_by="__dict__", page=4)

    safe_state = renderer._sanitize_table_state(
        state,
        config,
        config.columns,
        None,
    )

    assert safe_state.sort_by == "name"
    assert safe_state.group_by == "name"
    assert safe_state.page == 1
    assert safe_state.cursor is None


def test_explicit_empty_permission_map_fails_closed():
    html = render_to_string(
        DataTable(
            columns=[TextColumn("name")],
            data=[{"id": "1", "name": "A"}],
            resource_prefix="/admin/users",
            permissions={},
        )
    )

    assert "You do not have access to this resource" in html
    assert ">A<" not in html


def test_denied_standard_actions_are_not_rendered():
    config = TableConfiguration(
        columns=[TextColumn("name")],
        actions=[EditAction()],
        bulk_actions=[DeleteBulkAction()],
        resource_prefix="/admin/users",
    )

    html = render_to_string(
        DataTable(
            config=config,
            data=[{"id": "1", "name": "A"}],
            permissions={
                "can_view": True,
                "can_create": False,
                "can_update": False,
                "can_delete": False,
            },
        )
    )

    assert "Edit" not in html
    assert "Delete Selected" not in html
    # The declaration remains intact for another request with different RBAC.
    assert config.actions[0].name == "edit"
    assert config.bulk_actions[0].name == "delete"


def test_admin_bulk_actions_are_preserved_by_resource_resolution():
    action = DeleteBulkAction()

    assert get_bulk_actions(TableConfiguration(bulk_actions=[action]), None) == [action]


def test_action_normalization_uses_a_context_instead_of_none():
    descriptor = normalize_action(DeleteAction())

    assert descriptor.name == "delete"
    assert descriptor.url is None


def test_canonical_bulk_action_uses_the_registered_bulk_route():
    html = render_bulk_action_button(
        DeleteBulkAction(),
        resource_name="users",
        resource_prefix="/admin/users",
    )

    assert "/admin/users/bulk" in str(html)
    assert "/admin/users/bulk/delete" not in str(html)


def test_cache_key_isolated_by_tenant_and_table_state():
    class Cache:
        def cache_key(self, resource_name: str, *parts: str) -> str:
            return ":".join((resource_name, *parts))

    fetcher = ListDataFetcher("users")
    fetcher._cache_integration = Cache()
    state = TableState(search="ada", filters={"status": "active"})

    acme_key = fetcher._build_cache_key(_Request({}, "acme", "u1"), state)
    beta_key = fetcher._build_cache_key(_Request({}, "beta", "u1"), state)
    other_query_key = fetcher._build_cache_key(
        _Request({}, "acme", "u1"), state.with_search("grace")
    )

    assert acme_key != beta_key
    assert acme_key != other_query_key
