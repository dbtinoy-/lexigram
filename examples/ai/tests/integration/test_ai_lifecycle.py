"""Integration test: full AI pipeline lifecycle.

Verifies that the domain model, chat pipeline, and RAG pipeline compose
correctly end-to-end without a real LLM or vector store.  The stub
backends provided by :class:`~lexigram_example_ai.di.provider.AIProvider`
are used throughout.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.result import Ok
from lexigram_example_ai.di.provider import AIProvider
from lexigram_example_ai.domain.conversation import Conversation, MessageRole
from lexigram_example_ai.pipelines.chat_pipeline import ChatPipeline, ChatRequest
from lexigram_example_ai.pipelines.rag_pipeline import RAGPipeline, RagQuery
from lexigram_example_ai.tools.summarise_tool import SummariseTool


def _stub_completion(text: str = "stub reply", model: str = "stub") -> MagicMock:
    c = MagicMock()
    c.content = text
    c.model = model
    return c


@pytest.mark.asyncio
async def test_conversation_starts_and_chat_pipeline_runs():
    """Conversation domain events are collected and the pipeline replies."""
    # Arrange
    llm = MagicMock()
    llm.complete = AsyncMock(return_value=Ok(_stub_completion("Hello from AI!")))
    token_counter = MagicMock()
    token_counter.count = MagicMock(return_value=5)
    token_counter.count_messages = MagicMock(return_value=10)

    pipeline = ChatPipeline(llm=llm, token_counter=token_counter)
    conv = Conversation.start(title="integration test")

    # Verify domain event was emitted
    events = conv.pop_events()
    assert len(events) == 1
    assert events[0].__class__.__name__ == "ConversationStarted"

    # Act
    request = ChatRequest(conversation=conv, user_message="Hello!")
    result = await pipeline.run(request)

    # Assert
    assert result.is_ok()
    resp = result.unwrap()
    assert resp.content == "Hello from AI!"
    assert resp.conversation_id == conv.id

    # Append to conversation
    conv.add_message(role=MessageRole.USER, content="Hello!")
    conv.add_message(role=MessageRole.ASSISTANT, content=resp.content)
    assert conv.message_count == 2
    assert conv.last_message is not None
    assert conv.last_message.content == "Hello from AI!"


@pytest.mark.asyncio
async def test_rag_pipeline_lifecycle():
    """RAG pipeline: embed → retrieve (empty) → synthesise."""
    llm = MagicMock()
    llm.complete = AsyncMock(return_value=Ok(_stub_completion("Lexigram summary")))
    embedder = MagicMock()
    embedder.embed = AsyncMock(return_value=[[0.1, 0.2, 0.3, 0.4]])
    vector_store = MagicMock()
    vector_store.search = AsyncMock(return_value=Ok([]))

    pipeline = RAGPipeline(llm=llm, embedder=embedder, vector_store=vector_store)
    result = await pipeline.run(RagQuery(query="What is Lexigram?", top_k=3))

    assert result.is_ok()
    answer = result.unwrap()
    assert answer.answer == "Lexigram summary"
    assert answer.query == "What is Lexigram?"
    assert answer.sources == []


@pytest.mark.asyncio
async def test_summarise_tool_delegates_to_rag_pipeline():
    """SummariseTool wraps the RAG pipeline and returns the answer text."""
    llm = MagicMock()
    llm.complete = AsyncMock(return_value=Ok(_stub_completion("tool answer")))
    embedder = MagicMock()
    embedder.embed = AsyncMock(return_value=[[0.0, 0.0, 0.0, 0.0]])
    vector_store = MagicMock()
    vector_store.search = AsyncMock(return_value=Ok([]))

    pipeline = RAGPipeline(llm=llm, embedder=embedder, vector_store=vector_store)
    tool = SummariseTool(pipeline=pipeline, top_k=2)

    result = await tool.run("summarise Lexigram")

    assert result.is_ok()
    assert result.unwrap() == "tool answer"


@pytest.mark.asyncio
async def test_multi_turn_conversation():
    """Multi-turn conversation accumulates history between requests."""
    llm = MagicMock()
    llm.complete = AsyncMock(
        side_effect=[
            Ok(_stub_completion("First reply")),
            Ok(_stub_completion("Second reply")),
        ]
    )
    token_counter = MagicMock()
    token_counter.count = MagicMock(return_value=5)
    token_counter.count_messages = MagicMock(return_value=15)

    pipeline = ChatPipeline(llm=llm, token_counter=token_counter)
    conv = Conversation.start()

    # Turn 1
    r1 = await pipeline.run(ChatRequest(conversation=conv, user_message="Turn 1"))
    assert r1.is_ok()
    conv.add_message(role=MessageRole.USER, content="Turn 1")
    conv.add_message(role=MessageRole.ASSISTANT, content=r1.unwrap().content)

    # Turn 2
    r2 = await pipeline.run(ChatRequest(conversation=conv, user_message="Turn 2"))
    assert r2.is_ok()
    assert r2.unwrap().content == "Second reply"

    # Verify history was included in second call
    second_call_messages = llm.complete.call_args_list[1][0][0]
    history_contents = [m.content for m in second_call_messages]
    assert "Turn 1" in history_contents


__all__: list[str] = []
