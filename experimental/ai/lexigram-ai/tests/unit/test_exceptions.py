"""Tests for lexigram.intelligence.exceptions module."""

import pytest

pytest.importorskip("lexigram.ai.rag", reason="lexigram-ai-rag not installed")

from lexigram.ai.agents.exceptions import (
    AgentConfigurationError,
    AgentExecutionError,
    ToolExecutionError,
)
from lexigram.ai.llm.exceptions import (
    InvalidRequestError,
    LLMAuthenticationError,
    LLMError,
    LLMRateLimitError,
    ModelNotFoundError,
    TokenLimitError,
)
from lexigram.contracts.ai.agents import AgentError
from lexigram.contracts.ai.session import (
    TaskCancelledError,
    TaskError,
    TaskTimeoutError,
    TaskValidationError,
)
from lexigram.contracts.exceptions import LexigramError
from lexigram.contracts.observability.ai import (
    MetricsCollectionError,
    MonitoringError,
    TracingError,
)

from lexigram.contracts.ai.exceptions import RAGError as ContractsRAGError

# Base alias for backward compat
IntelligenceError = LexigramError
from lexigram.ai.rag.exceptions import (
    AudioLoaderError,
    ChunkingError,
    CLIPEmbeddingError,
    ImageLoaderError,
    MultimodalError,
    PreprocessingError,
    RAGError,
    RetrievalError,
    SynthesisError,
    VideoLoaderError,
)
from lexigram.vector.exceptions import (
    VectorConnectionError as VectorStoreConnectionError,
    VectorError as VectorStoreError,
    VectorTimeoutError as VectorStoreTimeoutError,
    CollectionNotFoundError as VectorStoreNotFoundError,
)


class TestExceptionHierarchy:
    """Test exception class hierarchy and inheritance."""

    def test_base_exception_inheritance(self):
        """Test that IntelligenceError inherits from LexigramError."""
        assert issubclass(IntelligenceError, Exception)

    def test_llm_exceptions_inheritance(self):
        """Test LLM exception inheritance."""
        assert issubclass(LLMError, IntelligenceError)
        assert issubclass(LLMRateLimitError, LLMError)
        assert issubclass(LLMAuthenticationError, LLMError)
        assert issubclass(InvalidRequestError, LLMError)
        assert issubclass(ModelNotFoundError, LLMError)
        assert issubclass(TokenLimitError, LLMError)

    def test_vector_store_exceptions_inheritance(self):
        """Test vector store exception inheritance."""
        assert issubclass(VectorStoreError, LexigramError)
        assert issubclass(VectorStoreConnectionError, VectorStoreError)
        assert issubclass(VectorStoreTimeoutError, VectorStoreError)
        assert issubclass(VectorStoreNotFoundError, VectorStoreError)

    def test_rag_exceptions_inheritance(self):
        """Test RAG exception inheritance."""
        assert issubclass(RAGError, LexigramError)
        assert issubclass(PreprocessingError, RAGError)
        # RetrievalError, SynthesisError, ChunkingError are now imported from
        # contracts; they extend contracts.RAGError (parent of pkg RAGError)
        assert issubclass(RetrievalError, ContractsRAGError)
        assert issubclass(SynthesisError, ContractsRAGError)
        assert issubclass(ChunkingError, ContractsRAGError)

    def test_multimodal_exceptions_inheritance(self):
        """Test multimodal exception inheritance."""
        assert issubclass(MultimodalError, LexigramError)
        assert issubclass(AudioLoaderError, MultimodalError)
        assert issubclass(VideoLoaderError, MultimodalError)
        assert issubclass(ImageLoaderError, MultimodalError)
        assert issubclass(CLIPEmbeddingError, MultimodalError)

    def test_agent_exceptions_inheritance(self):
        """Test agent exception inheritance."""
        assert issubclass(AgentError, IntelligenceError)
        assert issubclass(AgentConfigurationError, AgentError)
        assert issubclass(AgentExecutionError, AgentError)
        assert issubclass(ToolExecutionError, AgentError)

    def test_task_exceptions_inheritance(self):
        """Test task exception inheritance."""
        assert issubclass(TaskError, IntelligenceError)
        assert issubclass(TaskTimeoutError, TaskError)
        assert issubclass(TaskCancelledError, IntelligenceError)
        assert issubclass(TaskValidationError, TaskError)

    def test_monitoring_exceptions_inheritance(self):
        """Test monitoring exception inheritance."""
        assert issubclass(MonitoringError, IntelligenceError)
        assert issubclass(MetricsCollectionError, MonitoringError)
        assert issubclass(TracingError, IntelligenceError)


