"""Tests for SearchProvider multi-backend Named DI support (SR2)."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from lexigram.contracts.core import HealthCheckResult, HealthStatus
from lexigram.search.config import BackendType, MeiliSearchConfig, NamedSearchConfig, SearchConfig
from lexigram.search.di.provider import SearchProvider


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_healthy_result(component: str = "search") -> HealthCheckResult:
    return HealthCheckResult(component=component, status=HealthStatus.HEALTHY, duration_ms=1.0)


def _make_degraded_result(component: str = "search") -> HealthCheckResult:
    return HealthCheckResult(component=component, status=HealthStatus.DEGRADED, duration_ms=1.0)


def _make_unhealthy_result(component: str = "search") -> HealthCheckResult:
    return HealthCheckResult(component=component, status=HealthStatus.UNHEALTHY, duration_ms=1.0)


def _mock_container() -> MagicMock:
    """Build a mock container registrar that records all singleton() calls."""
    container = MagicMock()
    container.singleton = MagicMock()
    return container


# ---------------------------------------------------------------------------
# Test 1 — backends=[] falls through to single-backend path
# ---------------------------------------------------------------------------


class TestSingleBackendFallthrough:
    """SearchProvider with backends=[] falls through to _register_single_backend()."""

    @pytest.mark.asyncio
    async def test_empty_backends_uses_single_path(self) -> None:
        """No backends → _search_services stays empty, singleton(SearchEngine) called."""
        from lexigram.search.engine import SearchEngine

        config = SearchConfig(backends=[])
        provider = SearchProvider.from_config(config)
        container = _mock_container()

        await provider.register(container)

        # _search_services must be empty (single-backend path)
        assert provider._search_services == []

        # container.singleton should have been called with SearchEngine
        types_registered = [c.args[0] for c in container.singleton.call_args_list]
        assert SearchEngine in types_registered

    @pytest.mark.asyncio
    async def test_no_backends_field_uses_single_path(self) -> None:
        """SearchConfig with no backends field at all defaults to single-backend."""
        provider = SearchProvider.with_memory()
        provider._config = SearchConfig()
        container = _mock_container()

        await provider.register(container)

        assert provider._search_services == []


# ---------------------------------------------------------------------------
# Test 2 — _register_multi_backend registers SearchEngineProtocol with name=
# ---------------------------------------------------------------------------


class TestMultiBackendNamedRegistration:
    """_register_multi_backend() registers SearchEngineProtocol with name= per backend."""

    @pytest.mark.asyncio
    async def test_named_singletons_registered_per_backend(self) -> None:
        """Each NamedSearchConfig entry → a singleton with name=entry.name."""
        from lexigram.contracts.search import SearchEngineProtocol

        config = SearchConfig(
            backends=[
                NamedSearchConfig(name="alpha", backend_type=BackendType.MEMORY),
                NamedSearchConfig(name="beta", backend_type=BackendType.MEMORY),
            ]
        )
        provider = SearchProvider.from_config(config)
        container = _mock_container()

        await provider.register(container)

        # Collect all (type, name) pairs registered
        named_calls: dict[str, type] = {}
        for c in container.singleton.call_args_list:
            kwargs = c.kwargs
            if "name" in kwargs:
                named_calls[kwargs["name"]] = c.args[0]

        assert "alpha" in named_calls
        assert "beta" in named_calls
        assert named_calls["alpha"] is SearchEngineProtocol
        assert named_calls["beta"] is SearchEngineProtocol

    @pytest.mark.asyncio
    async def test_search_services_populated_per_backend(self) -> None:
        """_search_services has one entry per NamedSearchConfig."""
        config = SearchConfig(
            backends=[
                NamedSearchConfig(name="one", backend_type=BackendType.MEMORY),
                NamedSearchConfig(name="two", backend_type=BackendType.MEMORY),
                NamedSearchConfig(name="three", backend_type=BackendType.MEMORY),
            ]
        )
        provider = SearchProvider.from_config(config)
        container = _mock_container()

        await provider.register(container)

        assert len(provider._search_services) == 3
        names = [n for n, _ in provider._search_services]
        assert names == ["one", "two", "three"]


# ---------------------------------------------------------------------------
# Test 3 — Primary backend gets both named AND unnamed binding
# ---------------------------------------------------------------------------


class TestPrimaryBackendBinding:
    """Primary backend (first or flagged) gets both named and unnamed bindings."""

    @pytest.mark.asyncio
    async def test_first_entry_gets_unnamed_binding(self) -> None:
        """First entry in backends list always receives the unnamed SearchEngineProtocol binding."""
        from lexigram.contracts.search import SearchEngineProtocol

        config = SearchConfig(
            backends=[
                NamedSearchConfig(name="first", backend_type=BackendType.MEMORY),
                NamedSearchConfig(name="second", backend_type=BackendType.MEMORY),
            ]
        )
        provider = SearchProvider.from_config(config)
        container = _mock_container()

        await provider.register(container)

        # Count how many times SearchEngineProtocol was registered without a name
        unnamed_protocol_calls = [
            c
            for c in container.singleton.call_args_list
            if c.args and c.args[0] is SearchEngineProtocol and "name" not in c.kwargs
        ]
        # Exactly one unnamed binding (for "first")
        assert len(unnamed_protocol_calls) == 1

    @pytest.mark.asyncio
    async def test_primary_flag_gets_unnamed_binding(self) -> None:
        """Entry with primary=True receives the unnamed SearchEngineProtocol binding."""
        from lexigram.contracts.search import SearchEngineProtocol

        config = SearchConfig(
            backends=[
                NamedSearchConfig(name="archive", backend_type=BackendType.MEMORY),
                NamedSearchConfig(
                    name="main", primary=True, backend_type=BackendType.MEMORY
                ),
            ]
        )
        provider = SearchProvider.from_config(config)
        container = _mock_container()

        await provider.register(container)

        unnamed_protocol_calls = [
            c
            for c in container.singleton.call_args_list
            if c.args and c.args[0] is SearchEngineProtocol and "name" not in c.kwargs
        ]
        # Both "archive" (first) and "main" (primary=True) get unnamed binding
        assert len(unnamed_protocol_calls) == 2

    @pytest.mark.asyncio
    async def test_identity_check_not_equality(self) -> None:
        """Primary detection uses identity (``is``), not equality, to avoid false positives."""
        from lexigram.contracts.search import SearchEngineProtocol

        # Two entries with identical data — only the first should be primary by identity
        entry_a = NamedSearchConfig(name="a", backend_type=BackendType.MEMORY)
        entry_b = NamedSearchConfig(name="b", backend_type=BackendType.MEMORY)
        config = SearchConfig(backends=[entry_a, entry_b])
        provider = SearchProvider.from_config(config)
        container = _mock_container()

        await provider.register(container)

        unnamed_protocol_calls = [
            c
            for c in container.singleton.call_args_list
            if c.args and c.args[0] is SearchEngineProtocol and "name" not in c.kwargs
        ]
        # Only entry_a (first, by identity) should get unnamed binding
        assert len(unnamed_protocol_calls) == 1


# ---------------------------------------------------------------------------
# Test 4 — health_check() aggregates worst status
# ---------------------------------------------------------------------------


class TestHealthCheckAggregation:
    """health_check() returns the worst individual status across all backends."""

    @pytest.mark.asyncio
    async def test_all_healthy_returns_healthy(self) -> None:
        config = SearchConfig(
            backends=[
                NamedSearchConfig(name="x", backend_type=BackendType.MEMORY),
                NamedSearchConfig(name="y", backend_type=BackendType.MEMORY),
            ]
        )
        provider = SearchProvider.from_config(config)
        container = _mock_container()
        await provider.register(container)

        # Patch backends with healthy mocks
        for idx, (name, _) in enumerate(provider._search_services):
            mock_backend = AsyncMock()
            mock_backend.health_check = AsyncMock(return_value=_make_healthy_result(name))
            provider._search_services[idx] = (name, mock_backend)

        result = await provider.health_check()

        assert result.status == HealthStatus.HEALTHY
        assert result.component == "search"

    @pytest.mark.asyncio
    async def test_one_degraded_returns_degraded(self) -> None:
        config = SearchConfig(
            backends=[
                NamedSearchConfig(name="a", backend_type=BackendType.MEMORY),
                NamedSearchConfig(name="b", backend_type=BackendType.MEMORY),
            ]
        )
        provider = SearchProvider.from_config(config)
        container = _mock_container()
        await provider.register(container)

        healthy_backend = AsyncMock()
        healthy_backend.health_check = AsyncMock(return_value=_make_healthy_result("a"))
        degraded_backend = AsyncMock()
        degraded_backend.health_check = AsyncMock(return_value=_make_degraded_result("b"))

        provider._search_services = [("a", healthy_backend), ("b", degraded_backend)]

        result = await provider.health_check()

        assert result.status == HealthStatus.DEGRADED

    @pytest.mark.asyncio
    async def test_one_unhealthy_returns_unhealthy_even_with_degraded(self) -> None:
        config = SearchConfig(
            backends=[
                NamedSearchConfig(name="p", backend_type=BackendType.MEMORY),
                NamedSearchConfig(name="q", backend_type=BackendType.MEMORY),
                NamedSearchConfig(name="r", backend_type=BackendType.MEMORY),
            ]
        )
        provider = SearchProvider.from_config(config)
        container = _mock_container()
        await provider.register(container)

        p_backend = AsyncMock()
        p_backend.health_check = AsyncMock(return_value=_make_healthy_result("p"))
        q_backend = AsyncMock()
        q_backend.health_check = AsyncMock(return_value=_make_degraded_result("q"))
        r_backend = AsyncMock()
        r_backend.health_check = AsyncMock(return_value=_make_unhealthy_result("r"))

        provider._search_services = [("p", p_backend), ("q", q_backend), ("r", r_backend)]

        result = await provider.health_check()

        assert result.status == HealthStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_exception_from_backend_counts_as_unhealthy(self) -> None:
        config = SearchConfig(
            backends=[
                NamedSearchConfig(name="ok", backend_type=BackendType.MEMORY),
                NamedSearchConfig(name="bad", backend_type=BackendType.MEMORY),
            ]
        )
        provider = SearchProvider.from_config(config)
        container = _mock_container()
        await provider.register(container)

        ok_backend = AsyncMock()
        ok_backend.health_check = AsyncMock(return_value=_make_healthy_result("ok"))
        bad_backend = AsyncMock()
        bad_backend.health_check = AsyncMock(side_effect=RuntimeError("connection refused"))

        provider._search_services = [("ok", ok_backend), ("bad", bad_backend)]

        result = await provider.health_check()

        assert result.status == HealthStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_details_contain_per_backend_status(self) -> None:
        """health_check() includes per-backend status in details dict."""
        config = SearchConfig(
            backends=[
                NamedSearchConfig(name="m1", backend_type=BackendType.MEMORY),
                NamedSearchConfig(name="m2", backend_type=BackendType.MEMORY),
            ]
        )
        provider = SearchProvider.from_config(config)
        container = _mock_container()
        await provider.register(container)

        m1_backend = AsyncMock()
        m1_backend.health_check = AsyncMock(return_value=_make_healthy_result("m1"))
        m2_backend = AsyncMock()
        m2_backend.health_check = AsyncMock(return_value=_make_degraded_result("m2"))

        provider._search_services = [("m1", m1_backend), ("m2", m2_backend)]

        result = await provider.health_check()

        assert result.details is not None
        assert "search:m1" in result.details
        assert "search:m2" in result.details


# ---------------------------------------------------------------------------
# Test 5 — shutdown() iterates in reversed order
# ---------------------------------------------------------------------------


class TestShutdownOrder:
    """shutdown() closes backends in reversed LIFO registration order."""

    @pytest.mark.asyncio
    async def test_shutdown_reversed_order(self) -> None:
        config = SearchConfig(
            backends=[
                NamedSearchConfig(name="first", backend_type=BackendType.MEMORY),
                NamedSearchConfig(name="second", backend_type=BackendType.MEMORY),
                NamedSearchConfig(name="third", backend_type=BackendType.MEMORY),
            ]
        )
        provider = SearchProvider.from_config(config)
        container = _mock_container()
        await provider.register(container)

        close_order: list[str] = []

        def _make_closer(name: str) -> AsyncMock:
            async def _close() -> None:
                close_order.append(name)

            m = AsyncMock()
            m.close = _close
            return m

        provider._search_services = [
            ("first", _make_closer("first")),
            ("second", _make_closer("second")),
            ("third", _make_closer("third")),
        ]

        await provider.shutdown()

        assert close_order == ["third", "second", "first"]

    @pytest.mark.asyncio
    async def test_shutdown_skips_backends_without_close(self) -> None:
        """Backends without a close() method are silently skipped."""
        config = SearchConfig(
            backends=[
                NamedSearchConfig(name="no_close", backend_type=BackendType.MEMORY),
            ]
        )
        provider = SearchProvider.from_config(config)
        container = _mock_container()
        await provider.register(container)

        backend_without_close = MagicMock(spec=[])  # no close attribute
        provider._search_services = [("no_close", backend_without_close)]

        # Must not raise
        await provider.shutdown()

    @pytest.mark.asyncio
    async def test_single_backend_shutdown_no_error(self) -> None:
        """Single-backend path (no _search_services) still shuts down cleanly."""
        provider = SearchProvider.with_memory()

        # Must not raise even without any backends tracked
        await provider.shutdown()

        assert provider._search_services == []
