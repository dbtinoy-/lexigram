"""Tests for GraphQL module."""

import pytest
from unittest.mock import AsyncMock
from lexigram.di.module import DynamicModule
from lexigram.graphql import GraphQLModule
from lexigram.graphql.di.provider import GraphQLProvider
from lexigram.graphql.core.caching import _MemoryCacheShim
from lexigram.graphql.security.rate_limit import UnifiedRateLimiter



class _FakeWebRateLimiter:
    def __init__(self) -> None:
        self.calls = 0

    async def check_rate_limit(self, request, *, max_requests: int, window_seconds: int, scope: str) -> None:
        self.calls += 1


class _FakeContainer:
    def __init__(self, resolved) -> None:
        self._resolved = resolved
        self.resolve_calls = 0

    async def resolve(self, token):
        self.resolve_calls += 1
        return self._resolved


class _FailingCacheContainer:
    def __init__(self) -> None:
        self.calls: list[tuple[object, bool]] = []

    async def resolve(self, token, *, bypass_visibility: bool = False):
        from lexigram.contracts.events import EventBusProtocol
        from lexigram.contracts.infra.cache.protocols import CacheBackendProtocol
        from lexigram.contracts.observability.metrics import MetricsRecorderProtocol
        from lexigram.contracts.web import WebRateLimiterProtocol

        self.calls.append((token, bypass_visibility))

        if token is CacheBackendProtocol:
            raise ValueError("Cache service 'None' not found. Available: []")

        if token in {
            WebRateLimiterProtocol,
            MetricsRecorderProtocol,
            EventBusProtocol,
        }:
            return None

        return None


class _BypassOnlySubscriptionAuthContainer:
    def __init__(self, auth_handler: object) -> None:
        self.auth_handler = auth_handler
        self.calls: list[tuple[object, bool]] = []

    async def resolve(self, token, *, bypass_visibility: bool = False):
        from lexigram.contracts.events import EventBusProtocol
        from lexigram.contracts.infra.cache.protocols import CacheBackendProtocol
        from lexigram.contracts.observability.metrics import MetricsRecorderProtocol
        from lexigram.contracts.web import WebRateLimiterProtocol
        from lexigram.graphql.subscriptions.auth import SubscriptionAuth

        self.calls.append((token, bypass_visibility))

        if token is CacheBackendProtocol:
            raise ValueError("Cache service 'None' not found. Available: []")

        if token is SubscriptionAuth:
            if not bypass_visibility:
                raise RuntimeError(
                    "subscription auth lookup must bypass visibility",
                )
            return self.auth_handler

        if token in {
            WebRateLimiterProtocol,
            MetricsRecorderProtocol,
            EventBusProtocol,
        }:
            return None

        return None


class _FakeRegistrar:
    def __init__(self) -> None:
        self.bindings = {}

    def singleton(self, token, factory):
        self.bindings[token] = factory


class TestGraphQLModule:
    def test_graphql_module_exists(self) -> None:
        assert GraphQLModule is not None

    def test_configure_returns_dynamic_module(self) -> None:
        result = GraphQLModule.configure()
        assert isinstance(result, DynamicModule)
        assert result.module is GraphQLModule

    def test_configure_with_query_class(self) -> None:
        class DummyQuery:
            pass
        result = GraphQLModule.configure(query_class=DummyQuery)
        assert isinstance(result, DynamicModule)

    def test_configure_with_mutation_class(self) -> None:
        class DummyMutation:
            pass
        result = GraphQLModule.configure(mutation_class=DummyMutation)
        assert isinstance(result, DynamicModule)

    def test_configure_with_subscription_class(self) -> None:
        class DummySubscription:
            pass
        result = GraphQLModule.configure(subscription_class=DummySubscription)
        assert isinstance(result, DynamicModule)

    def test_configure_is_global(self) -> None:
        result = GraphQLModule.configure()
        assert result.is_global is True

    @pytest.mark.asyncio
    async def test_provider_registers_unified_rate_limiter_without_container_argument(
        self,
    ) -> None:
        from lexigram.graphql.security.rate_limit import RateLimiter

        provider = GraphQLProvider()
        registrar = _FakeRegistrar()

        await provider.register(registrar)

        rate_limiter_factory = registrar.bindings[RateLimiter]
        unified_factory = registrar.bindings[UnifiedRateLimiter]

        rate_limiter = rate_limiter_factory()
        unified = unified_factory()

        assert isinstance(rate_limiter, UnifiedRateLimiter)
        assert isinstance(unified, UnifiedRateLimiter)
        assert rate_limiter._web_rate_limiter is None
        assert unified._web_rate_limiter is None

    @pytest.mark.asyncio
    async def test_provider_boot_injects_web_rate_limiter_into_unified_rate_limiter(
        self,
    ) -> None:
        from lexigram.graphql.security.rate_limit import RateLimiter

        web_rate_limiter = _FakeWebRateLimiter()
        container = _FakeContainer(resolved=web_rate_limiter)
        provider = GraphQLProvider()
        registrar = _FakeRegistrar()

        await provider.register(registrar)
        await provider.boot(container)

        rate_limiter_factory = registrar.bindings[RateLimiter]
        unified_rate_limiter = rate_limiter_factory()

        class _Context:
            raw_request = object()

        allowed = await unified_rate_limiter.is_allowed(_Context())

        assert allowed is True
        assert web_rate_limiter.calls == 1
        assert container.resolve_calls >= 1

    @pytest.mark.asyncio
    async def test_provider_boot_falls_back_to_memory_cache_when_backend_lookup_fails(
        self,
    ) -> None:
        provider = GraphQLProvider()
        registrar = _FakeRegistrar()
        container = _FailingCacheContainer()

        await provider.register(registrar)
        await provider.boot(container)

        assert isinstance(provider._response_cache._backend, _MemoryCacheShim)  # noqa: SLF001

    @pytest.mark.asyncio
    async def test_provider_boot_bypasses_visibility_for_subscription_auth_lookup(
        self,
    ) -> None:
        auth_handler = object()
        provider = GraphQLProvider()
        registrar = _FakeRegistrar()
        container = _BypassOnlySubscriptionAuthContainer(auth_handler)

        await provider.register(registrar)
        await provider.boot(container)

        assert provider._ws_transport._auth_handler is auth_handler  # noqa: SLF001
