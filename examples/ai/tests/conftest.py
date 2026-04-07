"""Shared pytest fixtures for lexigram-example-ai tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram_example_ai.domain.conversation import Conversation
from lexigram_example_ai.pipelines.chat_pipeline import ChatPipeline, ChatRequest
from lexigram_example_ai.pipelines.rag_pipeline import RAGPipeline, RagQuery


@pytest.fixture()
def stub_completion():
    """Return a minimal completion-like object."""
    completion = MagicMock()
    completion.content = "This is a stub reply."
    completion.model = "stub"
    return completion


@pytest.fixture()
def mock_llm(stub_completion):
    """Stub LLM client that returns Ok(stub_completion) by default."""
    from lexigram.result import Ok

    llm = MagicMock()
    llm.complete = AsyncMock(return_value=Ok(stub_completion))
    return llm


@pytest.fixture()
def mock_token_counter():
    """Stub token counter: 1 token per 4 characters."""
    counter = MagicMock()
    counter.count = MagicMock(side_effect=lambda t: max(1, len(t) // 4))
    counter.count_messages = MagicMock(
        side_effect=lambda msgs: sum(max(1, len(m.content) // 4) for m in msgs)
    )
    return counter


@pytest.fixture()
def mock_embedder():
    """Stub embedding client returning a fixed 4-dim vector."""
    embedder = MagicMock()
    embedder.embed = AsyncMock(return_value=[[0.1, 0.2, 0.3, 0.4]])
    return embedder


@pytest.fixture()
def mock_vector_store():
    """Stub vector store returning an empty hit list by default."""
    from lexigram.result import Ok

    store = MagicMock()
    store.search = AsyncMock(return_value=Ok([]))
    return store


@pytest.fixture()
def chat_pipeline(mock_llm, mock_token_counter):
    """ChatPipeline wired with stub dependencies."""
    return ChatPipeline(
        llm=mock_llm,
        token_counter=mock_token_counter,
        history_token_budget=1000,
    )


@pytest.fixture()
def rag_pipeline(mock_llm, mock_embedder, mock_vector_store):
    """RAGPipeline wired with stub dependencies."""
    return RAGPipeline(
        llm=mock_llm,
        embedder=mock_embedder,
        vector_store=mock_vector_store,
    )


@pytest.fixture()
def empty_conversation():
    """A fresh conversation with no messages."""
    return Conversation.start(title="Test session")
