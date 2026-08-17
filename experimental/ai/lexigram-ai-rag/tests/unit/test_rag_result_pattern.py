"""Tests for Result pattern in RAG pipeline."""

import pytest
from lexigram.contracts.ai.exceptions import RAGError
from lexigram.ai.rag.services.result_pattern_service import RAGPipelineWithResultPattern

class TestRAGPipelineResultPattern:
    """Test Result pattern in RAG pipeline."""

    @pytest.fixture
    def rag_pipeline(self) -> RAGPipelineWithResultPattern:
        """Create RAG pipeline."""
        return RAGPipelineWithResultPattern(chunk_size=512, chunk_overlap=50, max_retrieved_docs=5)

    @pytest.fixture
    def mock_documents(self) -> list[dict]:
        """Create mock documents."""
        return [
            {"id": "doc1", "content": "Python is a programming language", "metadata": {}},
            {"id": "doc2", "content": "RAG systems retrieve relevant documents", "metadata": {}},
        ]

    @pytest.mark.asyncio
    async def test_preprocess_documents_returns_ok(self, rag_pipeline, mock_documents):
        """Verify preprocess_documents returns Ok."""
        result = await rag_pipeline.preprocess_documents(mock_documents)
        assert result.is_ok()
        docs = result.unwrap()
        assert len(docs) == 2

    @pytest.mark.asyncio
    async def test_preprocess_documents_returns_err_for_empty(self, rag_pipeline):
        """Verify preprocess_documents returns Err for empty list."""
        result = await rag_pipeline.preprocess_documents([])
        assert result.is_err()
        assert isinstance(result.unwrap_err(), RAGError)

    @pytest.mark.asyncio
    async def test_retrieve_documents_returns_ok(self, rag_pipeline):
        """Verify retrieve_documents returns Ok."""
        result = await rag_pipeline.retrieve_documents("What is Python?")
        assert result.is_ok()
        docs = result.unwrap()
        assert isinstance(docs, list)

    @pytest.mark.asyncio
    async def test_retrieve_documents_returns_err_for_empty_query(self, rag_pipeline):
        """Verify retrieve_documents returns Err for empty query."""
        result = await rag_pipeline.retrieve_documents("")
        assert result.is_err()

    @pytest.mark.asyncio
    async def test_synthesize_returns_ok(self, rag_pipeline, mock_documents):
        """Verify synthesize returns Ok."""
        result = await rag_pipeline.synthesize("What is RAG?", mock_documents)
        assert result.is_ok()
        answer = result.unwrap()
        assert isinstance(answer, str)

    @pytest.mark.asyncio
    async def test_synthesize_returns_err_for_empty_query(self, rag_pipeline, mock_documents):
        """Verify synthesize returns Err for empty query."""
        result = await rag_pipeline.synthesize("", mock_documents)
        assert result.is_err()

    @pytest.mark.asyncio
    async def test_process_full_pipeline_returns_ok(self, rag_pipeline, mock_documents):
        """Verify process full pipeline returns Ok."""
        result = await rag_pipeline.process("What is Python?", mock_documents)
        assert result.is_ok()
        pipeline_result = result.unwrap()
        assert "query" in pipeline_result
        assert "context_documents" in pipeline_result
        assert "answer" in pipeline_result

    @pytest.mark.asyncio
    async def test_process_returns_err_for_empty_query(self, rag_pipeline):
        """Verify process returns Err for empty query."""
        result = await rag_pipeline.process("")
        assert result.is_err()
