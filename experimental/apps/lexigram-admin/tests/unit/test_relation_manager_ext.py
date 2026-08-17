"""Tests for RelationManager (extended inline editing support)."""

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


class _PetRelationManager(RelationManager):
    """Concrete subclass for testing."""

    relationship_name = "pets"

    @classmethod
    def table(cls, table_config: Any = None) -> list[Any]:
        return []

    async def get_query(self) -> list[Any]:
        # Return some fake pets
        return [_FakePet(id=1, name="Rex"), _FakePet(id=2, name="Fluffy")]


class _FakePet:
    def __init__(self, id: int, name: str) -> None:
        self.id = id
        self.name = name

    def __repr__(self) -> str:
        return f"Pet({self.id}, {self.name})"


class TestRelationManagerInstantiation:
    """Test basic instantiation and inheritance."""

    def test_inherits_from_abstract_relation_manager(self) -> None:
        """RelationManager is a subclass of AbstractRelationManager."""
        assert issubclass(RelationManager, AbstractRelationManager)

    def test_inherits_from_abc(self) -> None:
        """AbstractRelationManager inherits from ABC."""
        assert issubclass(AbstractRelationManager, ABC)

    def test_can_instantiate_with_parent_id(self) -> None:
        """Can instantiate with parent_id."""
        mgr = _PetRelationManager(parent_id=42)
        assert mgr.parent_id == 42

    def test_can_instantiate_with_parent(self) -> None:
        """Can instantiate with parent object."""
        parent = _FakePet(id=99, name="Parent")
        mgr = _PetRelationManager(parent_id=99, parent=parent)
        assert mgr.parent is parent


class TestRelationManagerInlineDefaults:
    """Test inline editing policy defaults."""

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
    """Test default permission predicates."""

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
    """Test default form methods."""

    def test_create_form_returns_none(self) -> None:
        mgr = _PetRelationManager(parent_id=1)
        assert mgr.create_form() is None

    def test_edit_form_returns_none(self) -> None:
        mgr = _PetRelationManager(parent_id=1)
        result = mgr.edit_form(record=_FakePet(id=1, name="Rex"))
        assert result is None


class TestRelationManagerRender:
    """Test render method."""

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


class TestRegisterRelationRoutes:
    """Test route registration."""

    def test_register_relation_routes_returns_list_of_6_routes(self) -> None:
        routes = register_relation_routes("users", _PetRelationManager)
        assert isinstance(routes, list)
        assert len(routes) == 6

    def test_routes_have_correct_methods(self) -> None:
        routes = register_relation_routes("users", _PetRelationManager)

        # Route 0: list (GET) — Starlette adds HEAD for GET routes
        assert routes[0].methods == {"GET", "HEAD"}
        # Route 1: create form (GET)
        assert routes[1].methods == {"GET", "HEAD"}
        # Route 2: create (POST)
        assert routes[2].methods == {"POST"}
        # Route 3: edit form (GET)
        assert routes[3].methods == {"GET", "HEAD"}
        # Route 4: update (PUT)
        assert routes[4].methods == {"PUT"}
        # Route 5: delete (DELETE)
        assert routes[5].methods == {"DELETE"}

    def test_route_paths_contain_correct_segments(self) -> None:
        routes = register_relation_routes("users", _PetRelationManager)

        assert "/users/" in routes[0].path
        assert "/new" in routes[1].path
        assert routes[0].path == routes[2].path  # list and create share path
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


class TestConcreteSubclassOverride:
    """Test that concrete subclasses can override methods."""

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

    @pytest.mark.asyncio
    async def test_can_override_render(self) -> None:
        class OverrideManager(_PetRelationManager):
            async def render(self, request: Any, resource_name: str = "") -> str:
                return "<div>Custom render</div>"

        mgr = OverrideManager(parent_id=1)
        html = await mgr.render(request=None, resource_name="users")
        assert html == "<div>Custom render</div>"
