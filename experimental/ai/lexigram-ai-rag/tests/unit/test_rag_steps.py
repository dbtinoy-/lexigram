"""Tests for lexigram.ai.rag.steps module."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.ai.rag.steps.core import (
    IndexDocumentsStep,
    LoadDocumentsStep,
    SplitDocumentsStep,
)
from lexigram.ai.rag.types import Chunk
from lexigram.contracts.ai.vector import Document
from lexigram.primitives.pipeline import PipelineContext
from lexigram.result import Ok


class TestLoadDocumentsStep:
    """Test LoadDocumentsStep functionality."""

    @pytest.fixture
    def mock_loader(self):
        """Mock document loader."""
        return MagicMock()

    @pytest.fixture
    def step(self, mock_loader):
        """Create LoadDocumentsStep."""
        return LoadDocumentsStep("load", mock_loader)

    @pytest.fixture
    def context(self):
        """Create pipeline context."""
        context = PipelineContext(pipeline_name="test_pipeline")
        context.add_metadata("query", "test query")
        return context

    def test_init(self, mock_loader):
        """Test step initialization."""
        step = LoadDocumentsStep("load", mock_loader, source_key="custom_source")

        assert step.name == "load"
        assert step.loader == mock_loader
        assert step.source_key == "custom_source"
        assert step.dependencies == []

    @pytest.mark.asyncio
    async def test_execute_success_from_metadata(self, step, mock_loader, context):
        """Test successful execution with source from metadata."""
        # Set source in metadata
        context.add_metadata("source", "/path/to/docs")

        # Mock loader response
        mock_chunks = [
            Chunk(text="Test content", source="test.txt", chunk_index=0, metadata={}),
        ]
        mock_loader.load = AsyncMock(return_value=mock_chunks)

        result = await step.execute(context)

        assert result.is_ok()
        assert result.unwrap() == mock_chunks
        mock_loader.load.assert_called_once_with("/path/to/docs")

        # Check context storage
        assert context.get_step_result("load") == mock_chunks

    @pytest.mark.asyncio
    async def test_execute_success_from_step_result(self, step, mock_loader, context):
        """Test successful execution with source from step result."""
        # Set source in step result
        context.set_step_result("source", "/path/to/docs")

        mock_chunks = [
            Chunk(text="Test content", source="test.txt", chunk_index=0, metadata={}),
        ]
        mock_loader.load = AsyncMock(return_value=mock_chunks)

        result = await step.execute(context)

        assert result.is_ok()
        assert result.unwrap() == mock_chunks

    @pytest.mark.asyncio
    async def test_execute_no_source(self, step, context):
        """Test execution with no source found."""
        result = await step.execute(context)

        assert result.is_err()
        assert "No source found" in str(result.unwrap_err())

    @pytest.mark.asyncio
    async def test_execute_loader_error(self, step, mock_loader, context):
        """Test execution with loader error."""
        context.add_metadata("source", "/path/to/docs")
        mock_loader.load.side_effect = OSError("Load failed")

        result = await step.execute(context)

        assert result.is_err()
        assert "Load failed" in str(result.unwrap_err())


class TestSplitDocumentsStep:
    """Test SplitDocumentsStep functionality."""

    @pytest.fixture
    def mock_splitter(self):
        """Mock text splitter."""
        return MagicMock()

    @pytest.fixture
    def step(self, mock_splitter):
        """Create SplitDocumentsStep."""
        return SplitDocumentsStep("split", mock_splitter)

    @pytest.fixture
    def context(self):
        """Create pipeline context."""
        context = PipelineContext(pipeline_name="test_pipeline")
        context.add_metadata("query", "test query")
        return context

    def test_init(self, mock_splitter):
        """Test step initialization."""
        step = SplitDocumentsStep("split", mock_splitter, input_key="custom_input")

        assert step.name == "split"
        assert step.chunker == mock_splitter
        assert step.input_key == "custom_input"

    @pytest.mark.asyncio
    async def test_execute_success(self, step, mock_splitter, context):
        """Test successful document splitting."""
        # Set input documents
        docs = [
            Chunk(
                text="Doc 1 content",
                source="doc1.txt",
                chunk_index=0,
                metadata={"doc": 1},
            ),
            Chunk(
                text="Doc 2 content",
                source="doc2.txt",
                chunk_index=0,
                metadata={"doc": 2},
            ),
        ]
        context.set_step_result("load", docs)

        # Mock splitter responses
        chunks1 = [
            Chunk(
                text="Chunk 1",
                source="doc1.txt",
                chunk_index=1,
                metadata={"doc": 1, "chunk": 1},
            ),
        ]
        chunks2 = [
            Chunk(
                text="Chunk 2",
                source="doc2.txt",
                chunk_index=1,
                metadata={"doc": 2, "chunk": 1},
            ),
        ]
        mock_splitter.chunk.side_effect = [chunks1, chunks2]

        result = await step.execute(context)

        assert result.is_ok()
        all_chunks = result.unwrap()
        assert len(all_chunks) == 2
        assert all_chunks[0].text == "Chunk 1"
        assert all_chunks[1].text == "Chunk 2"

        # Check context storage
        assert context.get_step_result("split") == all_chunks

        # Verify chunker calls
        assert mock_splitter.chunk.call_count == 2

    @pytest.mark.asyncio
    async def test_execute_no_input(self, step, context):
        """Test execution with no input documents."""
        result = await step.execute(context)

        assert result.is_err()
        assert "No documents found" in str(result.unwrap_err())

    @pytest.mark.asyncio
    async def test_execute_chunker_error(self, step, mock_splitter, context):
        """Test execution with chunker error."""
        docs = [Chunk(text="Content", source="test.txt", chunk_index=0, metadata={})]
        context.set_step_result("load", docs)

        mock_splitter.chunk.side_effect = OSError("Chunk failed")

        result = await step.execute(context)

        assert result.is_err()
        assert "Chunk failed" in str(result.unwrap_err())


class TestIndexDocumentsStep:
    """Test IndexDocumentsStep functionality."""

    @pytest.fixture
    def mock_vector_store(self):
        """Mock vector store."""
        store = MagicMock()
        store.add = AsyncMock(return_value=Ok(None))
        store.search = AsyncMock()
        return store

    @pytest.fixture
    def step(self, mock_vector_store):
        """Create IndexDocumentsStep."""
        return IndexDocumentsStep("index", mock_vector_store)

    @pytest.fixture
    def context(self):
        """Create pipeline context."""
        context = PipelineContext(pipeline_name="test_pipeline")
        context.add_metadata("query", "test query")
        return context

    def test_init(self, mock_vector_store):
        """Test step initialization."""
        step = IndexDocumentsStep("index", mock_vector_store, input_key="custom_chunks")

        assert step.name == "index"
        assert step.vector_store == mock_vector_store
        assert step.input_key == "custom_chunks"

    @pytest.mark.asyncio
    async def test_execute_success(self, step, mock_vector_store, context):
        """Test successful document indexing."""
        # Set input chunks
        chunks = [
            Chunk(
                text="Chunk 1",
                source="doc1.txt",
                chunk_index=0,
                metadata={"source": "doc1"},
            ),
            Chunk(
                text="Chunk 2",
                source="doc2.txt",
                chunk_index=0,
                metadata={"source": "doc2"},
            ),
        ]
        context.set_step_result("split", chunks)

        result = await step.execute(context)

        assert result.is_ok()
        assert result.unwrap() == 2

        # Check context storage
        assert context.get_step_result("index") == 2

        # Verify vector store call
        mock_vector_store.add.assert_called_once()
        call_args = mock_vector_store.add.call_args[0][0]
        assert len(call_args) == 2
        assert isinstance(call_args[0], Document)
        assert call_args[0].text == "Chunk 1"
        assert call_args[0].metadata == {"source": "doc1"}

    @pytest.mark.asyncio
    async def test_execute_no_chunks(self, step, context):
        """Test execution with no input chunks."""
        result = await step.execute(context)

        assert result.is_err()
        assert "No chunks found" in str(result.unwrap_err())

    @pytest.mark.asyncio
    async def test_execute_vector_store_error(self, step, mock_vector_store, context):
        """Test execution with vector store error."""
        chunks = [Chunk(text="Content", source="test.txt", chunk_index=0, metadata={})]
        context.set_step_result("split", chunks)

        mock_vector_store.add.side_effect = ConnectionError("Index failed")

        result = await step.execute(context)

        assert result.is_err()
        assert "Index failed" in str(result.unwrap_err())


