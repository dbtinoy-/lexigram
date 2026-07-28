from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

from lexigram.graphql.core.introspection import (
    INTROSPECTION_QUERY,
    SIMPLE_INTROSPECTION_QUERY,
    IntrospectionHandler,
    get_introspection_query,
)


class TestGetIntrospectionQuery:
    def test_full_query(self) -> None:
        query = get_introspection_query(simplified=False)
        assert "query IntrospectionQuery" in query
        assert query == INTROSPECTION_QUERY

    def test_simplified_query(self) -> None:
        query = get_introspection_query(simplified=True)
        assert "query SimpleIntrospectionQuery" in query
        assert query == SIMPLE_INTROSPECTION_QUERY


class TestIntrospectionHandler:
    @pytest.fixture
    def mock_schema(self) -> MagicMock:
        schema = MagicMock()
        execute_result = MagicMock()
        execute_result.errors = None
        execute_result.data = {"__schema": {"types": [], "queryType": {"name": "Query"}}}
        schema.execute = AsyncMock(return_value=execute_result)
        schema._schema = MagicMock()
        return schema

    @pytest.mark.asyncio
    async def test_introspect_caches_result(self, mock_schema: MagicMock) -> None:
        handler = IntrospectionHandler(mock_schema)
        result1 = await handler.introspect()
        result2 = await handler.introspect()
        assert result1 == result2
        mock_schema.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_enabled_property(self, mock_schema: MagicMock) -> None:
        handler = IntrospectionHandler(mock_schema, enabled=True)
        assert handler.enabled is True
        handler.disable()
        assert handler.enabled is False
        handler.enable()
        assert handler.enabled is True

    @pytest.mark.asyncio
    async def test_introspect_when_disabled(self, mock_schema: MagicMock) -> None:
        handler = IntrospectionHandler(mock_schema, enabled=False)
        with pytest.raises(ValueError, match="Introspection is disabled"):
            await handler.introspect()

    @pytest.mark.asyncio
    async def test_get_types(self, mock_schema: MagicMock) -> None:
        handler = IntrospectionHandler(mock_schema)
        types = await handler.get_types()
        assert types == []

    @pytest.mark.asyncio
    async def test_get_query_type(self, mock_schema: MagicMock) -> None:
        handler = IntrospectionHandler(mock_schema)
        query_type = await handler.get_query_type()
        assert query_type == {"name": "Query"}

    @pytest.mark.asyncio
    async def test_get_mutation_type_none(self, mock_schema: MagicMock) -> None:
        handler = IntrospectionHandler(mock_schema)
        mutation_type = await handler.get_mutation_type()
        assert mutation_type is None

    @pytest.mark.asyncio
    async def test_get_subscription_type_none(self, mock_schema: MagicMock) -> None:
        handler = IntrospectionHandler(mock_schema)
        sub_type = await handler.get_subscription_type()
        assert sub_type is None

    @pytest.mark.asyncio
    async def test_get_type_fields_found(self, mock_schema: MagicMock) -> None:
        mock_schema.execute.return_value.data = {
            "__schema": {
                "types": [
                    {"name": "User", "fields": [{"name": "id"}, {"name": "name"}]},
                    {"name": "Query", "fields": []},
                ]
            }
        }
        handler = IntrospectionHandler(mock_schema)
        fields = await handler.get_type_fields("User")
        assert len(fields) == 2

    @pytest.mark.asyncio
    async def test_get_type_fields_not_found(self, mock_schema: MagicMock) -> None:
        handler = IntrospectionHandler(mock_schema)
        fields = await handler.get_type_fields("NonExistent")
        assert fields == []

    @pytest.mark.asyncio
    async def test_clear_cache(self, mock_schema: MagicMock) -> None:
        handler = IntrospectionHandler(mock_schema)
        await handler.introspect()
        assert len(handler._cache) == 1
        handler.clear_cache()
        assert len(handler._cache) == 0

    @pytest.mark.asyncio
    async def test_generate_sdl(self, mock_schema: MagicMock) -> None:
        with MagicMock() as print_schema:
            handler = IntrospectionHandler(mock_schema)
            with MagicMock() as graphql_mod:
                graphql_mod.print_schema.return_value = "schema { query: Query }"
                import sys

                fake_module = type(sys)("graphql")
                fake_module.print_schema = MagicMock(return_value="schema { query: Query }")
                original = None
                if "graphql" in sys.modules:
                    original = sys.modules["graphql"]
                sys.modules["graphql"] = fake_module
                try:
                    sdl = await handler.generate_sdl()
                    assert "schema" in sdl
                finally:
                    if original:
                        sys.modules["graphql"] = original
                    else:
                        del sys.modules["graphql"]
