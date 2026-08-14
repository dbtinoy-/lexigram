"""Integration tests: Resource + ViewPage + RelationManager wiring."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from lexigram.admin.pages.resource_pages import ViewPage
from lexigram.admin.relations.manager_ext import RelationManager
from lexigram.admin.resources.base import Resource


class _PetRelationManager(RelationManager):
    """Concrete RelationManager subclass for testing."""

    relationship_name = "pets"

    @classmethod
    def table(cls, table_config: Any = None) -> list[Any]:
        return []

    async def get_query(self) -> list[Any]:
        return []


class _PostRelationManager(RelationManager):
    """Another RelationManager subclass for testing."""

    relationship_name = "posts"

    @classmethod
    def table(cls, table_config: Any = None) -> list[Any]:
        return []

    async def get_query(self) -> list[Any]:
        return []


@pytest.mark.asyncio
async def test_resource_has_relations_default() -> None:
    """Resource.relations defaults to empty list."""
    assert Resource.relations == []


@pytest.mark.asyncio
async def test_resource_can_define_relations() -> None:
    """Resource can define relations list."""

    class TestResource(Resource):
        relations = [_PetRelationManager]

    assert TestResource.relations == [_PetRelationManager]


@pytest.mark.asyncio
async def test_view_page_renders_relations() -> None:
    """ViewPage renders relation panels when relations are provided."""
    request = MagicMock()
    request.path_params = {"id": "123"}

    page = ViewPage(
        resource_name="users",
        path="/users/{id}",
        relations=[_PetRelationManager],
    )
    response = await page.view(request)
    assert "hx-get" in response.content
    assert "pets" in response.content
    assert "relations/pets" in response.content


@pytest.mark.asyncio
async def test_view_page_without_relations() -> None:
    """ViewPage without relations renders normally."""
    request = MagicMock()
    request.path_params = {"id": "123"}

    page = ViewPage(resource_name="users")
    response = await page.view(request)
    assert "hx-get" not in response.content


@pytest.mark.asyncio
async def test_view_page_relation_lazy_loads() -> None:
    """Relation panel uses hx-get for lazy loading."""
    request = MagicMock()
    request.path_params = {"id": "456"}

    page = ViewPage(
        resource_name="articles",
        relations=[_PetRelationManager],
    )
    response = await page.view(request)
    content = response.content
    assert "hx-get" in content
    assert 'hx-trigger="load"' in content
    assert "/articles/456/relations/pets" in content


@pytest.mark.asyncio
async def test_view_page_multiple_relations() -> None:
    """ViewPage renders multiple relation panels."""
    request = MagicMock()
    request.path_params = {"id": "789"}

    page = ViewPage(
        resource_name="users",
        relations=[_PetRelationManager, _PostRelationManager],
    )
    response = await page.view(request)
    content = response.content
    assert "relation-pets" in content
    assert "relation-posts" in content
    assert "relations/pets" in content
    assert "relations/posts" in content


@pytest.mark.asyncio
async def test_resource_routes_have_relations() -> None:
    """Resource-defined relations are accessible at class level."""

    class UserResource(Resource):
        relations = [_PetRelationManager, _PostRelationManager]

    assert len(UserResource.relations) == 2
    assert _PetRelationManager in UserResource.relations
    assert _PostRelationManager in UserResource.relations
