"""Tests for CallbackManagerImpl."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.mark.asyncio
async def test_callback_manager_register():
    """CallbackManager should register handlers."""
    from lexigram.ai.observability.callbacks.manager import CallbackManagerImpl
    
    manager = CallbackManagerImpl()
    handler = MagicMock()
    manager.register(handler)
    assert handler in manager._handlers


@pytest.mark.asyncio
async def test_callback_manager_unregister():
    """CallbackManager should unregister handlers."""
    from lexigram.ai.observability.callbacks.manager import CallbackManagerImpl
    
    manager = CallbackManagerImpl()
    handler = MagicMock()
    manager.register(handler)
    manager.unregister(handler)
    assert handler not in manager._handlers


@pytest.mark.asyncio
async def test_callback_manager_child_inherits_handlers():
    """Child manager should inherit parent's handlers."""
    from lexigram.ai.observability.callbacks.manager import CallbackManagerImpl
    
    manager = CallbackManagerImpl()
    handler = MagicMock()
    manager.register(handler)
    
    child = manager.child("run-123")
    assert handler in child._handlers


@pytest.mark.asyncio
async def test_callback_manager_fanout():
    """CallbackManager should fan out to all registered handlers."""
    from lexigram.ai.observability.callbacks.manager import CallbackManagerImpl
    
    manager = CallbackManagerImpl()
    handler1 = AsyncMock()
    handler2 = AsyncMock()
    manager.register(handler1)
    manager.register(handler2)
    
    await manager.on_llm_start(
        messages=[],
        model="gpt-4",
    )
    
    handler1.on_llm_start.assert_awaited_once()
    handler2.on_llm_start.assert_awaited_once()


@pytest.mark.asyncio
async def test_callback_manager_isolates_handler_failure():
    """Handler failure should not break other handlers."""
    from lexigram.ai.observability.callbacks.manager import CallbackManagerImpl
    
    manager = CallbackManagerImpl()
    
    failing_handler = AsyncMock()
    failing_handler.on_llm_start = AsyncMock(side_effect=RuntimeError("fail"))
    
    working_handler = AsyncMock()
    
    manager.register(failing_handler)
    manager.register(working_handler)
    
    # Should not raise
    await manager.on_llm_start(
        messages=[],
        model="gpt-4",
    )
    
    working_handler.on_llm_start.assert_awaited_once()


def test_aitracer_implements_callback_handler():
    """AITracer should implement CallbackHandlerProtocol."""
    from lexigram.ai.observability.tracing import AITracer
    from lexigram.contracts.ai.callbacks import CallbackHandlerProtocol
    from unittest.mock import MagicMock

    mock_tracer = MagicMock()
    tracer = AITracer(mock_tracer)
    assert isinstance(tracer, CallbackHandlerProtocol)


@pytest.mark.asyncio
async def test_callback_manager_chain_events():
    """CallbackManager should handle multiple event types."""
    from lexigram.ai.observability.callbacks.manager import CallbackManagerImpl

    manager = CallbackManagerImpl()
    handler = AsyncMock()
    manager.register(handler)

    # Test chain start
    await manager.on_chain_start(name="test_chain", inputs={})
    handler.on_chain_start.assert_awaited_once()

    # Test chain end
    await manager.on_chain_end(name="test_chain", outputs={"result": "done"})
    handler.on_chain_end.assert_awaited_once()


@pytest.mark.asyncio
async def test_callback_manager_tool_events():
    """CallbackManager should handle tool events."""
    from lexigram.ai.observability.callbacks.manager import CallbackManagerImpl

    manager = CallbackManagerImpl()
    handler = AsyncMock()
    manager.register(handler)

    # Test tool start
    await manager.on_tool_start(tool_name="search", arguments={"query": "test"})
    handler.on_tool_start.assert_awaited_once()

    # Test tool end
    await manager.on_tool_end(tool_name="search", result={"result": "found"})
    handler.on_tool_end.assert_awaited_once()


@pytest.mark.asyncio
async def test_callback_manager_agent_events():
    """CallbackManager should handle agent events."""
    from lexigram.ai.observability.callbacks.manager import CallbackManagerImpl

    manager = CallbackManagerImpl()
    handler = AsyncMock()
    manager.register(handler)

    # Test agent action
    await manager.on_agent_action(run_id="1", action={"type": "think", "thought": "analyzing"})
    handler.on_agent_action.assert_awaited_once()

    # Test agent finish
    await manager.on_agent_finish(run_id="1", response={"final": "answer"})
    handler.on_agent_finish.assert_awaited_once()


@pytest.mark.asyncio
async def test_callback_manager_retriever_events():
    """CallbackManager should handle retriever events."""
    from lexigram.ai.observability.callbacks.manager import CallbackManagerImpl

    manager = CallbackManagerImpl()
    handler = AsyncMock()
    manager.register(handler)

    # Test retriever start
    await manager.on_retriever_start(run_id="1", query="test query")
    handler.on_retriever_start.assert_awaited_once()

    # Test retriever end
    await manager.on_retriever_end(run_id="1", documents=[{"id": "1", "content": "doc"}])
    handler.on_retriever_end.assert_awaited_once()


@pytest.mark.asyncio
async def test_callback_manager_multiple_handlers_order():
    """Callbacks should fire in registration order."""
    from lexigram.ai.observability.callbacks.manager import CallbackManagerImpl

    manager = CallbackManagerImpl()
    call_order = []

    handler1 = AsyncMock()
    handler1.on_llm_start = AsyncMock(side_effect=lambda *a, **kw: call_order.append(1))

    handler2 = AsyncMock()
    handler2.on_llm_start = AsyncMock(side_effect=lambda *a, **kw: call_order.append(2))

    manager.register(handler1)
    manager.register(handler2)

    await manager.on_llm_start(messages=[], model="gpt-4")

    assert call_order == [1, 2]


@pytest.mark.asyncio
async def test_callback_manager_empty_handlers():
    """CallbackManager should handle empty handlers gracefully."""
    from lexigram.ai.observability.callbacks.manager import CallbackManagerImpl

    manager = CallbackManagerImpl()

    # Should not raise
    await manager.on_llm_start(messages=[], model="gpt-4")
    await manager.on_chain_start(name="chain", inputs={})


@pytest.mark.asyncio
async def test_callback_manager_unregister_missing():
    """Unregister should handle missing handler gracefully."""
    from lexigram.ai.observability.callbacks.manager import CallbackManagerImpl

    manager = CallbackManagerImpl()
    handler = MagicMock()

    # Should not raise
    manager.unregister(handler)


@pytest.mark.asyncio
async def test_callback_manager_double_register():
    """Double register should not duplicate handlers."""
    from lexigram.ai.observability.callbacks.manager import CallbackManagerImpl

    manager = CallbackManagerImpl()
    handler = MagicMock()

    manager.register(handler)
    manager.register(handler)

    assert len(manager._handlers) == 1
