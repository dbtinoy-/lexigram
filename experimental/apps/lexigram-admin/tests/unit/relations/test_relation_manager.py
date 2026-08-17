"""Tests for RelationManager (extended inline editing support) and AbstractRelationManager."""

from __future__ import annotations

from abc import ABC
from typing import Any

import pytest

from lexigram.admin.exceptions import PermissionDeniedError
from lexigram.admin.relations import (
    AbstractRelationManager,
    RelationManager,
    register_relation_routes,
)
from lexigram.result import Ok, Result


class _FakePet:
    def __init__(self, id: int, name: str) -> None:
        self.id = id
        self.name = name

    def __repr__(self) -> str:
        return f"Pet({self.id}, {self.name})"


class _PetRelationManager(RelationManager):
    """Concrete subclass for testing."""

    relationship_name = "pets"

    @classmethod
    def table(cls, table_config: Any = None) -> list[Any]:
        return []

    async def get_query(self) -> list[Any]:
        return [_FakePet(id=1, name="Rex"), _FakePet(id=2, name="Fluffy")]


class TestAbstractRelationManager:
    """AbstractRelationManager ABC contract."""

    def test_is_abstract(self) -> None:
        assert issubclass(AbstractRelationManager, ABC)

    def test_cannot_instantiate_abstract_class(self) -> None:
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            AbstractRelationManager(parent_id=1)  # type: ignore[abstract]

    def test_cannot_instantiate_without_table(self) -> None:
        class MissingTable(AbstractRelationManager):
            async def get_query(self) -> list[Any]:
                return []

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            MissingTable(parent_id=1)  # type: ignore[abstract]

    def test_cannot_instantiate_without_get_query(self) -> None:
        class MissingQuery(AbstractRelationManager):
            @classmethod
            def table(cls, table_config: Any = None) -> list[Any]:
                return []

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            MissingQuery(parent_id=1)  # type: ignore[abstract]

    def test_relationship_name_class_var(self) -> None:
        class NamedRelation(AbstractRelationManager):
            relationship_name = "custom"

            @classmethod
            def table(cls, table_config: Any = None) -> list[Any]:
                return []

            async def get_query(self) -> list[Any]:
                return []

        assert NamedRelation.relationship_name == "custom"

    def test_get_relationship_name_uses_class_var(self) -> None:
        assert _PetRelationManager.get_relationship_name() == "pets"

    def test_get_relationship_name_falls_back_to_class_name(self) -> None:
        class MyRelationManager(AbstractRelationManager):
            @classmethod
            def table(cls, table_config: Any = None) -> list[Any]:
                return []

            async def get_query(self) -> list[Any]:
                return []

        assert MyRelationManager.get_relationship_name() == "my"

    def test_init_sets_parent_id_and_parent(self) -> None:
        parent = _FakePet(id=99, name="Parent")
        mgr = _PetRelationManager(parent_id=99, parent=parent)
        assert mgr.parent_id == 99
        assert mgr.parent is parent

    def test_parent_id_defaults_to_none(self) -> None:
        mgr = _PetRelationManager(parent_id=None)
        assert mgr.parent_id is None

    def test_parent_defaults_to_none(self) -> None:
        mgr = _PetRelationManager(parent_id=1)
        assert mgr.parent is None

    @pytest.mark.asyncio
    async def test_count_returns_zero_when_empty(self) -> None:
        class EmptyRelation(RelationManager):
            relationship_name = "empty"

            @classmethod
            def table(cls, table_config: Any = None) -> list[Any]:
                return []

            async def get_query(self) -> list[Any]:
                return []

        mgr = EmptyRelation(parent_id=1)
        count = await mgr.count()
        assert count == 0

    @pytest.mark.asyncio
    async def test_count_returns_number_of_items(self) -> None:
        mgr = _PetRelationManager(parent_id=1)
        count = await mgr.count()
        assert count == 2

    @pytest.mark.asyncio
    async def test_get_items_returns_paginated_results(self) -> None:
        mgr = _PetRelationManager(parent_id=1)
        items = await mgr.get_items(page=1, per_page=1)
        assert len(items) == 1

    @pytest.mark.asyncio
    async def test_get_items_returns_empty_when_no_results(self) -> None:
        class EmptyRelation(RelationManager):
            relationship_name = "empty"

            @classmethod
            def table(cls, table_config: Any = None) -> list[Any]:
                return []

            async def get_query(self) -> list[Any]:
                return []

        mgr = EmptyRelation(parent_id=1)
        items = await mgr.get_items(page=1, per_page=20)
        assert items == []


class TestRelationManagerInstantiation:
    """RelationManager concrete class construction."""

    def test_inherits_from_abstract_relation_manager(self) -> None:
        assert issubclass(RelationManager, AbstractRelationManager)

    def test_is_not_abstract(self) -> None:
        mgr = _PetRelationManager(parent_id=42)
        assert isinstance(mgr, RelationManager)

    def test_can_instantiate_with_parent_id(self) -> None:
        mgr = _PetRelationManager(parent_id=42)
        assert mgr.parent_id == 42

    def test_can_instantiate_with_parent(self) -> None:
        parent = _FakePet(id=99, name="Parent")
        mgr = _PetRelationManager(parent_id=99, parent=parent)
        assert mgr.parent is parent


