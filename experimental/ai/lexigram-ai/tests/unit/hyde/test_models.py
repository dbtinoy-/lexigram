"""Tests for HyDE data models."""

import pytest
pytest.importorskip("lexigram.ai.rag", reason="lexigram-ai-rag not installed")

from lexigram.ai.rag.hyde import HyDEResult, HyDEStrategy, HypotheticalDocument


class TestDataModels:
    """Tests for HyDE data models."""

    def test_hypothetical_document_creation(self):
        doc = HypotheticalDocument(
            content="Test content",
            query="test query",
            confidence=0.9,
        )

        assert doc.content == "Test content"
        assert doc.query == "test query"
        assert doc.confidence == 0.9
        assert "timestamp" in doc.__dict__

    def test_hypothetical_document_repr(self):
        doc = HypotheticalDocument(
            content="Test content here",
            query="query",
            confidence=0.85,
        )

        repr_str = repr(doc)
        assert "length=17" in repr_str
        assert "confidence=0.85" in repr_str

    def test_hyde_result_creation(self):
        doc = HypotheticalDocument(
            content="Test",
            query="query",
        )

        result = HyDEResult(
            query="query",
            hypothetical_docs=[doc],
            strategy=HyDEStrategy.SINGLE,
        )

        assert result.query == "query"
        assert result.num_documents == 1
        assert result.strategy == HyDEStrategy.SINGLE

    def test_hyde_result_properties(self):
        docs = [
            HypotheticalDocument("Doc 1", "query", confidence=1.0),
            HypotheticalDocument("Doc 2", "query", confidence=0.8),
            HypotheticalDocument("Doc 3", "query", confidence=0.6),
        ]

        result = HyDEResult(
            query="query",
            hypothetical_docs=docs,
            strategy=HyDEStrategy.MULTIPLE,
        )

        assert result.num_documents == 3
        assert result.avg_confidence == pytest.approx(0.8, abs=0.01)
        assert result.total_length == 15

    def test_hyde_result_empty(self):
        result = HyDEResult(
            query="query",
            hypothetical_docs=[],
            strategy=HyDEStrategy.SINGLE,
        )

        assert result.num_documents == 0
        assert result.avg_confidence == 0.0
        assert result.total_length == 0
