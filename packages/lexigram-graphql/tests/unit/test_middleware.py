from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.graphql.core.middleware import (
    AbstractMiddleware,
    AuthMiddleware,
    LoggingMiddleware,
    MetricsMiddleware,
    MiddlewarePipeline,
    create_middleware_pipeline,
)


class TestAbstractMiddleware:
    @pytest.mark.asyncio
    async def test_default_process_passes_through(self) -> None:
        mw = AbstractMiddleware()
        handler = AsyncMock(return_value="result")
        result = await mw.process("ctx", handler)
        assert result == "result"
        handler.assert_awaited_once_with("ctx")

    def test_enabled_default(self) -> None:
        mw = AbstractMiddleware()
        assert mw.enabled is True

    def test_disabled(self) -> None:
        mw = AbstractMiddleware(enabled=False)
        assert mw.enabled is False


class TestLoggingMiddleware:
    @pytest.mark.asyncio
    async def test_logs_and_passes_through(self) -> None:
        mw = LoggingMiddleware(enabled=True)
        handler = AsyncMock(return_value="ok")
        result = await mw.process(MagicMock(request=MagicMock(query="{ hello }")), handler)
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_disabled_passes_through(self) -> None:
        mw = LoggingMiddleware(enabled=False)
        handler = AsyncMock(return_value="ok")
        result = await mw.process("ctx", handler)
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_logs_and_reraises(self) -> None:
        mw = LoggingMiddleware()
        handler = AsyncMock(side_effect=ValueError("oops"))
        with pytest.raises(ValueError, match="oops"):
            await mw.process(MagicMock(request=MagicMock(query="{ hello }")), handler)

    @pytest.mark.asyncio
    async def test_no_request_attribute(self) -> None:
        mw = LoggingMiddleware()
        handler = AsyncMock(return_value="ok")
        result = await mw.process(MagicMock(spec=object), handler)
        assert result == "ok"


class TestAuthMiddleware:
    @pytest.mark.asyncio
    async def test_with_user_passes(self) -> None:
        mw = AuthMiddleware(enabled=True, require_auth=True)
        context = MagicMock(user="test_user")
        handler = AsyncMock(return_value="ok")
        result = await mw.process(context, handler)
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_no_user_raises(self) -> None:
        mw = AuthMiddleware(enabled=True, require_auth=True)
        context = MagicMock(user=None)
        handler = AsyncMock()
        with pytest.raises(Exception, match="Authentication required"):
            await mw.process(context, handler)

    @pytest.mark.asyncio
    async def test_disabled_skips_auth(self) -> None:
        mw = AuthMiddleware(enabled=False, require_auth=True)
        context = MagicMock(user=None)
        handler = AsyncMock(return_value="ok")
        result = await mw.process(context, handler)
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_no_auth_not_required(self) -> None:
        mw = AuthMiddleware(enabled=True, require_auth=False)
        context = MagicMock(user=None)
        handler = AsyncMock(return_value="ok")
        result = await mw.process(context, handler)
        assert result == "ok"


class TestMetricsMiddleware:
    @pytest.mark.asyncio
    async def test_records_metrics(self) -> None:
        mw = MetricsMiddleware(enabled=True)
        handler = AsyncMock(return_value="ok")
        result = await mw.process("ctx", handler)
        assert result == "ok"
        metrics = mw.get_metrics()
        assert metrics["total_requests"] == 1
        assert metrics["total_time"] > 0

    @pytest.mark.asyncio
    async def test_disabled_no_metrics(self) -> None:
        mw = MetricsMiddleware(enabled=False)
        handler = AsyncMock(return_value="ok")
        result = await mw.process("ctx", handler)
        assert result == "ok"
        assert mw.get_metrics() == {}

    @pytest.mark.asyncio
    async def test_records_errors(self) -> None:
        mw = MetricsMiddleware(enabled=True)
        handler = AsyncMock(side_effect=RuntimeError("fail"))
        with pytest.raises(RuntimeError):
            await mw.process("ctx", handler)
        metrics = mw.get_metrics()
        assert metrics["total_errors"] == 1


class TestMiddlewarePipeline:
    @pytest.mark.asyncio
    async def test_empty_pipeline(self) -> None:
        pipeline = MiddlewarePipeline()
        handler = AsyncMock(return_value="ok")
        result = await pipeline.execute("ctx", handler)
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_single_middleware(self) -> None:
        mw = MagicMock(spec=AbstractMiddleware)
        mw.enabled = True

        async def process_side(ctx: object, next_handler: object) -> object:
            return await next_handler(ctx)  # type: ignore[no-any-return]

        mw.process = AsyncMock(side_effect=process_side)
        pipeline = MiddlewarePipeline(middlewares=[mw])
        handler = AsyncMock(return_value="result")
        result = await pipeline.execute("ctx", handler)
        assert result == "result"

    @pytest.mark.asyncio
    async def test_disabled_middleware_skipped(self) -> None:
        mw = MagicMock(spec=AbstractMiddleware)
        mw.enabled = False
        pipeline = MiddlewarePipeline(middlewares=[mw])
        handler = AsyncMock(return_value="ok")
        result = await pipeline.execute("ctx", handler)
        assert result == "ok"
        mw.process.assert_not_called()

    @pytest.mark.asyncio
    async def test_add_method(self) -> None:
        pipeline = MiddlewarePipeline()
        mw = MagicMock(spec=AbstractMiddleware)
        mw.enabled = True
        mw.process = AsyncMock(side_effect=lambda ctx, next: next(ctx))
        result = pipeline.add(mw)
        assert result is pipeline


class TestCreateMiddlewarePipeline:
    @pytest.mark.asyncio
    async def test_default_config(self) -> None:
        pipeline = create_middleware_pipeline()
        assert len(pipeline._middlewares) >= 2  # logging + metrics

    @pytest.mark.asyncio
    async def test_with_auth(self) -> None:
        pipeline = create_middleware_pipeline({"logging": True, "auth": True, "metrics": True})
        assert len(pipeline._middlewares) == 3

    @pytest.mark.asyncio
    async def test_all_disabled(self) -> None:
        pipeline = create_middleware_pipeline({"logging": False, "auth": False, "metrics": False})
        assert len(pipeline._middlewares) == 0