class TestRelationManagerInlineDefaults:
    """Inline editing policy defaults."""

    def test_inline_create_defaults_to_true(self) -> None:
        mgr = _PetRelationManager(parent_id=1)
        assert mgr.inline_create is True

    def test_inline_edit_defaults_to_true(self) -> None:
        mgr = _PetRelationManager(parent_id=1)
        assert mgr.inline_edit is True

    def test_inline_delete_defaults_to_true(self) -> None:
        mgr = _PetRelationManager(parent_id=1)
        assert mgr.inline_delete is True

    def test_inline_detach_defaults_to_false(self) -> None:
        mgr = _PetRelationManager(parent_id=1)
        assert mgr.inline_detach is False


class TestRelationManagerPermissionPredicates:
    """Default permission predicates return Ok(None)."""

    def test_can_create_returns_ok(self) -> None:
        mgr = _PetRelationManager(parent_id=1)
        result = mgr.can_create()
        assert isinstance(result, Ok)
        assert result.unwrap() is None

    def test_can_edit_returns_ok(self) -> None:
        mgr = _PetRelationManager(parent_id=1)
        result = mgr.can_edit(record=_FakePet(id=1, name="Rex"))
        assert isinstance(result, Ok)
        assert result.unwrap() is None

    def test_can_delete_returns_ok(self) -> None:
        mgr = _PetRelationManager(parent_id=1)
        result = mgr.can_delete(record=_FakePet(id=1, name="Rex"))
        assert isinstance(result, Ok)
        assert result.unwrap() is None

    def test_can_detach_returns_ok(self) -> None:
        mgr = _PetRelationManager(parent_id=1)
        result = mgr.can_detach(record=_FakePet(id=1, name="Rex"))
        assert isinstance(result, Ok)
        assert result.unwrap() is None

    def test_can_create_with_user_returns_ok(self) -> None:
        mgr = _PetRelationManager(parent_id=1)
        result = mgr.can_create(user="admin")
        assert result.is_ok()

    def test_can_edit_with_user_returns_ok(self) -> None:
        mgr = _PetRelationManager(parent_id=1)
        result = mgr.can_edit(record=_FakePet(id=1, name="Rex"), user="admin")
        assert result.is_ok()


class TestRelationManagerFormDefaults:
    """Form methods return None by default (derived from table)."""

    def test_create_form_returns_none(self) -> None:
        mgr = _PetRelationManager(parent_id=1)
        assert mgr.create_form() is None

    def test_edit_form_returns_none(self) -> None:
        mgr = _PetRelationManager(parent_id=1)
        result = mgr.edit_form(record=_FakePet(id=1, name="Rex"))
        assert result is None

    def test_create_form_can_be_overridden(self) -> None:
        class OverrideManager(_PetRelationManager):
            def create_form(self) -> str | None:
                return "<form>Custom</form>"

        mgr = OverrideManager(parent_id=1)
        assert mgr.create_form() == "<form>Custom</form>"


