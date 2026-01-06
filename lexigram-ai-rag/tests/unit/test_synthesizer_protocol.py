"""Tests that synthesizers conform to SynthesizerProtocol."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

from lexigram.ai.rag.synthesis.synthesizers import (
    AbstractiveSynthesizer,
    DirectSynthesizer,
    ExtractiveSynthesizer,
    HybridSynthesizer,
)
from lexigram.contracts.ai.rag import RAGResponse
from lexigram.contracts.ai.vector import SearchResultProtocol


def _make_search_result(text: str, score: float = 0.85, doc_id: str = "doc-1") -> MagicMock:
    """Build a minimal SearchResultProtocol mock.

    Args:
        text: Document text content.
        score: Relevance score.
        doc_id: Document identifier.

    Returns:
        MagicMock satisfying SearchResultProtocol.
    """
    doc = MagicMock()
    type(doc).id = PropertyMock(return_value=doc_id)
    type(doc).text = PropertyMock(return_value=text)
    type(doc).metadata = PropertyMock(return_value={})

    result = MagicMock(spec=SearchResultProtocol)
    type(result).document = PropertyMock(return_value=doc)
    type(result).score = PropertyMock(return_value=score)
    type(result).metadata = PropertyMock(return_value={"source": doc_id})
    return result


def _make_llm_client() -> MagicMock:
    """Build a minimal LLMClientProtocol mock.

    Returns:
        MagicMock with a ``complete`` AsyncMock that returns a completion.
    """
    completion = MagicMock()
    type(completion).content = PropertyMock(return_value="Mocked LLM answer.")
    completion_result = MagicMock()
    completion_result.is_err.return_value = False
    completion_result.unwrap.return_value = completion

    client = MagicMock()
    client.complete = AsyncMock(return_value=completion_result)
    return client


class TestDirectSynthesizerProtocolConformance:
    """DirectSynthesizer satisfies SynthesizerProtocol."""

    @pytest.mark.asyncio
    async def test_synthesize_accepts_search_result_protocol(self) -> None:
        """synthesize() accepts list[SearchResultProtocol]."""
        synthesizer = DirectSynthesizer()
        results = [_make_search_result("Chunk one."), _make_search_result("Chunk two.")]

        outcome = await synthesizer.synthesize("What is X?", results)

        assert outcome.is_ok()

    @pytest.mark.asyncio
    async def test_synthesize_returns_rag_response(self) -> None:
        """synthesize() wraps the answer in RAGResponse."""
        synthesizer = DirectSynthesizer(include_sources=False)
        results = [_make_search_result("Direct answer text.")]

        outcome = await synthesizer.synthesize("query", results)

        assert outcome.is_ok()
        response = outcome.unwrap()
        assert isinstance(response, RAGResponse)
        assert response.answer
        assert response.sources == results

    @pytest.mark.asyncio
    async def test_synthesize_returns_err_on_empty_query(self) -> None:
        """synthesize() returns Err when query is empty."""
        synthesizer = DirectSynthesizer()
        results = [_make_search_result("Some text.")]

        outcome = await synthesizer.synthesize("", results)

        assert outcome.is_err()

    @pytest.mark.asyncio
    async def test_synthesize_returns_err_on_empty_context(self) -> None:
        """synthesize() returns Err when context list is empty."""
        synthesizer = DirectSynthesizer()

        outcome = await synthesizer.synthesize("query", [])

        assert outcome.is_err()


class TestExtractiveSynthesizerProtocolConformance:
    """ExtractiveSynthesizer satisfies SynthesizerProtocol."""

    @pytest.mark.asyncio
    async def test_synthesize_returns_ok_rag_response(self) -> None:
        """synthesize() returns Ok(RAGResponse) with valid input."""
        synthesizer = ExtractiveSynthesizer()
        results = [
            _make_search_result("The sky is blue. It reflects sunlight.", score=0.9),
            _make_search_result("Water boils at 100 degrees Celsius.", score=0.7),
        ]

        outcome = await synthesizer.synthesize("Tell me about nature.", results)

        assert outcome.is_ok()
        response = outcome.unwrap()
        assert isinstance(response, RAGResponse)
        assert response.answer

    @pytest.mark.asyncio
    async def test_synthesize_preserves_source_references(self) -> None:
        """synthesize() sources in RAGResponse match input SearchResults."""
        synthesizer = ExtractiveSynthesizer()
        results = [_make_search_result("Relevant content here.")]

        outcome = await synthesizer.synthesize("query", results)

        assert outcome.is_ok()
        assert outcome.unwrap().sources == results


class TestAbstractiveSynthesizerProtocolConformance:
    """AbstractiveSynthesizer satisfies SynthesizerProtocol."""

    @pytest.mark.asyncio
    async def test_synthesize_returns_ok_rag_response(self) -> None:
        """synthesize() returns Ok(RAGResponse) using LLM client."""
        llm = _make_llm_client()
        synthesizer = AbstractiveSynthesizer(llm_client=llm, include_citations=False)
        results = [_make_search_result("Context for the LLM.")]

        outcome = await synthesizer.synthesize("What is the answer?", results)

        assert outcome.is_ok()
        response = outcome.unwrap()
        assert isinstance(response, RAGResponse)
        assert response.answer == "Mocked LLM answer."

    @pytest.mark.asyncio
    async def test_synthesize_returns_err_when_llm_fails(self) -> None:
        """synthesize() returns Err when LLM raises an exception."""
        llm = MagicMock()
        llm.complete = AsyncMock(side_effect=RuntimeError("LLM unavailable"))
        synthesizer = AbstractiveSynthesizer(llm_client=llm)
        results = [_make_search_result("Some context.")]

        outcome = await synthesizer.synthesize("query", results)

        assert outcome.is_err()


class TestHybridSynthesizerProtocolConformance:
    """HybridSynthesizer satisfies SynthesizerProtocol."""

    @pytest.mark.asyncio
    async def test_synthesize_returns_ok_rag_response(self) -> None:
        """synthesize() returns Ok(RAGResponse) combining extractive + LLM."""
        llm = _make_llm_client()
        synthesizer = HybridSynthesizer(llm_client=llm)
        results = [
            _make_search_result("First piece of context data.", score=0.9),
            _make_search_result("Second piece of context data.", score=0.8),
        ]

        outcome = await synthesizer.synthesize("Explain this.", results)

        assert outcome.is_ok()
        response = outcome.unwrap()
        assert isinstance(response, RAGResponse)
        assert response.answer

    @pytest.mark.asyncio
    async def test_synthesize_confidence_is_none_without_quality_metrics(self) -> None:
        """synthesize() sets confidence=None when no quality_metrics present."""
        synthesizer = DirectSynthesizer()
        results = [_make_search_result("A simple direct answer.")]

        outcome = await synthesizer.synthesize("query", results)

        assert outcome.is_ok()
        assert outcome.unwrap().confidence is None
