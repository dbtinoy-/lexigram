"""Unit tests for RAG types."""

from __future__ import annotations

import pytest


class TestRagTypesExports:
    """Test module exports."""

    def test_chunk_exported(self) -> None:
        from lexigram.ai.rag.types import Chunk

        assert Chunk is not None

    def test_context_exported(self) -> None:
        from lexigram.ai.rag.types import Context

        assert Context is not None

    def test_rag_error_exported(self) -> None:
        from lexigram.ai.rag.types import RAGError

        assert RAGError is not None


class TestContextDataclass:
    """Test Context dataclass."""

    def test_context_creation_with_required_fields(self) -> None:
        from lexigram.ai.rag.types import Context

        context = Context(
            query="test query",
            documents=[],
        )

        assert context.query == "test query"
        assert context.documents == []

    def test_context_creation_with_all_fields(self) -> None:
        from lexigram.ai.rag.types import Context
        from lexigram.contracts.ai.vector import Document

        doc = Document(id="doc1", text="test content", metadata={})
        context = Context(
            query="test query",
            documents=[doc],
            metadata={"retrieval_time": 0.123},
        )

        assert context.query == "test query"
        assert len(context.documents) == 1
        assert context.metadata["retrieval_time"] == 0.123

    def test_context_default_metadata(self) -> None:
        from lexigram.ai.rag.types import Context

        context = Context(query="test", documents=[])

        assert context.metadata == {}


class TestChunkImport:
    """Test Chunk import from chunking module."""

    def test_chunk_imported_from_types(self) -> None:
        from lexigram.ai.rag.types import Chunk

        assert Chunk is not None

    def test_chunk_has_expected_attributes(self) -> None:
        from lexigram.ai.rag.types import Chunk

        chunk = Chunk(text="test text", chunk_index=0)

        assert chunk.text == "test text"
        assert chunk.chunk_index == 0

    def test_chunk_len(self) -> None:
        from lexigram.ai.rag.types import Chunk

        chunk = Chunk(text="hello", chunk_index=0)

        assert len(chunk) == 5


class TestRAGErrorImport:
    """Test RAGError import."""

    def test_rag_error_is_exception(self) -> None:
        from lexigram.ai.rag.types import RAGError

        assert issubclass(RAGError, Exception)

    def test_rag_error_can_be_raised(self) -> None:
        from lexigram.ai.rag.types import RAGError

        with pytest.raises(RAGError):
            raise RAGError("test error")