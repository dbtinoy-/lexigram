"""Tests for ObservableLLMClient additional edge cases."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from lexigram.ai.observability.wrappers.observable_llm import ObservableLLMClient
from lexigram.result import Err, Ok


class DummyUsage:
    def __init__(self, prompt_tokens=10, completion_tokens=20, total_tokens=30):
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = total_tokens


class DummyCompletion:
    def __init__(self, content="Hello", cost=0.01):
        self.content = content
        self.usage = DummyUsage()
        self.cost = cost


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


class TestObservableLLMClientEdgeCases:
    """Additional edge case tests."""

    @pytest.mark.asyncio
    async def test_complete_without_tracer(self, mock_delegate, mock_metrics):
        mock_delegate.complete.return_value = Ok(DummyCompletion())

        client = ObservableLLMClient(
            mock_delegate,
            provider="test",
            model="test",
            tracer=None,
            metrics=mock_metrics,
        )

        result = await client.complete([{"role": "user", "content": "hi"}])

        assert result.is_ok()

    @pytest.mark.asyncio
    async def test_complete_without_metrics(self, mock_delegate, mock_tracer):
        mock_delegate.complete.return_value = Ok(DummyCompletion())

        client = ObservableLLMClient(
            mock_delegate,
            provider="test",
            model="test",
            tracer=mock_tracer,
            metrics=None,
        )

        result = await client.complete([{"role": "user", "content": "hi"}])

        assert result.is_ok()

    @pytest.mark.asyncio
    async def test_complete_no_usage_attribute(self, mock_delegate, mock_tracer, mock_metrics):
        mock_delegate.complete.return_value = Ok(object())

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
    async def test_complete_no_cost_attribute(self, mock_delegate, mock_tracer, mock_metrics):
        class NoCostResult:
            pass

        mock_delegate.complete.return_value = Ok(NoCostResult())

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
    async def test_stream_chat_no_tracer(self, mock_delegate, mock_metrics):
        from lexigram.contracts.infra import AsyncStream

        async def dummy_stream():
            yield "hello"

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
        assert chunks == ["hello"]

    @pytest.mark.asyncio
    async def test_delegate_health_check_forwarded(self, mock_delegate):
        client = ObservableLLMClient(mock_delegate, provider="test", model="test")

        await client.health_check(timeout=3.0)
        mock_delegate.health_check.assert_awaited_once_with(timeout=3.0)

    @pytest.mark.asyncio
    async def test_delegate_close_forwarded(self, mock_delegate):
        client = ObservableLLMClient(mock_delegate, provider="test", model="test")

        await client.close()
        mock_delegate.close.assert_awaited_once()