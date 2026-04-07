"""Tests for ObservableLLMClient."""

from unittest.mock import AsyncMock, MagicMock

import pytest

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
    """Mock AITracer instance."""
    tracer = MagicMock()
    ctx_manager = MagicMock()
    ctx_manager.__enter__.return_value = MagicMock()
    ctx_manager.__exit__.return_value = False
    tracer.trace_llm_call.return_value = ctx_manager
    return tracer


@pytest.fixture
def mock_metrics():
    """Mock AIMetrics instance."""
    return MagicMock()


@pytest.fixture
def mock_audit_store():
    """Mock AIAuditStore instance."""
    audit_store = MagicMock()
    audit_store.record = AsyncMock()
    return audit_store


@pytest.fixture
def mock_delegate():
    """Mock LLMClientProtocol."""
    delegate = MagicMock()
    delegate.complete = AsyncMock()
    delegate.stream_chat = MagicMock()  # Not async anymore
    delegate.health_check = AsyncMock()
    delegate.close = AsyncMock()
    return delegate


@pytest.mark.asyncio
async def test_observable_llm_complete_success(
    mock_delegate, mock_tracer, mock_metrics, mock_audit_store
):
    mock_delegate.complete.return_value = Ok(DummyCompletion())

    client = ObservableLLMClient(
        mock_delegate,
        provider="test_provider",
        model="test_model",
        tracer=mock_tracer,
        metrics=mock_metrics,
        audit_store=mock_audit_store,
    )

    result = await client.complete([{"role": "user", "content": "hi"}])

    assert result.is_ok()
    completion = result.unwrap()
    assert completion.content == "Hello"

    mock_metrics.llm_active_requests.increment.assert_called()
    mock_metrics.llm_active_requests.decrement.assert_called()
    mock_metrics.llm_duration_seconds.observe.assert_called()
    mock_metrics.llm_tokens_total.increment.assert_called()
    mock_metrics.llm_cost_dollars.increment.assert_called()

    mock_tracer.trace_llm_call.assert_called_once_with("test_provider", "test_model")


@pytest.mark.asyncio
async def test_observable_llm_complete_err_result(
    mock_delegate, mock_tracer, mock_metrics, mock_audit_store
):
    mock_delegate.complete.return_value = Err(ValueError("API Error"))

    client = ObservableLLMClient(
        mock_delegate,
        provider="test_provider",
        model="test_model",
        tracer=mock_tracer,
        metrics=mock_metrics,
        audit_store=mock_audit_store,
    )

    result = await client.complete([{"role": "user", "content": "hi"}])

    assert result.is_err()
    mock_metrics.llm_requests_total.increment.assert_called()


@pytest.mark.asyncio
async def test_observable_llm_complete_exception(
    mock_delegate, mock_tracer, mock_metrics, mock_audit_store
):
    mock_delegate.complete.side_effect = RuntimeError("Catastrophic chunk failure")

    client = ObservableLLMClient(
        mock_delegate,
        provider="test_provider",
        model="test_model",
        tracer=mock_tracer,
        metrics=mock_metrics,
        audit_store=mock_audit_store,
    )

    with pytest.raises(RuntimeError):
        await client.complete([{"role": "user", "content": "hi"}])


@pytest.mark.asyncio
async def test_observable_llm_stream_chat_success(
    mock_delegate, mock_tracer, mock_metrics
):
    from lexigram.contracts.infra import AsyncStream

    async def dummy_stream():
        yield "Hello"
        yield " World"

    # stream_chat() is not async and returns AsyncStream directly
    mock_delegate.stream_chat.return_value = AsyncStream(
        dummy_stream(), error_adapter=lambda e: e
    )

    client = ObservableLLMClient(
        mock_delegate,
        provider="test_provider",
        model="test_model",
        tracer=mock_tracer,
        metrics=mock_metrics,
    )

    # stream_chat() is not async anymore
    stream = client.stream_chat([{"role": "user", "content": "hi"}])

    chunks = [chunk async for chunk in stream]
    assert chunks == ["Hello", " World"]

    mock_tracer.trace_llm_call.assert_called_once_with(
        "test_provider", "test_model", streaming=True
    )


@pytest.mark.asyncio
async def test_observable_llm_stream_chat_mid_stream_failure(
    mock_delegate, mock_tracer, mock_metrics
):
    """Verify mid-stream LLMError is preserved through wrapper."""
    from lexigram.contracts.ai.exceptions import LLMError
    from lexigram.contracts.infra import AsyncStream

    class TestLLMError(LLMError):
        """Specific LLM error for testing."""

    async def failing_stream():
        yield "Hello"
        raise TestLLMError("Mid-stream failure")

    # Delegate returns properly typed AsyncStream with LLMError adapter
    mock_delegate.stream_chat.return_value = AsyncStream(
        failing_stream(),
        error_adapter=lambda e: e if isinstance(e, LLMError) else LLMError(str(e)),
    )

    client = ObservableLLMClient(
        mock_delegate,
        provider="test_provider",
        model="test_model",
        tracer=mock_tracer,
        metrics=mock_metrics,
    )

    stream = client.stream_chat([{"role": "user", "content": "hi"}])

    # Collect should preserve the typed error
    result = await stream.collect()
    assert result.is_err()
    error = result.unwrap_err()
    assert isinstance(error, LLMError)
    assert isinstance(error, TestLLMError)
    assert "Mid-stream failure" in str(error)


@pytest.mark.asyncio
async def test_observable_llm_delagates(mock_delegate):
    client = ObservableLLMClient(mock_delegate, provider="test", model="test")

    await client.health_check(timeout=1.0)
    mock_delegate.health_check.assert_awaited_once_with(timeout=1.0)

    await client.close()
    mock_delegate.close.assert_awaited_once()
