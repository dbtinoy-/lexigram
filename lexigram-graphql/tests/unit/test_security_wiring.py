"""Through-executor proofs that depth/complexity/alias limits reject on the live path."""

from __future__ import annotations

import pytest
import strawberry

from lexigram.graphql.config import GraphQLConfig
from lexigram.graphql.core.execution import GraphQLExecutorProtocol
from lexigram.graphql.schema.builder import SchemaBuilderProtocol


@strawberry.type
class Nested:
    @strawberry.field
    def hello(self) -> str:
        return "world"

    @strawberry.field
    def nested(self) -> Nested:
        return Nested()


@strawberry.type
class Query:
    @strawberry.field
    def hello(self) -> str:
        return "world"

    @strawberry.field
    def items(self, first: int | None = 10) -> list[str]:
        return ["x"] * (first if first is not None else 0)

    @strawberry.field
    def nested(self) -> Nested:
        return Nested()


def _executor() -> GraphQLExecutorProtocol:
    schema = SchemaBuilderProtocol(config=GraphQLConfig()).query(Query).build()
    return GraphQLExecutorProtocol(schema)


class TestSecurityWiring:
    @pytest.mark.asyncio
    async def test_simple_query_still_executes(self) -> None:
        result = await _executor().execute("{ hello }")
        assert result.is_ok()
        response = result.unwrap()
        assert response.data == {"hello": "world"}
        assert not response.errors

    @pytest.mark.asyncio
    async def test_over_depth_query_is_rejected(self) -> None:
        query = "{" + "nested {" * 11 + "hello" + "}" * 11 + "}"
        result = await _executor().execute(query)
        assert result.is_ok()
        response = result.unwrap()
        assert response.errors, "depth-11 query must be rejected"
        assert "depth 11 exceeds maximum" in response.errors[0].message

    @pytest.mark.asyncio
    async def test_alias_bomb_is_rejected(self) -> None:
        query = "{" + " ".join(f"a{i}: hello" for i in range(16)) + "}"
        result = await _executor().execute(query)
        assert result.is_ok()
        response = result.unwrap()
        assert response.errors, "16-alias query must be rejected"
        assert "aliases" in response.errors[0].message

    @pytest.mark.asyncio
    async def test_over_complexity_query_is_rejected(self) -> None:
        result = await _executor().execute("{ items(first: 100000) }")
        assert result.is_ok()
        response = result.unwrap()
        assert response.errors, "complexity-100000 query must be rejected"
        assert "complexity" in response.errors[0].message.lower()

    @pytest.mark.asyncio
    async def test_disabled_config_does_not_enforce_limits(self) -> None:
        cfg = GraphQLConfig(
            depth_limit={"enabled": False},
            complexity={"enabled": False},
            alias_limit={"enabled": False},
        )
        schema = SchemaBuilderProtocol(config=cfg).query(Query).build()
        executor = GraphQLExecutorProtocol(schema)

        query = "{" + "nested {" * 11 + "hello" + "}" * 11 + "}"
        result = await executor.execute(query)
        assert result.is_ok()
        assert not result.unwrap().errors, "depth limit must not enforce when disabled"

        query = "{" + " ".join(f"a{i}: hello" for i in range(16)) + "}"
        result = await executor.execute(query)
        assert result.is_ok()
        assert not result.unwrap().errors, "alias limit must not enforce when disabled"

        result = await executor.execute("{ items(first: 100000) }")
        assert result.is_ok()
        assert not result.unwrap().errors, (
            "complexity limit must not enforce when disabled"
        )
