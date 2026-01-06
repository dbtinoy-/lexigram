"""Tests for app/pipeline module - MiddlewarePipeline."""

import pytest

from lexigram.app.pipeline import MiddlewarePipeline


class TestMiddlewarePipelineInit:
    """Tests for MiddlewarePipeline initialization."""

    def test_init_empty(self) -> None:
        """Test initialization with no middleware."""
        pipeline = MiddlewarePipeline()
        assert len(pipeline) == 0
        assert pipeline._middleware == []

    def test_init_with_middleware_list(self) -> None:
        """Test initialization with middleware list."""
        async def mw1(ctx, next):
            return await next(ctx)

        async def mw2(ctx, next):
            return await next(ctx)

        pipeline = MiddlewarePipeline([mw1, mw2])
        assert len(pipeline) == 2


class TestMiddlewarePipelineAdd:
    """Tests for MiddlewarePipeline.add method."""

    def test_add_returns_new_pipeline(self) -> None:
        """Test that add returns a new pipeline."""
        pipeline = MiddlewarePipeline()

        async def mw(ctx, next):
            return await next(ctx)

        new_pipeline = pipeline.add(mw)
        assert new_pipeline is not pipeline
        assert len(new_pipeline) == 1
        assert len(pipeline) == 0

    def test_add_multiple_middleware(self) -> None:
        """Test adding multiple middleware."""
        pipeline = MiddlewarePipeline()

        async def mw1(ctx, next):
            return await next(ctx)

        async def mw2(ctx, next):
            return await next(ctx)

        pipeline = pipeline.add(mw1).add(mw2)
        assert len(pipeline) == 2


class TestMiddlewarePipelineExecute:
    """Tests for MiddlewarePipeline.execute method."""

    @pytest.mark.asyncio
    async def test_execute_no_middleware(self) -> None:
        """Test execute with no middleware calls handler directly."""
        pipeline = MiddlewarePipeline()
        called = False

        async def handler(ctx):
            nonlocal called
            called = True
            return "result"

        result = await pipeline.execute({}, handler)
        assert result == "result"
        assert called is True

    @pytest.mark.asyncio
    async def test_execute_single_middleware(self) -> None:
        """Test execute with single middleware."""
        call_order = []

        async def my_middleware(ctx, next):
            call_order.append("before")
            result = await next(ctx)
            call_order.append("after")
            return result

        pipeline = MiddlewarePipeline().add(my_middleware)

        async def handler(ctx):
            call_order.append("handler")
            return "result"

        result = await pipeline.execute({}, handler)
        assert result == "result"
        assert call_order == ["before", "handler", "after"]

    @pytest.mark.asyncio
    async def test_execute_multiple_middleware(self) -> None:
        """Test execute with multiple middleware."""
        call_order = []

        async def mw1(ctx, next):
            call_order.append("mw1_before")
            result = await next(ctx)
            call_order.append("mw1_after")
            return result

        async def mw2(ctx, next):
            call_order.append("mw2_before")
            result = await next(ctx)
            call_order.append("mw2_after")
            return result

        pipeline = MiddlewarePipeline().add(mw1).add(mw2)

        async def handler(ctx):
            call_order.append("handler")
            return "result"

        result = await pipeline.execute({}, handler)
        assert result == "result"
        # First added middleware executes first
        assert call_order[0] == "mw1_before"

    @pytest.mark.asyncio
    async def test_execute_passes_context(self) -> None:
        """Test that context is passed through middleware chain."""
        pipeline = MiddlewarePipeline()

        async def handler(ctx):
            return ctx["value"]

        ctx = {"value": 42}
        result = await pipeline.execute(ctx, handler)
        assert result == 42


class TestMiddlewarePipelineLen:
    """Tests for MiddlewarePipeline.__len__ method."""

    def test_len_empty(self) -> None:
        """Test len of empty pipeline."""
        pipeline = MiddlewarePipeline()
        assert len(pipeline) == 0

    def test_len_with_middleware(self) -> None:
        """Test len with middleware."""
        async def mw1(ctx, next):
            return await next(ctx)

        async def mw2(ctx, next):
            return await next(ctx)

        pipeline = MiddlewarePipeline().add(mw1).add(mw2)
        assert len(pipeline) == 2


class TestMiddlewarePipelineRepr:
    """Tests for MiddlewarePipeline.__repr__ method."""

    def test_repr_empty(self) -> None:
        """Test repr of empty pipeline."""
        pipeline = MiddlewarePipeline()
        assert "0 middleware" in repr(pipeline)

    def test_repr_with_middleware(self) -> None:
        """Test repr of pipeline with middleware."""
        async def mw(ctx, next):
            return await next(ctx)

        pipeline = MiddlewarePipeline().add(mw)
        assert "1 middleware" in repr(pipeline)


class TestMiddlewarePipelineImmutability:
    """Tests for pipeline immutability."""

    def test_original_pipeline_unchanged_after_add(self) -> None:
        """Test that original pipeline is not modified."""
        pipeline = MiddlewarePipeline()

        async def mw(ctx, next):
            return await next(ctx)

        new_pipeline = pipeline.add(mw)
        assert len(pipeline) == 0
        assert len(new_pipeline) == 1

    def test_multiple_adds_dont_affect_original(self) -> None:
        """Test that multiple adds don't affect original."""
        pipeline = MiddlewarePipeline()
        original = pipeline

        async def mw1(ctx, next):
            return await next(ctx)

        async def mw2(ctx, next):
            return await next(ctx)

        p1 = pipeline.add(mw1)
        p2 = pipeline.add(mw2)

        assert pipeline is original
        assert len(p1) == 1
        assert len(p2) == 1
        assert p1 is not p2
