"""Integration tests for RAG pipeline using Ollama.

Tests end-to-end RAG functionality with real Ollama models.
Requires Ollama running with appropriate models.
"""

import pytest

try:
    import pytest_asyncio
except ImportError:
    pytest_asyncio = None

from lexigram.ai.llm.config import ClientConfig
from lexigram.ai.config import VectorConfig
from lexigram.ai.llm.clients.ollama import OllamaClient
from lexigram.ai.llm.types import ChatMessage, Role
from lexigram.vector.backends.chroma import ChromaStore
from lexigram.contracts.ai.vector import Document, RAGSearchResult

SearchResult = RAGSearchResult


@pytest.mark.skip(
    reason="Skipping RAG Ollama integration tests due to resource limitations with local LLM models",
)
class TestRAGOllamaIntegration:
    """Integration tests for RAG with Ollama."""

    @ pytest.fixture if pytest_asyncio is None else pytest_asyncio.fixture
    async def ollama_llm_client(self):
        """Ollama LLM client fixture."""
        config = ClientConfig(
            provider="ollama",
            model="qwen2.5-coder:32b-instruct-q4_K_M",
            api_base="http://localhost:11434",
            temperature=0.1,
            max_tokens=200,
        )
        client = OllamaClient(config)
        yield client
        await client.close()

    @ pytest.fixture if pytest_asyncio is None else pytest_asyncio.fixture
    async def chroma_store(self):
        """ChromaDB vector store fixture."""
        config = VectorConfig(
            provider="chroma",
            collection_name="test_rag_collection",
            dimension=768,  # nomic-embed-text dimension
        )
        store = ChromaStore(config)
        yield store
        # Clean up
        try:
            await store.close()
        except (OSError, RuntimeError):
            pass

    @pytest.fixture
    def sample_documents(self):
        """Sample documents for testing."""
        return [
            Document(
                text="Python is a high-level programming language known for its simplicity and readability. It was created by Guido van Rossum and first released in 1991.",
                metadata={"source": "python_wiki", "topic": "introduction"},
            ),
            Document(
                text="Machine learning is a subset of artificial intelligence that enables computers to learn without being explicitly programmed. It uses algorithms and statistical models.",
                metadata={"source": "ml_wiki", "topic": "definition"},
            ),
            Document(
                text="Data science combines statistics, programming, and domain expertise to extract insights from data. It involves data cleaning, analysis, and visualization.",
                metadata={"source": "ds_guide", "topic": "overview"},
            ),
        ]

    @pytest.mark.asyncio
    async def test_rag_pipeline_with_ollama(
        self, ollama_llm_client, chroma_store, sample_documents,
    ):
        """Test complete RAG pipeline using Ollama."""
        # Generate embeddings for documents using Ollama
        from ollama import AsyncClient

        ollama_client = AsyncClient()

        for doc in sample_documents:
            embedding_result = await ollama_client.embeddings(
                model="nomic-embed-text:latest",
                prompt=doc.text,
            )
            doc.embedding = embedding_result["embedding"]

        # Index the sample documents with embeddings
        for doc in sample_documents:
            await chroma_store.add([doc])

        # Generate embedding for the query using the same model
        query = "Python programming"
        embedding_result = await ollama_client.embeddings(
            model="nomic-embed-text:latest",
            prompt=query,
        )
        query_embedding = embedding_result["embedding"]

        # Test retrieval directly
        results = await chroma_store.search(query_vector=query_embedding, k=2)
        assert len(results) > 0
        assert any("Python" in result.document.text for result in results)

        # Test generation with retrieved context
        context_str = "\n\n".join(
            f"[{i+1}] {result.document.text}" for i, result in enumerate(results)
        )
        messages = [
            ChatMessage(
                role="system",
                content="You are a helpful assistant. Answer based on the provided context.",
            ),
            ChatMessage(
                role="user",
                content=f"Context:\n{context_str}\n\nQuestion: What is Python?",
            ),
        ]

        completion = await ollama_llm_client.complete(messages=messages)
        assert completion.content is not None
        assert "python" in completion.content.lower()

    @pytest.mark.asyncio
    async def test_vector_store_with_documents(self, chroma_store, sample_documents):
        """Test vector store operations with Ollama embeddings."""
        # Generate embeddings for documents
        from ollama import AsyncClient

        ollama_client = AsyncClient()

        for doc in sample_documents:
            embedding_result = await ollama_client.embeddings(
                model="nomic-embed-text:latest",
                prompt=doc.text,
            )
            doc.embedding = embedding_result["embedding"]

        # Add documents
        ids = await chroma_store.add(sample_documents)
        assert len(ids) == len(sample_documents)

        # Search for documents
        query_embedding = [0.1] * 768  # Mock embedding with correct dimension
        results = await chroma_store.search(query_vector=query_embedding, k=2)
        for result in results:
            assert isinstance(result, SearchResult)
            assert result.document is not None
            assert result.score >= 0
            assert result.rank >= 0

    @pytest.mark.asyncio
    async def test_ollama_structured_output(self, ollama_llm_client):
        """Test structured output generation with Ollama."""
        messages = [
            ChatMessage(
                role=Role.USER,
                content='Extract information from this text: "John Doe works at Acme Corp as a Senior Engineer. He has 5 years of experience." Return as JSON with keys: name, company, role, experience_years.',
            ),
        ]

        completion = await ollama_llm_client.complete(
            messages=messages,
            temperature=0.1,
            max_tokens=150,
        )

        content = completion.content
        assert content is not None

        # Should contain JSON-like structure
        from lexigram import serialization as json

        try:
            # Try to parse as JSON
            parsed = json.loads(content)
            assert "name" in parsed
            assert "company" in parsed
            assert parsed["name"] == "John Doe"
            assert parsed["company"] == "Acme Corp"
        except json.JSONDecodeError:
            # If not valid JSON, check for key information
            assert "John Doe" in content
            assert "Acme Corp" in content
            assert "Senior Engineer" in content
            assert "5" in content

    @pytest.mark.asyncio
    async def test_ollama_conversation_flow(self, ollama_llm_client):
        """Test multi-turn conversation with Ollama."""
        conversation = []

        # First question
        conversation.append(
            ChatMessage(role=Role.USER, content="What are the main benefits of Python?"),
        )
        completion1 = await ollama_llm_client.complete(messages=conversation)
        conversation.append(
            ChatMessage(role=Role.ASSISTANT, content=completion1.content),
        )

        # Follow-up
        conversation.append(
            ChatMessage(role=Role.USER, content="How does that compare to JavaScript?"),
        )
        completion2 = await ollama_llm_client.complete(messages=conversation)

        # Both responses should be relevant
        assert completion1.content is not None
        assert completion2.content is not None
        assert len(completion1.content.strip()) > 10
        assert len(completion2.content.strip()) > 10

        # Second response should reference the comparison
        response2_lower = completion2.content.lower()
        assert any(
            word in response2_lower
            for word in ["python", "javascript", "compare", "vs", "versus"]
        )