class TestExceptionInstantiation:
    """Test that exceptions can be instantiated properly."""

    def test_base_exception_creation(self):
        """Test creating base IntelligenceError."""
        exc = IntelligenceError("Test error")
        assert "Test error" in str(exc)
        assert isinstance(exc, Exception)

    def test_llm_exceptions_creation(self):
        """Test creating LLM exceptions."""
        rate_limit = LLMRateLimitError("Rate limit exceeded")
        auth = LLMAuthenticationError("Invalid API key")
        invalid = InvalidRequestError("Invalid parameters")
        model = ModelNotFoundError("Model not found")
        token = TokenLimitError("Token limit exceeded")

        assert all(
            isinstance(exc, LLMError)
            for exc in [rate_limit, auth, invalid, model, token]
        )

    def test_vector_store_exceptions_creation(self):
        """Test creating vector store exceptions."""
        conn = VectorStoreConnectionError("Connection failed")
        timeout = VectorStoreTimeoutError("Operation timed out")
        not_found = VectorStoreNotFoundError("Document not found")

        assert all(
            isinstance(exc, VectorStoreError) for exc in [conn, timeout, not_found]
        )

    def test_rag_exceptions_creation(self):
        """Test creating RAG exceptions."""
        preprocess = PreprocessingError("Preprocessing failed")
        retrieval = RetrievalError("Retrieval failed")
        synthesis = SynthesisError("Synthesis failed")
        chunking = ChunkingError("Chunking failed")

        assert isinstance(preprocess, RAGError)
        # Deduped classes extend contracts.RAGError (parent of pkg RAGError)
        assert all(
            isinstance(exc, ContractsRAGError)
            for exc in [retrieval, synthesis, chunking]
        )

    def test_multimodal_exceptions_creation(self):
        """Test creating multimodal exceptions."""
        audio = AudioLoaderError("Audio loading failed")
        video = VideoLoaderError("Video loading failed")
        image = ImageLoaderError("Image loading failed")
        clip = CLIPEmbeddingError("CLIP embedding failed")

        assert all(
            isinstance(exc, MultimodalError) for exc in [audio, video, image, clip]
        )

    def test_agent_exceptions_creation(self):
        """Test creating agent exceptions."""
        config = AgentConfigurationError("Invalid configuration")
        execution = AgentExecutionError("Execution failed")
        tool = ToolExecutionError("Tool execution failed")

        assert all(isinstance(exc, AgentError) for exc in [config, execution, tool])

    def test_task_exceptions_creation(self):
        """Test creating task exceptions."""
        timeout = TaskTimeoutError("Task timed out")
        cancelled = TaskCancelledError("Task cancelled")
        validation = TaskValidationError("Validation failed")

        assert isinstance(timeout, TaskError)
        assert isinstance(validation, TaskError)
        assert isinstance(cancelled, IntelligenceError)

    def test_monitoring_exceptions_creation(self):
        """Test creating monitoring exceptions."""
        metrics = MetricsCollectionError("Metrics collection failed")
        tracing = TracingError("Tracing failed")

        assert isinstance(metrics, MonitoringError)
        assert isinstance(tracing, IntelligenceError)


class TestExceptionMessages:
    """Test exception messages and string representation."""

    def test_exception_messages(self):
        """Test that exceptions preserve their messages."""
        test_message = "Test error message"
        exc = IntelligenceError(test_message)
        assert test_message in str(exc)

    def test_exception_with_additional_info(self):
        """Test exceptions with additional context."""
        exc = LLMRateLimitError("Rate limit exceeded", details={"retry_after": 60})
        assert "Rate limit exceeded" in str(exc)
        # Test that additional args are preserved
        assert len(exc.args) >= 1
        assert exc.args[0] == "Rate limit exceeded"
