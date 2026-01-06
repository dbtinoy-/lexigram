"""Additional tests for ObservableLLMClient wrapper edge cases."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from lexigram.ai.observability.wrappers.observable_llm import ObservableLLMClient
from lexigram.result import Err, Ok


class DummyUsage:
    def __init__(self, total_tokens=None):
        self.total_tokens = total_tokens


class NoCostCompletion:
    def __init__(self):
        self.usage = DummyUsage(total_tokens=100)


class NoUsageCompletion:
    def __init__(self):
        self.cost = 0.01
        self.usage = None


class ZeroCostCompletion:
    def __init__(self):
        self.usage = DummyUsage(total_tokens=100)
        self.cost = 0.0


@pytest.fixture
def mock_tracer():
    tracer = MagicMock()
    ctx_manager = MagicMock()
    ctx_manager.__enter__.return_value = MagicMock()
    ctx_manager.__exit__.return_value = False
    tracer.trace_llm_call.return_value = ctx_manager
    return tracer


@pytest.fixture
def mock_metrics():
    metrics = MagicMock()
    return metrics


@pytest.fixture
def mock_delegate():
    delegate = MagicMock()
    delegate.complete = AsyncMock()
    delegate.stream_chat = MagicMock()
    delegate.health_check = AsyncMock()
    delegate.close = AsyncMock()
    return delegate


class TestObservableLLMClientCostHandling:
    """Tests for various cost attribute handling."""

    @pytest.mark.asyncio
    async def test_complete_no_cost_attribute(self, mock_delegate, mock_tracer, mock_metrics):
        mock_delegate.complete.return_value = Ok(NoCostCompletion())

        client = ObservableLLMClient(
            mock_delegate,
            provider="test",
            model="test",
            tracer=mock_tracer,
            metrics=mock_metrics,
        )

        result = await client.complete([{"role": "user", "content": "hi"}])

        assert result.is_ok()

    @pytest.mark.asyncio
    async def test_complete_no_usage_attribute(self, mock_delegate, mock_tracer, mock_metrics):
        mock_delegate.complete.return_value = Ok(NoUsageCompletion())

        client = ObservableLLMClient(
            mock_delegate,
            provider="test",
            model="test",
            tracer=mock_tracer,
            metrics=mock_metrics,
        )

        result = await client.complete([{"role": "user", "content": "hi"}])

        assert result.is_ok()

    @pytest.mark.asyncio
    async def test_complete_zero_cost(self, mock_delegate, mock_tracer, mock_metrics):
        mock_delegate.complete.return_value = Ok(ZeroCostCompletion())

        client = ObservableLLMClient(
            mock_delegate,
            provider="test",
            model="test",
            tracer=mock_tracer,
            metrics=mock_metrics,
        )

        result = await client.complete([{"role": "user", "content": "hi"}])

        assert result.is_ok()

    @pytest.mark.asyncio
    async def test_complete_with_none_tokens(self, mock_delegate, mock_tracer, mock_metrics):
        class NoneTokensCompletion:
            usage = None

        mock_delegate.complete.return_value = Ok(NoneTokensCompletion())

        client = ObservableLLMClient(
            mock_delegate,
            provider="test",
            model="test",
            tracer=mock_tracer,
            metrics=mock_metrics,
        )

        result = await client.complete([{"role": "user", "content": "hi"}])

        assert result.is_ok()


class TestObservableLLMMisc:
    """Miscellaneous tests."""

    @pytest.mark.asyncio
    async def test_explicit_provider_and_model_passed(self, mock_delegate, mock_tracer, mock_metrics):
        mock_delegate.complete.return_value = Ok(NoCostCompletion())

        client = ObservableLLMClient(
            mock_delegate,
            provider="explicit_provider",
            model="explicit_model",
            tracer=mock_tracer,
            metrics=mock_metrics,
        )

        result = await client.complete([{"role": "user", "content": "hi"}])

        assert result.is_ok()

    @pytest.mark.asyncio
    async def test_metrics_incremented_on_success(self, mock_delegate, mock_metrics):
        mock_delegate.complete.return_value = Ok(NoCostCompletion())

        client = ObservableLLMClient(
            mock_delegate,
            provider="test",
            model="test",
            tracer=None,
            metrics=mock_metrics,
        )

        result = await client.complete([{"role": "user", "content": "hi"}])

        assert result.is_ok()
        mock_metrics.llm_requests_total.increment.assert_called()


class TestObservableLLMStreamEdgeCases:
    """Stream edge cases."""

    @pytest.mark.asyncio
    async def test_stream_none_tracer(self, mock_delegate, mock_metrics):
        from lexigram.contracts.infra import AsyncStream

        async def dummy_stream():
            yield "hello"
            yield "world"

        mock_delegate.stream_chat.return_value = AsyncStream(
            dummy_stream(), error_adapter=lambda e: e
        )

        client = ObservableLLMClient(
            mock_delegate,
            provider="test",
            model="test",
            tracer=None,
            metrics=mock_metrics,
        )

        stream = client.stream_chat([{"role": "user", "content": "hi"}])
        chunks = [chunk async for chunk in stream]
        assert chunks == ["hello", "world"]

    @pytest.mark.asyncio
    async def test_stream_no_metrics(self, mock_delegate, mock_tracer):
        from lexigram.contracts.infra import AsyncStream

        async def dummy_stream():
            yield "test"

        mock_delegate.stream_chat.return_value = AsyncStream(
            dummy_stream(), error_adapter=lambda e: e
        )

        client = ObservableLLMClient(
            mock_delegate,
            provider="test",
            model="test",
            tracer=mock_tracer,
            metrics=None,
        )

        stream = client.stream_chat([{"role": "user", "content": "hi"}])
        chunks = [chunk async for chunk in stream]
        assert chunks == ["test"]