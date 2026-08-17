"""Tests for lexigram.ai.rag.steps module."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.result import Ok

from lexigram.ai.llm.types import Completion, Role
from lexigram.ai.rag.steps.core import (
    GenerateAnswerStep,
    IndexDocumentsStep,
    LoadDocumentsStep,
    RetrieveContextStep,
    SplitDocumentsStep,
    TranslationStep,
)
from lexigram.ai.rag.types import Chunk
from lexigram.contracts.ai.vector import Document, RAGSearchResult as SearchResult
from lexigram.primitives.pipeline import PipelineContext


class TestLoadDocumentsStep:
    """Test LoadDocumentsStep functionality."""

    @pytest.fixture
    def mock_loader(self):
        """Mock document loader."""
        loader = MagicMock()
        return loader

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
        splitter = MagicMock()
        return splitter

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


class TestRetrieveContextStep:
    """Test RetrieveContextStep functionality."""

    @pytest.fixture
    def mock_vector_store(self):
        """Mock vector store."""
        store = MagicMock()
        store.search = AsyncMock(return_value=Ok([]))
        return store

    @pytest.fixture
    def step(self, mock_vector_store):
        """Create RetrieveContextStep."""
        return RetrieveContextStep("retrieve", mock_vector_store, top_k=3)

    @pytest.fixture
    def context(self):
        """Create pipeline context."""
        context = PipelineContext(pipeline_name="test_pipeline")
        context.add_metadata("query", "test query")
        return context

    def test_init(self, mock_vector_store):
        """Test step initialization."""
        step = RetrieveContextStep(
            "retrieve",
            mock_vector_store,
            top_k=10,
            query_key="custom_query",
            filters_key="custom_filters",
        )

        assert step.name == "retrieve"
        assert step.vector_store == mock_vector_store
        assert step.top_k == 10
        assert step.query_key == "custom_query"
        assert step.filters_key == "custom_filters"

    @pytest.mark.asyncio
    async def test_execute_success_from_metadata(
        self, step, mock_vector_store, context,
    ):
        """Test successful retrieval with query from metadata."""
        context.add_metadata("query", "What is AI?")

        mock_results = [
            SearchResult(
                document=Document(text="Result 1", metadata={}), score=0.9, rank=0,
            ),
            SearchResult(
                document=Document(text="Result 2", metadata={}), score=0.8, rank=1,
            ),
        ]
        mock_vector_store.search.return_value = Ok(mock_results)

        result = await step.execute(context)

        assert result.is_ok()
        assert result.unwrap() == mock_results

        # Check context storage
        assert context.get_step_result("retrieve") == mock_results

        # Verify search call
        mock_vector_store.search.assert_called_once_with(
            query="What is AI?",
            top_k=3,
            filters=None,
        )

    @pytest.mark.asyncio
    async def test_execute_success_from_step_result(
        self, step, mock_vector_store, context,
    ):
        """Test successful retrieval with query from step result."""
        context.set_step_result("query", "What is AI?")

        mock_results = [
            SearchResult(
                document=Document(text="Result", metadata={}), score=0.9, rank=0,
            ),
        ]
        mock_vector_store.search.return_value = Ok(mock_results)

        result = await step.execute(context)

        assert result.is_ok()
        assert result.unwrap() == mock_results

    @pytest.mark.asyncio
    async def test_execute_with_filters(self, step, mock_vector_store, context):
        """Test retrieval with filters."""
        context.add_metadata("query", "What is AI?")
        context.add_metadata("filters", {"topic": "ML"})

        step_with_filters = RetrieveContextStep(
            "retrieve",
            mock_vector_store,
            filters_key="filters",
        )

        mock_results = [
            SearchResult(
                document=Document(text="Result", metadata={}), score=0.9, rank=0,
            ),
        ]
        mock_vector_store.search.return_value = Ok(mock_results)

        result = await step_with_filters.execute(context)

        assert result.is_ok()
        mock_vector_store.search.assert_called_once_with(
            query="What is AI?",
            top_k=5,
            filters={"topic": "ML"},
        )

    @pytest.mark.asyncio
    async def test_execute_no_query(self, step, context):
        """Test execution with no query found."""
        # Create fresh context without query
        fresh_context = PipelineContext(pipeline_name="test_pipeline")
        result = await step.execute(fresh_context)

        assert result.is_err()
        assert "No query found" in str(result.unwrap_err())

    @pytest.mark.asyncio
    async def test_execute_vector_store_error(self, step, mock_vector_store, context):
        """Test execution with vector store error."""
        context.add_metadata("query", "What is AI?")
        mock_vector_store.search.side_effect = ConnectionError("Search failed")

        result = await step.execute(context)

        assert result.is_err()
        assert "Search failed" in str(result.unwrap_err())


class TestGenerateAnswerStep:
    """Test GenerateAnswerStep functionality."""

    @pytest.fixture
    def mock_llm(self):
        """Mock LLM client."""
        llm = MagicMock()
        return llm

    @pytest.fixture
    def step(self, mock_llm):
        """Create GenerateAnswerStep."""
        return GenerateAnswerStep("generate", mock_llm)

    @pytest.fixture
    def context(self):
        """Create pipeline context."""
        context = PipelineContext(pipeline_name="test_pipeline")
        context.add_metadata("query", "test query")
        return context

    def test_init(self, mock_llm):
        """Test step initialization."""
        custom_prompt = "Custom system prompt"
        step = GenerateAnswerStep(
            "generate",
            mock_llm,
            query_key="custom_query",
            context_key="custom_context",
            system_prompt=custom_prompt,
        )

        assert step.name == "generate"
        assert step.llm == mock_llm
        assert step.query_key == "custom_query"
        assert step.context_key == "custom_context"
        assert step.system_prompt == custom_prompt

    @pytest.mark.asyncio
    async def test_execute_success(self, step, mock_llm, context):
        """Test successful answer generation."""
        # Set query and context
        context.add_metadata("query", "What is AI?")
        context.set_step_result(
            "retrieve",
            [
                SearchResult(
                    document=Document(
                        text="AI is artificial intelligence", metadata={},
                    ),
                    score=0.9,
                    rank=0,
                ),
                SearchResult(
                    document=Document(text="ML is machine learning", metadata={}),
                    score=0.8,
                    rank=1,
                ),
            ],
        )

        mock_completion = Completion(
            content="AI stands for Artificial Intelligence",
            model="gpt-4",
            usage={"prompt_tokens": 10, "completion_tokens": 8, "total_tokens": 18},
        )
        mock_llm.complete = AsyncMock(return_value=Ok(mock_completion))

        result = await step.execute(context)

        assert result.is_ok()
        assert result.unwrap() == mock_completion

        # Check context storage
        assert context.get_step_result("generate") == mock_completion

        # Verify LLM call
        mock_llm.complete.assert_called_once()
        call_args = mock_llm.complete.call_args[0][0]

        assert len(call_args) == 2
        assert call_args[0].role == Role.SYSTEM
        assert "helpful assistant" in call_args[0].content
        assert call_args[1].role == Role.USER
        assert "Context:" in call_args[1].content
        assert "[1] AI is artificial intelligence" in call_args[1].content
        assert "[2] ML is machine learning" in call_args[1].content
        assert "Question: What is AI?" in call_args[1].content

    @pytest.mark.asyncio
    async def test_execute_no_query(self, step, context):
        """Test execution with no query."""
        # Create fresh context without query
        fresh_context = PipelineContext(pipeline_name="test_pipeline")
        fresh_context.set_step_result(
            "retrieve",
            [
                SearchResult(
                    document=Document(text="Context", metadata={}), score=0.9, rank=0,
                ),
            ],
        )

        result = await step.execute(fresh_context)

        assert result.is_err()
        assert "No query found" in str(result.unwrap_err())

    @pytest.mark.asyncio
    async def test_execute_no_context(self, step, context):
        """Test execution with no context."""
        context.add_metadata("query", "What is AI?")

        result = await step.execute(context)

        assert result.is_err()
        assert "No context found" in str(result.unwrap_err())

    @pytest.mark.asyncio
    async def test_execute_llm_error(self, step, mock_llm, context):
        """Test execution with LLM error."""
        context.add_metadata("query", "What is AI?")
        context.set_step_result(
            "retrieve",
            [
                SearchResult(
                    document=Document(text="Context", metadata={}), score=0.9, rank=0,
                ),
            ],
        )

        mock_llm.complete = AsyncMock(side_effect=ConnectionError("LLM failed"))

        result = await step.execute(context)

        assert result.is_err()
        assert "LLM failed" in str(result.unwrap_err())


class TestTranslationStep:
    """Test TranslationStep functionality."""

    @pytest.fixture
    def mock_llm(self):
        """Mock LLM client."""
        llm = MagicMock()
        return llm

    @pytest.fixture
    def step(self, mock_llm):
        """Create TranslationStep."""
        return TranslationStep("translate", mock_llm, target_language="Spanish")

    @pytest.fixture
    def context(self):
        """Create pipeline context."""
        context = PipelineContext(pipeline_name="test_pipeline")
        context.add_metadata("query", "test query")
        return context

    def test_init(self, mock_llm):
        """Test step initialization."""
        step = TranslationStep(
            "translate",
            mock_llm,
            target_language="French",
            input_key="custom_input",
        )

        assert step.name == "translate"
        assert step.llm == mock_llm
        assert step.target_language == "French"
        assert step.input_key == "custom_input"

    @pytest.mark.asyncio
    async def test_execute_success(self, step, mock_llm, context):
        """Test successful translation."""
        # Set input chunks
        chunks = [
            Chunk(
                text="Hello world",
                source="test.txt",
                chunk_index=0,
                metadata={"lang": "en"},
            ),
            Chunk(
                text="How are you?",
                source="test.txt",
                chunk_index=1,
                metadata={"lang": "en"},
            ),
        ]
        context.set_step_result("split", chunks)

        # Mock LLM responses
        from lexigram.result import Ok

        completion1 = Completion(
            content="Hola mundo",
            model="gpt-4",
            usage={"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
        )
        completion2 = Completion(
            content="¿Cómo estás?",
            model="gpt-4",
            usage={"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
        )
        mock_llm.complete = AsyncMock(side_effect=[Ok(completion1), Ok(completion2)])

        result = await step.execute(context)

        assert result.is_ok()
        translated_chunks = result.unwrap()
        assert len(translated_chunks) == 2

        assert translated_chunks[0].text == "Hola mundo"
        assert translated_chunks[0].metadata["translated"] is True
        assert translated_chunks[0].metadata["target_language"] == "Spanish"
        assert translated_chunks[0].metadata["original_content"] == "Hello world"

        assert translated_chunks[1].text == "¿Cómo estás?"
        assert translated_chunks[1].metadata["translated"] is True

        # Check context storage
        assert context.get_step_result("translate") == translated_chunks

        # Verify LLM calls
        assert mock_llm.complete.call_count == 2

    @pytest.mark.asyncio
    async def test_execute_no_chunks(self, step, context):
        """Test execution with no input chunks."""
        result = await step.execute(context)

        assert result.is_err()
        assert "No chunks found" in str(result.unwrap_err())

    @pytest.mark.asyncio
    async def test_execute_llm_error(self, step, mock_llm, context):
        """Test execution with LLM error."""
        chunks = [Chunk(text="Hello", source="test.txt", chunk_index=0, metadata={})]
        context.set_step_result("split", chunks)

        mock_llm.complete = AsyncMock(side_effect=ConnectionError("Translation failed"))

        result = await step.execute(context)

        assert result.is_err()
        assert "Translation failed" in str(result.unwrap_err())
