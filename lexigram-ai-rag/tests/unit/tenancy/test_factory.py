"""Tests for the TenantScopedRAGPipeline."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.contracts.ai.rag import RAGPipelineProtocol


class TestTenantScopedRAGPipeline:
    """Tests for per-tenant RAG pipeline factory."""

    def _make_factory(self, return_value=None):
        async def factory(config):
            return return_value or MagicMock(spec=RAGPipelineProtocol)
        return factory

    def _make(self, ctx=None, resolver=None, factory=None, config=None):
        from lexigram.ai.rag.config import RAGConfig
        from lexigram.ai.rag.tenancy import TenantScopedRAGPipeline

        cfg = config or RAGConfig(collection_name="canon")
        r = resolver or MagicMock()
        r.resolve.side_effect = lambda name, tid: f"{name}_t_{tid}"
        c = ctx or MagicMock()
        f = factory or self._make_factory()
        return TenantScopedRAGPipeline(
            base_config=cfg,
            resolver=r,
            ctx=c,
            pipeline_factory=f,
        )

    @pytest.mark.asyncio
    async def test_execute_with_tenant_resolves_collection(self) -> None:
        mock_ctx = MagicMock()
        mock_ctx.get.return_value = "t1"
        mock_pipeline = MagicMock(spec=RAGPipelineProtocol)
        mock_pipeline.execute = AsyncMock()
        tracker = {"called": False}

        async def factory(config):
            tracker["called"] = True
            assert config.collection_name == "canon_t_t1"
            return mock_pipeline

        d = self._make(ctx=mock_ctx, factory=factory)
        from lexigram.contracts.ai.rag import RAGContext
        await d.execute(RAGContext(query="test"))
        assert tracker["called"] is True
        mock_pipeline.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_execute_without_tenant_uses_base_config(self) -> None:
        mock_ctx = MagicMock()
        mock_ctx.get.return_value = None
        mock_pipeline = MagicMock(spec=RAGPipelineProtocol)
        mock_pipeline.execute = AsyncMock()

        async def factory(config):
            assert config.collection_name == "canon"
            return mock_pipeline

        d = self._make(ctx=mock_ctx, factory=factory)
        from lexigram.contracts.ai.rag import RAGContext
        await d.execute(RAGContext(query="test"))
        mock_pipeline.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_caches_pipeline_per_tenant(self) -> None:
        mock_ctx = MagicMock()
        mock_pipeline_t1 = MagicMock(spec=RAGPipelineProtocol)
        mock_pipeline_t1.execute = AsyncMock()
        mock_pipeline_t2 = MagicMock(spec=RAGPipelineProtocol)
        mock_pipeline_t2.execute = AsyncMock()

        call_count = 0

        async def factory(config):
            nonlocal call_count
            call_count += 1
            if "t1" in config.collection_name:
                return mock_pipeline_t1
            return mock_pipeline_t2

        d = self._make(ctx=mock_ctx, factory=factory)

        from lexigram.contracts.ai.rag import RAGContext

        # First call with t1 — creates pipeline
        mock_ctx.get.return_value = "t1"
        await d.execute(RAGContext(query="q1"))
        assert call_count == 1

        # Second call with t1 — uses cache
        await d.execute(RAGContext(query="q2"))
        assert call_count == 1  # factory not called again

        # Call with t2 — creates new pipeline
        mock_ctx.get.return_value = "t2"
        await d.execute(RAGContext(query="q3"))
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_query_convenience_raises_on_error(self) -> None:
        mock_ctx = MagicMock()
        mock_ctx.get.return_value = "t1"
        mock_pipeline = MagicMock(spec=RAGPipelineProtocol)
        from lexigram.result import Err
        from lexigram.contracts.ai.exceptions import RAGError
        mock_pipeline.execute = AsyncMock(return_value=Err(RAGError("fail")))

        d = self._make(ctx=mock_ctx, factory=self._make_factory(mock_pipeline))
        with pytest.raises(RAGError, match="fail"):
            await d.query("test")

    @pytest.mark.asyncio
    async def test_query_convenience_returns_response(self) -> None:
        mock_ctx = MagicMock()
        mock_ctx.get.return_value = "t1"
        mock_pipeline = MagicMock(spec=RAGPipelineProtocol)
        from lexigram.contracts.ai.rag import RAGResponse
        from lexigram.result import Ok
        mock_pipeline.execute = AsyncMock(
            return_value=Ok(RAGResponse(answer="hello", sources=[]))
        )

        d = self._make(ctx=mock_ctx, factory=self._make_factory(mock_pipeline))
        resp = await d.query("test")
        assert resp.answer == "hello"

    @pytest.mark.asyncio
    async def test_lru_eviction(self) -> None:
        from lexigram.ai.rag.config import RAGConfig
        from lexigram.ai.rag.tenancy import TenantScopedRAGPipeline

        mock_ctx = MagicMock()
        call_count = 0

        async def factory(config):
            nonlocal call_count
            call_count += 1
            return MagicMock(spec=RAGPipelineProtocol, execute=AsyncMock())

        mock_resolver = MagicMock()
        mock_resolver.resolve.side_effect = lambda name, tid: f"{name}_t_{tid}"

        d = TenantScopedRAGPipeline(
            base_config=RAGConfig(),
            resolver=mock_resolver,
            ctx=mock_ctx,
            pipeline_factory=factory,
            cache_size=2,
        )

        from lexigram.contracts.ai.rag import RAGContext

        # Fill cache with 3 different tenants
        for tid in ["t1", "t2", "t1", "t3"]:
            mock_ctx.get.return_value = tid
            await d.execute(RAGContext(query="test"))

        # t3 caused eviction; t1 was used twice (not evicted?)
        # With LRU, after t1, t2, t1: the order is [t2, t1]
        # t3 evicts t2. So call_count = 3 (t1, t2, t3)
        assert call_count == 3

    def test_implements_pipeline_protocol(self) -> None:
        d = self._make()
        assert isinstance(d, RAGPipelineProtocol)
