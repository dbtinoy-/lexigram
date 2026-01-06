"""Tests for core/decorators.py — Scope, singleton, scoped, transient, injectable, ScopeContext."""

from __future__ import annotations

import pytest

from lexigram.admin.core.decorators import (
    HAS_LEX_DI,
    Scope,
    ScopeContext,
    clear_singletons,
    injectable,
    scoped,
    singleton,
    transient,
)


class TestScope:
    """Tests for Scope enum."""

    def test_values(self) -> None:
        assert Scope.SINGLETON.value == "singleton"
        assert Scope.SCOPED.value == "scoped"
        assert Scope.TRANSIENT.value == "transient"

    def test_members(self) -> None:
        assert len(list(Scope)) == 3


class TestDecorators:
    """Tests for singleton / scoped / transient decorators."""

    def setup_method(self) -> None:
        clear_singletons()

    def test_transient_decorator_returns_class(self) -> None:
        @transient
        class MyService:
            pass

        svc1 = MyService()
        svc2 = MyService()
        # Transient: may or may not be the same — just verify it creates instances
        assert isinstance(svc1, MyService)
        assert isinstance(svc2, MyService)

    def test_scoped_decorator_returns_class(self) -> None:
        @scoped
        class RequestSvc:
            pass

        svc = RequestSvc()
        assert isinstance(svc, RequestSvc)

    def test_singleton_decorator_when_no_lexigram_di(self) -> None:
        # We can always apply the decorator and create an instance
        @singleton
        class CacheSvc:
            pass

        instance = CacheSvc()
        assert isinstance(instance, CacheSvc)


class TestInjectable:
    """Tests for injectable decorator factory."""

    def setup_method(self) -> None:
        clear_singletons()

    def test_injectable_singleton_scope(self) -> None:
        @injectable(scope=Scope.SINGLETON)
        class MySingleton:
            pass

        assert hasattr(MySingleton, "__injectable_scope__")
        assert MySingleton.__injectable_scope__ == Scope.SINGLETON

    def test_injectable_scoped_scope(self) -> None:
        @injectable(scope=Scope.SCOPED)
        class MyScopedSvc:
            pass

        assert MyScopedSvc.__injectable_scope__ == Scope.SCOPED  # type: ignore[attr-defined]

    def test_injectable_transient_scope(self) -> None:
        @injectable(scope=Scope.TRANSIENT)
        class MyTransientSvc:
            pass

        assert MyTransientSvc.__injectable_scope__ == Scope.TRANSIENT  # type: ignore[attr-defined]

    def test_injectable_default_scope_is_transient(self) -> None:
        @injectable()
        class DefaultSvc:
            pass

        assert DefaultSvc.__injectable_scope__ == Scope.TRANSIENT  # type: ignore[attr-defined]

    def test_injectable_with_token(self) -> None:
        @injectable(scope=Scope.SINGLETON, token="my.service")
        class TokenSvc:
            pass

        assert TokenSvc.__injectable_token__ == "my.service"  # type: ignore[attr-defined]

    def test_injectable_without_token_is_none(self) -> None:
        @injectable(scope=Scope.TRANSIENT)
        class NoTokenSvc:
            pass

        assert NoTokenSvc.__injectable_token__ is None  # type: ignore[attr-defined]


class TestScopeContext:
    """Tests for ScopeContext context manager."""

    def setup_method(self) -> None:
        clear_singletons()

    def test_sync_context_manager(self) -> None:
        with ScopeContext() as ctx:
            assert isinstance(ctx, ScopeContext)

    @pytest.mark.asyncio
    async def test_async_context_manager(self) -> None:
        async with ScopeContext() as ctx:
            assert isinstance(ctx, ScopeContext)

    def test_resolve_transient_creates_new_instance(self) -> None:
        @injectable(scope=Scope.TRANSIENT)
        class Svc:
            pass

        with ScopeContext() as ctx:
            s1 = ctx.resolve(Svc)
            s2 = ctx.resolve(Svc)
            assert isinstance(s1, Svc)
            assert isinstance(s2, Svc)
            # Transient = new each time
            assert s1 is not s2

    def test_resolve_scoped_returns_same_within_scope(self) -> None:
        @injectable(scope=Scope.SCOPED)
        class ScopedSvc:
            def __init__(self) -> None:
                self.val = "scoped"

        with ScopeContext() as ctx:
            s1 = ctx.resolve(ScopedSvc)
            s2 = ctx.resolve(ScopedSvc)
            assert s1 is s2

    def test_instances_cleared_after_scope_exit(self) -> None:
        @injectable(scope=Scope.SCOPED)
        class TmpSvc:
            pass

        with ScopeContext() as ctx:
            s1 = ctx.resolve(TmpSvc)

        with ScopeContext() as ctx2:
            s2 = ctx2.resolve(TmpSvc)

        assert s1 is not s2

    @pytest.mark.asyncio
    async def test_async_scope_cleanup(self) -> None:
        closed = []

        @injectable(scope=Scope.SCOPED)
        class AsyncSvc:
            async def close(self) -> None:
                closed.append(True)

        async with ScopeContext() as ctx:
            ctx.resolve(AsyncSvc)

        assert closed == [True]

    def test_resolve_without_scope_annotation_is_transient(self) -> None:
        class PlainClass:
            pass

        with ScopeContext() as ctx:
            s1 = ctx.resolve(PlainClass)
            s2 = ctx.resolve(PlainClass)
            # No scope annotation → treated as transient
            assert s1 is not s2


class TestClearSingletons:
    """Tests for clear_singletons utility."""

    def test_clear_singletons_runs_without_error(self) -> None:
        clear_singletons()  # Should not raise

    def test_has_lexigram_di_flag_is_bool(self) -> None:
        assert isinstance(HAS_LEX_DI, bool)
