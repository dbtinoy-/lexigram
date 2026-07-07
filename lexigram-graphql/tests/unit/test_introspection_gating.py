"""Introspection must be disabled in production at boot and enforced at request time."""

from __future__ import annotations

import pytest
import strawberry

from lexigram.graphql.config import GraphQLConfig
from lexigram.graphql.core.execution import GraphQLExecutorProtocol
from lexigram.graphql.schema.builder import SchemaBuilderProtocol


@strawberry.type
class Query:
    @strawberry.field
    def hello(self) -> str:
        return "world"


INTROSPECTION_QUERY = "{ __schema { queryType { name } } }"


def _executor(config: GraphQLConfig) -> GraphQLExecutorProtocol:
    schema = SchemaBuilderProtocol(config=config).query(Query).build()
    return GraphQLExecutorProtocol(schema)


class TestBootForceInProduction:
    def test_introspection_disabled_at_boot_in_production(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("LEX_ENV", "production")
        cfg = GraphQLConfig()
        assert cfg.introspection.enabled is False

    def test_introspection_force_cannot_be_overridden_in_production(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("LEX_ENV", "production")
        cfg = GraphQLConfig(introspection={"enabled": True})
        assert cfg.introspection.enabled is False

    def test_default_config_introspection_enabled_in_development(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("LEX_ENV", raising=False)
        cfg = GraphQLConfig()
        assert cfg.introspection.enabled is True


class TestRequestTimeGating:
    @pytest.mark.asyncio
    async def test_introspection_rejected_in_production(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("LEX_ENV", "production")
        result = await _executor(GraphQLConfig()).execute(INTROSPECTION_QUERY)
        assert result.is_ok()
        response = result.unwrap()
        assert response.errors, "introspection query must be rejected in production"
        assert "Introspection is disabled" in response.errors[0].message

    @pytest.mark.asyncio
    async def test_introspection_rejected_when_env_not_in_allowed_environments(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("LEX_ENV", "staging")
        result = await _executor(GraphQLConfig()).execute(INTROSPECTION_QUERY)
        assert result.is_ok()
        assert result.unwrap().errors

    @pytest.mark.asyncio
    async def test_introspection_allowed_in_development(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("LEX_ENV", raising=False)
        result = await _executor(GraphQLConfig()).execute(INTROSPECTION_QUERY)
        assert result.is_ok()
        assert not result.unwrap().errors
