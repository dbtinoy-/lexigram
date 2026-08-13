"""Unit tests for HyDE generators."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.ai.rag.hyde.generators.multiple import MultipleHyDEGenerator
from lexigram.ai.rag.hyde.generators.single import SingleHyDEGenerator
from lexigram.ai.rag.hyde.generators.weighted import WeightedHyDEGenerator
from lexigram.ai.rag.hyde.types import HyDEStrategy


class TestHyDESingleGenerator:
    """Tests for SingleHyDEGenerator class."""

    @pytest.fixture
    def mock_llm_client(self) -> MagicMock:
        """Create mock LLM client."""
        llm = MagicMock()
        result = MagicMock()
        result.is_err = MagicMock(return_value=False)
        result.unwrap = MagicMock(
            return_value="Generated hypothetical document content"
        )
        llm.complete = AsyncMock(return_value=result)
        return llm

    @pytest.fixture
    def mock_embedding_client(self) -> MagicMock:
        """Create mock embedding client."""
        embedding = MagicMock()
        embedding.embed = AsyncMock(return_value=[[0.1, 0.2, 0.3]])
        return embedding

    @pytest.mark.asyncio
    async def test_generate_single_document(
        self,
        mock_llm_client: MagicMock,
    ) -> None:
        """Test generate creates single hypothetical document."""
        generator = SingleHyDEGenerator(
            llm_client=mock_llm_client,
            temperature=0.7,
            max_tokens=200,
        )

        result = await generator.generate("What is Python?")

        assert result.query == "What is Python?"
        assert result.strategy == HyDEStrategy.SINGLE
        assert len(result.hypothetical_docs) == 1
        assert result.hypothetical_docs[0].query == "What is Python?"
        assert result.hypothetical_docs[0].confidence == 1.0

    @pytest.mark.asyncio
    async def test_generate_with_embedding_client(
        self,
        mock_llm_client: MagicMock,
        mock_embedding_client: MagicMock,
    ) -> None:
        """Test generate with embedding client produces embedding."""
        generator = SingleHyDEGenerator(
            llm_client=mock_llm_client,
            embedding_client=mock_embedding_client,
            temperature=0.5,
            max_tokens=150,
        )

        result = await generator.generate("test query")

        assert result.aggregated_embedding is not None
        assert result.aggregated_embedding == [0.1, 0.2, 0.3]

    @pytest.mark.asyncio
    async def test_generate_without_embedding_client(
        self,
        mock_llm_client: MagicMock,
    ) -> None:
        """Test generate without embedding client returns None embedding."""
        generator = SingleHyDEGenerator(
            llm_client=mock_llm_client,
            embedding_client=None,
        )

        result = await generator.generate("test query")

        assert result.aggregated_embedding is None

    @pytest.mark.asyncio
    async def test_generate_respects_temperature_and_max_tokens(
        self,
        mock_llm_client: MagicMock,
    ) -> None:
        """Test that temperature and max_tokens are set correctly."""
        generator = SingleHyDEGenerator(
            llm_client=mock_llm_client,
            temperature=0.9,
            max_tokens=300,
        )

        result = await generator.generate("query")

        assert result.metadata["temperature"] == 0.9
        assert result.metadata["max_tokens"] == 300

    @pytest.mark.asyncio
    async def test_num_documents_parameter_ignored(
        self, mock_llm_client: MagicMock
    ) -> None:
        """Test that num_documents parameter is ignored for single generator."""
        generator = SingleHyDEGenerator(llm_client=mock_llm_client)

        result = await generator.generate("query", num_documents=5)

        assert len(result.hypothetical_docs) == 1


class TestHydeMultipleGenerator:
    """Tests for MultipleHyDEGenerator class."""

    @pytest.fixture
    def mock_llm_client(self) -> MagicMock:
        """Create mock LLM client."""
        llm = MagicMock()
        result = MagicMock()
        result.is_err = MagicMock(return_value=False)
        result.unwrap = MagicMock(return_value="Hypothetical content")
        llm.complete = AsyncMock(return_value=result)
        return llm

    @pytest.fixture
    def mock_embedding_client(self) -> MagicMock:
        """Create mock embedding client."""
        embedding = MagicMock()
        embedding.embed = AsyncMock(return_value=[[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]])
        return embedding

    @pytest.mark.asyncio
    async def test_generate_multiple_documents(
        self,
        mock_llm_client: MagicMock,
    ) -> None:
        """Test generate creates multiple hypothetical documents."""
        generator = MultipleHyDEGenerator(
            llm_client=mock_llm_client,
            default_num_documents=3,
        )

        result = await generator.generate("What is Python?")

        assert result.query == "What is Python?"
        assert result.strategy == HyDEStrategy.MULTIPLE
        assert len(result.hypothetical_docs) == 3

    @pytest.mark.asyncio
    async def test_generate_with_custom_num_documents(
        self,
        mock_llm_client: MagicMock,
    ) -> None:
        """Test generate with custom num_documents parameter."""
        generator = MultipleHyDEGenerator(
            llm_client=mock_llm_client,
            default_num_documents=2,
        )

        result = await generator.generate("query", num_documents=5)

        assert len(result.hypothetical_docs) == 5

    @pytest.mark.asyncio
    async def test_generate_uses_default_when_none(
        self,
        mock_llm_client: MagicMock,
    ) -> None:
        """Test that default_num_documents is used when param is None."""
        generator = MultipleHyDEGenerator(
            llm_client=mock_llm_client,
            default_num_documents=4,
        )

        result = await generator.generate("query")

        assert len(result.hypothetical_docs) == 4

    @pytest.mark.asyncio
    async def test_confidence_decreases_with_index(
        self,
        mock_llm_client: MagicMock,
    ) -> None:
        """Test that confidence decreases for later documents."""
        generator = MultipleHyDEGenerator(
            llm_client=mock_llm_client,
            default_num_documents=3,
        )

        result = await generator.generate("query")

        confidences = [doc.confidence for doc in result.hypothetical_docs]
        assert confidences[0] > confidences[1] > confidences[2]

    @pytest.mark.asyncio
    async def test_generate_with_embedding_aggregation(
        self,
        mock_llm_client: MagicMock,
        mock_embedding_client: MagicMock,
    ) -> None:
        """Test embedding aggregation with multiple documents."""
        generator = MultipleHyDEGenerator(
            llm_client=mock_llm_client,
            embedding_client=mock_embedding_client,
            default_num_documents=3,
        )

        result = await generator.generate("query")

        assert result.aggregated_embedding is not None


class TestHydeWeightedGenerator:
    """Tests for WeightedHyDEGenerator class."""

    @pytest.fixture
    def mock_llm_client(self) -> MagicMock:
        """Create mock LLM client."""
        llm = MagicMock()
        result = MagicMock()
        result.is_err = MagicMock(return_value=False)
        result.unwrap = MagicMock(return_value="Weighted content")
        llm.complete = AsyncMock(return_value=result)
        return llm

    @pytest.fixture
    def mock_embedding_client(self) -> MagicMock:
        """Create mock embedding client."""
        embedding = MagicMock()
        embedding.embed = AsyncMock(return_value=[[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]])
        return embedding

    @pytest.mark.asyncio
    async def test_generate_weighted_documents(
        self,
        mock_llm_client: MagicMock,
        mock_embedding_client: MagicMock,
    ) -> None:
        """Test generate creates weighted documents."""
        generator = WeightedHyDEGenerator(
            llm_client=mock_llm_client,
            embedding_client=mock_embedding_client,
            default_num_documents=3,
            confidence_decay=0.7,
        )

        result = await generator.generate("What is Python?")

        assert result.query == "What is Python?"
        assert result.strategy == HyDEStrategy.WEIGHTED
        assert len(result.hypothetical_docs) == 3

    @pytest.mark.asyncio
    async def test_exponential_confidence_decay(
        self,
        mock_llm_client: MagicMock,
        mock_embedding_client: MagicMock,
    ) -> None:
        """Test exponential confidence decay formula."""
        generator = WeightedHyDEGenerator(
            llm_client=mock_llm_client,
            embedding_client=mock_embedding_client,
            default_num_documents=3,
            confidence_decay=0.5,
        )

        result = await generator.generate("query")

        confidences = [doc.confidence for doc in result.hypothetical_docs]
        assert confidences[0] == 1.0
        assert confidences[1] == 0.5
        assert confidences[2] == 0.25

    @pytest.mark.asyncio
    async def test_weighted_aggregation(
        self,
        mock_llm_client: MagicMock,
        mock_embedding_client: MagicMock,
    ) -> None:
        """Test weighted embedding aggregation."""
        generator = WeightedHyDEGenerator(
            llm_client=mock_llm_client,
            embedding_client=mock_embedding_client,
            default_num_documents=3,
        )

        result = await generator.generate("query")

        assert result.aggregated_embedding is not None

    @pytest.mark.asyncio
    async def test_metadata_includes_weights(
        self,
        mock_llm_client: MagicMock,
        mock_embedding_client: MagicMock,
    ) -> None:
        """Test that weights are included in metadata."""
        generator = WeightedHyDEGenerator(
            llm_client=mock_llm_client,
            embedding_client=mock_embedding_client,
            default_num_documents=3,
            confidence_decay=0.7,
        )

        result = await generator.generate("query")

        assert "weights" in result.metadata
        assert len(result.metadata["weights"]) == 3

    @pytest.mark.asyncio
    async def test_requires_embedding_client(
        self,
        mock_llm_client: MagicMock,
    ) -> None:
        """Test that weighted generator requires embedding client."""
        generator = WeightedHyDEGenerator(
            llm_client=mock_llm_client,
            embedding_client=None,
        )

        with pytest.raises(ValueError, match="Embedding client required"):
            await generator.generate("query")


class TestHyDEGeneratorsExports:
    """Tests for HyDE generators module exports."""

    def test_all_exports(self) -> None:
        """Test that all expected exports are available."""
        from lexigram.ai.rag.hyde import generators

        expected = [
            "SingleHyDEGenerator",
            "MultipleHyDEGenerator",
            "WeightedHyDEGenerator",
        ]
        for name in expected:
            assert hasattr(generators, name)
