"""Reflected record_id fallback tests for relation routes (F3 reflected XSS)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from lexigram.admin.relations import RelationManager, register_relation_routes


class _EmptyRelationManager(RelationManager):
    relationship_name = "pets"

    @classmethod
    def table(cls, table_config: Any = None) -> list[Any]:
        return []

    async def get_query(self) -> list[Any]:
        return []


class _FoundRelationManager(_EmptyRelationManager):
    async def get_query(self) -> list[Any]:
        return [type("Item", (), {"id": "7", "name": "Rex"})()]


class _StubRequest:
    def __init__(self, path_params: dict[str, str]) -> None:
        self.path_params = path_params
        self.state = SimpleNamespace(user=object())


class TestRelationRoutesReflectedXss:
    @pytest.mark.asyncio
    async def test_hostile_record_id_escaped_in_fallback(self) -> None:
        routes = register_relation_routes("users", _EmptyRelationManager)
        request = _StubRequest(
            {"parent_id": "1", "record_id": "/><script>alert(1)</script>"}
        )
        response = await routes[3].endpoint(request)
        body = response.body.decode()
        assert "&lt;script&gt;" in body
        assert "<script>" not in body

    @pytest.mark.asyncio
    async def test_benign_record_id_keeps_fallback_shape(self) -> None:
        routes = register_relation_routes("users", _EmptyRelationManager)
        request = _StubRequest({"parent_id": "1", "record_id": "123"})
        response = await routes[3].endpoint(request)
        body = response.body.decode()
        assert "Edit form for 123" in body

    @pytest.mark.asyncio
    async def test_missing_edit_form_for_found_record_escapes_payload(self) -> None:
        routes = register_relation_routes("users", _FoundRelationManager)
        request = _StubRequest(
            {"parent_id": "1", "record_id": "/><script>alert(1)</script>"}
        )
        response = await routes[3].endpoint(request)
        body = response.body.decode()
        assert "&lt;script&gt;" in body
        assert "<script>" not in body
