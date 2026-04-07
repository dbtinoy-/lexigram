"""Tests for GraphQL configuration — production safety and Cache-Control wiring.

Covers:
    - G4: ``GraphQLConfig`` auto-disables Playground when ``LEX_ENV=production``
    - G3: ``GraphQLResponse`` carries ``http_headers``; executor sets ``Cache-Control``
"""

from __future__ import annotations

import os

import pytest
import strawberry

from lexigram.graphql.config import GraphQLConfig, CacheConfig, PlaygroundConfig
from lexigram.graphql.core.context import GraphQLResponse
from lexigram.graphql.core.execution import GraphQLExecutorProtocol


# ---------------------------------------------------------------------------
# G4: Playground auto-disable in production
# ---------------------------------------------------------------------------


class TestPlaygroundAutoDisableInProduction:
    """GraphQLConfig.playground.enabled is forced to False in production."""

    def test_playground_enabled_by_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Playground defaults to enabled in non-production environments."""
        monkeypatch.delenv("LEX_ENV", raising=False)
        config = GraphQLConfig()
        assert config.playground.enabled is True

    def test_playground_disabled_when_lexigram_env_production(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Playground is forcibly disabled when LEX_ENV=production."""
        monkeypatch.setenv("LEX_ENV", "production")
        config = GraphQLConfig()
        assert config.playground.enabled is False

    def test_playground_disabled_case_insensitive(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """LEX_ENV check is case-insensitive (PRODUCTION, Production, etc.)."""
        monkeypatch.setenv("LEX_ENV", "PRODUCTION")
        config = GraphQLConfig()
        assert config.playground.enabled is False

    def test_playground_not_disabled_for_staging(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Non-production environments keep the configured playground value."""
        monkeypatch.setenv("LEX_ENV", "staging")
        config = GraphQLConfig()
        assert config.playground.enabled is True

    def test_playground_not_disabled_for_development(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Development environment keeps playground enabled."""
        monkeypatch.setenv("LEX_ENV", "development")
        config = GraphQLConfig()
        assert config.playground.enabled is True

    def test_production_classmethod_still_disables_playground(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """``GraphQLConfig.production()`` continues to disable playground regardless of env."""
        monkeypatch.delenv("LEX_ENV", raising=False)
        config = GraphQLConfig.production()
        assert config.playground.enabled is False

    def test_explicit_playground_true_overridden_in_production(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Even if PlaygroundConfig(enabled=True) is supplied, production env wins."""
        monkeypatch.setenv("LEX_ENV", "production")
        config = GraphQLConfig(playground=PlaygroundConfig(enabled=True))
        assert config.playground.enabled is False


# ---------------------------------------------------------------------------
# G3: GraphQLResponse http_headers field
# ---------------------------------------------------------------------------


class TestGraphQLResponseHttpHeaders:
    """GraphQLResponse carries an http_headers dict for Cache-Control etc."""

    def test_http_headers_empty_by_default(self) -> None:
        """New ``GraphQLResponse`` has an empty ``http_headers`` dict."""
        response: GraphQLResponse[None] = GraphQLResponse(data=None)
        assert response.http_headers == {}

    def test_http_headers_can_be_set(self) -> None:
        """``http_headers`` is mutable and accepts arbitrary header entries."""
        response: GraphQLResponse[None] = GraphQLResponse(data=None)
        response.http_headers["Cache-Control"] = "public, max-age=300"
        assert response.http_headers["Cache-Control"] == "public, max-age=300"

    def test_http_headers_independent_across_instances(self) -> None:
        """Each response instance has its own ``http_headers`` dict."""
        r1: GraphQLResponse[None] = GraphQLResponse(data=None)
        r2: GraphQLResponse[None] = GraphQLResponse(data=None)
        r1.http_headers["X-Custom"] = "value"
        assert "X-Custom" not in r2.http_headers


# ---------------------------------------------------------------------------
# G3: Executor sets Cache-Control when cache config is enabled
# ---------------------------------------------------------------------------


@strawberry.type
class _SimpleQuery:
    @strawberry.field
    def ping(self) -> str:
        return "pong"


_schema = strawberry.Schema(query=_SimpleQuery)


class TestExecutorCacheControlHeader:
    """GraphQLExecutorProtocol sets Cache-Control when CacheConfig.enabled=True."""

    @pytest.fixture
    def executor(self) -> GraphQLExecutorProtocol:
        """Executor backed by a minimal Strawberry schema."""
        return GraphQLExecutorProtocol(_schema)

    @pytest.mark.asyncio
    async def test_cache_control_header_set_when_cache_enabled(
        self, executor: GraphQLExecutorProtocol
    ) -> None:
        """Cache-Control header present when config.cache.enabled=True."""
        from lexigram.graphql.config import GraphQLConfig, CacheConfig
        from lexigram.graphql.core.context import GraphQLContext
        from lexigram.graphql.types import CacheScope

        config = GraphQLConfig(
            cache=CacheConfig(enabled=True, default_max_age=120, vary_headers=[])
        )
        context = GraphQLContext(config=config)
        result_obj = await executor.execute("{ ping }", context=context)
        assert result_obj.is_ok()
        response = result_obj.unwrap()

        assert not response.has_errors
        assert "Cache-Control" in response.http_headers
        assert "max-age=120" in response.http_headers["Cache-Control"]

    @pytest.mark.asyncio
    async def test_cache_control_public_scope(
        self, executor: GraphQLExecutorProtocol
    ) -> None:
        """Cache-Control header contains 'public' for PUBLIC scope."""
        from lexigram.graphql.config import GraphQLConfig, CacheConfig
        from lexigram.graphql.core.context import GraphQLContext
        from lexigram.graphql.types import CacheScope

        config = GraphQLConfig(
            cache=CacheConfig(
                enabled=True,
                default_max_age=60,
                default_scope=CacheScope.PUBLIC,
                vary_headers=[],
            )
        )
        context = GraphQLContext(config=config)
        result_obj = await executor.execute("{ ping }", context=context)
        assert result_obj.is_ok()
        response = result_obj.unwrap()

        assert not response.has_errors
        header = response.http_headers.get("Cache-Control", "")
        assert "public" in header

    @pytest.mark.asyncio
    async def test_cache_control_private_scope(
        self, executor: GraphQLExecutorProtocol
    ) -> None:
        """Cache-Control header contains 'private' for PRIVATE scope."""
        from lexigram.graphql.config import GraphQLConfig, CacheConfig
        from lexigram.graphql.core.context import GraphQLContext
        from lexigram.graphql.types import CacheScope

        config = GraphQLConfig(
            cache=CacheConfig(
                enabled=True,
                default_max_age=30,
                default_scope=CacheScope.PRIVATE,
                vary_headers=[],
            )
        )
        context = GraphQLContext(config=config)
        result_obj = await executor.execute("{ ping }", context=context)
        assert result_obj.is_ok()
        response = result_obj.unwrap()

        assert not response.has_errors
        header = response.http_headers.get("Cache-Control", "")
        assert "private" in header

    @pytest.mark.asyncio
    async def test_vary_header_set_when_vary_headers_configured(
        self, executor: GraphQLExecutorProtocol
    ) -> None:
        """Vary header is set when vary_headers list is non-empty."""
        from lexigram.graphql.config import GraphQLConfig, CacheConfig
        from lexigram.graphql.core.context import GraphQLContext

        config = GraphQLConfig(
            cache=CacheConfig(
                enabled=True,
                default_max_age=300,
                vary_headers=["Accept", "Accept-Encoding"],
            )
        )
        context = GraphQLContext(config=config)
        result_obj = await executor.execute("{ ping }", context=context)
        assert result_obj.is_ok()
        response = result_obj.unwrap()

        assert not response.has_errors
        assert "Vary" in response.http_headers
        assert "Accept" in response.http_headers["Vary"]

    @pytest.mark.asyncio
    async def test_no_cache_control_when_cache_disabled(
        self, executor: GraphQLExecutorProtocol
    ) -> None:
        """Cache-Control header is NOT set when cache is disabled."""
        from lexigram.graphql.config import GraphQLConfig, CacheConfig
        from lexigram.graphql.core.context import GraphQLContext

        config = GraphQLConfig(cache=CacheConfig(enabled=False))
        context = GraphQLContext(config=config)
        result_obj = await executor.execute("{ ping }", context=context)
        assert result_obj.is_ok()
        response = result_obj.unwrap()

        assert not response.has_errors
        assert "Cache-Control" not in response.http_headers

    @pytest.mark.asyncio
    async def test_no_cache_control_without_config(
        self, executor: GraphQLExecutorProtocol
    ) -> None:
        """Cache-Control header is NOT set when no config is provided."""
        result_obj = await executor.execute("{ ping }")
        assert result_obj.is_ok()
        response = result_obj.unwrap()
        assert not response.has_errors
        assert "Cache-Control" not in response.http_headers