class TestRelationManagerRender:
    """Render method produces HTML."""

    @pytest.mark.asyncio
    async def test_render_returns_non_empty_string(self) -> None:
        mgr = _PetRelationManager(parent_id=42)
        html = await mgr.render(request=None, resource_name="users")
        assert isinstance(html, str)
        assert len(html) > 0

    @pytest.mark.asyncio
    async def test_render_contains_relationship_name(self) -> None:
        mgr = _PetRelationManager(parent_id=42)
        html = await mgr.render(request=None, resource_name="users")
        assert "pets" in html

    @pytest.mark.asyncio
    async def test_render_contains_table_tag(self) -> None:
        mgr = _PetRelationManager(parent_id=42)
        html = await mgr.render(request=None, resource_name="users")
        assert "<table>" in html

    @pytest.mark.asyncio
    async def test_render_contains_relation_panel_div(self) -> None:
        mgr = _PetRelationManager(parent_id=42)
        html = await mgr.render(request=None, resource_name="users")
        assert 'class="relation-panel"' in html

    @pytest.mark.asyncio
    async def test_render_includes_add_link_when_inline_create(self) -> None:
        mgr = _PetRelationManager(parent_id=42)
        html = await mgr.render(request=None, resource_name="users")
        assert "+ Add" in html
        assert "relations/pets/new" in html

    @pytest.mark.asyncio
    async def test_render_does_not_include_create_link_when_disabled(self) -> None:
        class NoCreateManager(_PetRelationManager):
            inline_create = False

        mgr = NoCreateManager(parent_id=42)
        html = await mgr.render(request=None, resource_name="users")
        assert "+ Add" not in html

    @pytest.mark.asyncio
    async def test_render_includes_edit_links_when_inline_edit(self) -> None:
        mgr = _PetRelationManager(parent_id=42)
        html = await mgr.render(request=None, resource_name="users")
        assert "/edit" in html
        assert "hx-get" in html

    @pytest.mark.asyncio
    async def test_render_does_not_include_edit_links_when_disabled(self) -> None:
        class NoEditManager(_PetRelationManager):
            inline_edit = False

        mgr = NoEditManager(parent_id=42)
        html = await mgr.render(request=None, resource_name="users")
        assert "/edit" not in html

    @pytest.mark.asyncio
    async def test_render_includes_delete_links_when_inline_delete(self) -> None:
        mgr = _PetRelationManager(parent_id=42)
        html = await mgr.render(request=None, resource_name="users")
        assert "hx-delete" in html

    @pytest.mark.asyncio
    async def test_render_does_not_include_delete_links_when_disabled(self) -> None:
        class NoDeleteManager(_PetRelationManager):
            inline_delete = False

        mgr = NoDeleteManager(parent_id=42)
        html = await mgr.render(request=None, resource_name="users")
        assert "hx-delete" not in html

    @pytest.mark.asyncio
    async def test_render_empty_query_returns_valid_html(self) -> None:
        class EmptyRelation(RelationManager):
            relationship_name = "none"

            @classmethod
            def table(cls, table_config: Any = None) -> list[Any]:
                return []

            async def get_query(self) -> list[Any]:
                return []

        mgr = EmptyRelation(parent_id=1)
        html = await mgr.render(request=None, resource_name="items")
        assert isinstance(html, str)
        assert "none" in html


class TestRegisterRelationRoutes:
    """Route registration for relation managers."""

    def test_register_relation_routes_returns_list_of_6_routes(self) -> None:
        routes = register_relation_routes("users", _PetRelationManager)
        assert isinstance(routes, list)
        assert len(routes) == 6

    def test_routes_have_correct_methods(self) -> None:
        routes = register_relation_routes("users", _PetRelationManager)
        assert routes[0].methods == {"GET", "HEAD"}
        assert routes[1].methods == {"GET", "HEAD"}
        assert routes[2].methods == {"POST"}
        assert routes[3].methods == {"GET", "HEAD"}
        assert routes[4].methods == {"PUT"}
        assert routes[5].methods == {"DELETE"}

    def test_route_paths_contain_correct_segments(self) -> None:
        routes = register_relation_routes("users", _PetRelationManager)
        assert "/users/" in routes[0].path
        assert "/new" in routes[1].path
        assert routes[0].path == routes[2].path
        assert "/edit" in routes[3].path

    def test_all_routes_are_starlette_route_instances(self) -> None:
        from starlette.routing import Route as StarletteRoute

        routes = register_relation_routes("users", _PetRelationManager)
        for route in routes:
            assert isinstance(route, StarletteRoute)

    def test_routes_have_names(self) -> None:
        routes = register_relation_routes("users", _PetRelationManager)
        for route in routes:
            assert route.name is not None


class TestRelationManagerOverride:
    """Subclass override behavior."""

    def test_can_override_inline_create(self) -> None:
        class OverrideManager(_PetRelationManager):
            inline_create = False

        mgr = OverrideManager(parent_id=1)
        assert mgr.inline_create is False

    def test_can_override_can_create(self) -> None:
        class OverrideManager(_PetRelationManager):
            def can_create(
                self, user: Any | None = None
            ) -> Result[None, PermissionDeniedError]:
                return Ok(None)

        mgr = OverrideManager(parent_id=1)
        result = mgr.can_create()
        assert result.is_ok()

    def test_can_override_create_form(self) -> None:
        class OverrideManager(_PetRelationManager):
            def create_form(self) -> str | None:
                return "<form>Custom create form</form>"

        mgr = OverrideManager(parent_id=1)
        assert mgr.create_form() == "<form>Custom create form</form>"

    def test_can_override_edit_form(self) -> None:
        class OverrideManager(_PetRelationManager):
            def edit_form(self, record: Any) -> str | None:
                return f"<form>Editing {record.name}</form>"

        mgr = OverrideManager(parent_id=1)
        record = _FakePet(id=1, name="Rex")
        assert mgr.edit_form(record) == "<form>Editing Rex</form>"

    def test_can_override_relationship_name(self) -> None:
        class OverrideManager(_PetRelationManager):
            relationship_name = "custom_pets"

        assert OverrideManager.get_relationship_name() == "custom_pets"

    @pytest.mark.asyncio
    async def test_can_override_render(self) -> None:
        class OverrideManager(_PetRelationManager):
            async def render(self, request: Any, resource_name: str = "") -> str:
                return "<div>Custom render</div>"

        mgr = OverrideManager(parent_id=1)
        html = await mgr.render(request=None, resource_name="users")
        assert html == "<div>Custom render</div>"
