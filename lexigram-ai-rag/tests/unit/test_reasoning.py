"""Unit tests for reasoning modules."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.ai.rag.reasoning.base import ReasoningStrategy
from lexigram.ai.rag.reasoning.chain_of_thought import ChainOfThoughtReasoner
from lexigram.ai.rag.reasoning.decomposition import QueryDecomposer
from lexigram.ai.rag.reasoning.iterative import IterativeRefinementReasoner


class TestChainOfThoughtReasoner:
    """Tests for ChainOfThoughtReasoner class."""

    @pytest.fixture
    def mock_llm_client(self) -> MagicMock:
        """Create mock LLM client."""
        llm = MagicMock()
        result = MagicMock()
        result.is_err = MagicMock(return_value=False)
        result.unwrap = MagicMock(
            return_value="Step 1: First, let's understand the problem. "
            "Step 2: Then we analyze the components. "
            "Therefore, the answer is derived from these steps."
        )
        llm.complete = AsyncMock(return_value=result)
        return llm

    @pytest.mark.asyncio
    async def test_reasoning_steps_generated(
        self,
        mock_llm_client: MagicMock,
    ) -> None:
        """Test that reasoning steps are generated."""
        reasoner = ChainOfThoughtReasoner(
            llm_client=mock_llm_client,
            max_thoughts=5,
        )

        result = await reasoner.reason("What is machine learning?")

        assert result.query == "What is machine learning?"
        assert result.strategy == ReasoningStrategy.CHAIN_OF_THOUGHT
        assert len(result.steps) >= 1

    @pytest.mark.asyncio
    async def test_reasoning_with_context(
        self,
        mock_llm_client: MagicMock,
    ) -> None:
        """Test reason_with_context method."""
        reasoner = ChainOfThoughtReasoner(llm_client=mock_llm_client)

        result = await reasoner.reason_with_context(
            query="Explain AI",
            context="AI stands for Artificial Intelligence...",
        )

        assert result.query == "Explain AI"
        assert result.strategy == ReasoningStrategy.CHAIN_OF_THOUGHT
        assert result.metadata.get("has_context") is True

    @pytest.mark.asyncio
    async def test_reasoning_without_context(
        self,
        mock_llm_client: MagicMock,
    ) -> None:
        """Test reason without context."""
        reasoner = ChainOfThoughtReasoner(llm_client=mock_llm_client)

        result = await reasoner.reason("What is Python?")

        assert result.metadata.get("has_context") is False

    @pytest.mark.asyncio
    async def test_final_answer_extracted(
        self,
        mock_llm_client: MagicMock,
    ) -> None:
        """Test that final answer is extracted from chain."""
        reasoner = ChainOfThoughtReasoner(llm_client=mock_llm_client)

        result = await reasoner.reason("test query")

        assert result.final_answer is not None
        assert len(result.final_answer) > 0

    @pytest.mark.asyncio
    async def test_confidence_default(
        self,
        mock_llm_client: MagicMock,
    ) -> None:
        """Test default confidence is set."""
        reasoner = ChainOfThoughtReasoner(llm_client=mock_llm_client)

        result = await reasoner.reason("query")

        assert result.overall_confidence == 0.8

    @pytest.mark.asyncio
    async def test_max_thoughts_in_metadata(
        self,
        mock_llm_client: MagicMock,
    ) -> None:
        """Test max_thoughts is recorded in metadata."""
        reasoner = ChainOfThoughtReasoner(
            llm_client=mock_llm_client,
            max_thoughts=10,
        )

        result = await reasoner.reason("query")

        assert result.metadata.get("max_thoughts") == 10


class TestDecompositionReasoner:
    """Tests for QueryDecomposer class."""

    @pytest.fixture
    def mock_llm_client(self) -> MagicMock:
        """Create mock LLM client."""
        llm = MagicMock()

        async def mock_complete(*args, **kwargs):
            result = MagicMock()
            result.is_err = MagicMock(return_value=False)

            messages = kwargs.get("messages", [])
            if messages:
                last_msg = messages[-1]
                if hasattr(last_msg, "content"):
                    user_msg = last_msg.content
                else:
                    user_msg = last_msg.get("content", "")
            else:
                user_msg = ""

            if "sub-question" in user_msg.lower() or "break down" in user_msg.lower():
                result.unwrap = MagicMock(
                    return_value="1. What is Python?\n2. What are its features?"
                )
            elif "concise answer" in user_msg.lower():
                result.unwrap = MagicMock(
                    return_value="Python is a programming language."
                )
            else:
                result.unwrap = MagicMock(return_value="Synthesized answer.")

            return result

        llm.complete = AsyncMock(side_effect=mock_complete)
        return llm

    @pytest.fixture
    def mock_vector_store(self) -> MagicMock:
        """Create mock vector store."""
        store = MagicMock()
        doc = MagicMock()
        doc.content = "Mock document content"
        store.search = AsyncMock(return_value=[doc])
        return store

    @pytest.mark.asyncio
    async def test_decompose_query(
        self,
        mock_llm_client: MagicMock,
        mock_vector_store: MagicMock,
    ) -> None:
        """Test query decomposition."""
        decomposer = QueryDecomposer(
            llm_client=mock_llm_client,
            vector_store=mock_vector_store,
            max_sub_queries=5,
        )

        result = await decomposer.reason("What is Python and its features?")

        assert result.query == "What is Python and its features?"
        assert result.strategy == ReasoningStrategy.DECOMPOSITION
        assert len(result.steps) >= 1

    @pytest.mark.asyncio
    async def test_total_hops_equals_steps(
        self,
        mock_llm_client: MagicMock,
        mock_vector_store: MagicMock,
    ) -> None:
        """Test that total_hops equals number of steps."""
        decomposer = QueryDecomposer(
            llm_client=mock_llm_client,
            vector_store=mock_vector_store,
            max_sub_queries=3,
        )

        result = await decomposer.reason("complex query")

        assert result.total_hops == len(result.steps)

    @pytest.mark.asyncio
    async def test_steps_contain_sub_queries(
        self,
        mock_llm_client: MagicMock,
        mock_vector_store: MagicMock,
    ) -> None:
        """Test that steps contain sub-queries."""
        decomposer = QueryDecomposer(
            llm_client=mock_llm_client,
            vector_store=mock_vector_store,
        )

        result = await decomposer.reason("test query")

        for step in result.steps:
            assert step.step_number is not None
            assert step.question is not None

    @pytest.mark.asyncio
    async def test_overall_confidence(
        self,
        mock_llm_client: MagicMock,
        mock_vector_store: MagicMock,
    ) -> None:
        """Test overall confidence is set."""
        decomposer = QueryDecomposer(
            llm_client=mock_llm_client,
            vector_store=mock_vector_store,
        )

        result = await decomposer.reason("query")

        assert result.overall_confidence is not None

    @pytest.mark.asyncio
    async def test_max_sub_queries_limit(
        self,
        mock_llm_client: MagicMock,
        mock_vector_store: MagicMock,
    ) -> None:
        """Test max_sub_queries is recorded in metadata."""
        decomposer = QueryDecomposer(
            llm_client=mock_llm_client,
            vector_store=mock_vector_store,
            max_sub_queries=3,
        )

        result = await decomposer.reason("query")

        assert result.metadata.get("max_sub_queries") == 3


class TestIterativeReasoner:
    """Tests for IterativeRefinementReasoner class."""

    @pytest.fixture
    def mock_llm_client(self) -> MagicMock:
        """Create mock LLM client."""
        llm = MagicMock()

        async def mock_complete(*args, **kwargs):
            result = MagicMock()
            result.is_err = MagicMock(return_value=False)

            messages = kwargs.get("messages", [])
            if messages:
                last_msg = messages[-1]
                if hasattr(last_msg, "content"):
                    content = last_msg.content
                else:
                    content = last_msg.get("content", "")
                if "refine" in content.lower() or "refined" in content.lower():
                    result.unwrap = MagicMock(
                        return_value="Critique: Better organization needed.\n\n"
                        "Refined Answer: Improved answer with better clarity."
                    )
                else:
                    result.unwrap = MagicMock(
                        return_value="Initial answer to the question."
                    )
            else:
                result.unwrap = MagicMock(return_value="Answer")

            return result

        llm.complete = AsyncMock(side_effect=mock_complete)
        return llm

    @pytest.fixture
    def mock_vector_store(self) -> MagicMock:
        """Create mock vector store."""
        store = MagicMock()
        doc = MagicMock()
        doc.content = "Context document"
        store.search = AsyncMock(return_value=[doc])
        return store

    @pytest.mark.asyncio
    async def test_iterative_refinement(
        self,
        mock_llm_client: MagicMock,
        mock_vector_store: MagicMock,
    ) -> None:
        """Test iterative refinement reasoning."""
        reasoner = IterativeRefinementReasoner(
            llm_client=mock_llm_client,
            vector_store=mock_vector_store,
            max_iterations=3,
        )

        result = await reasoner.reason("What is Python?")

        assert result.query == "What is Python?"
        assert result.strategy == ReasoningStrategy.ITERATIVE_REFINEMENT

    @pytest.mark.asyncio
    async def test_steps_equal_iterations(
        self,
        mock_llm_client: MagicMock,
        mock_vector_store: MagicMock,
    ) -> None:
        """Test that steps equal iteration count."""
        reasoner = IterativeRefinementReasoner(
            llm_client=mock_llm_client,
            vector_store=mock_vector_store,
            max_iterations=3,
        )

        result = await reasoner.reason("query")

        assert len(result.steps) == 3
        assert result.total_hops == 3

    @pytest.mark.asyncio
    async def test_confidence_increases_with_iterations(
        self,
        mock_llm_client: MagicMock,
        mock_vector_store: MagicMock,
    ) -> None:
        """Test that confidence increases with iterations."""
        reasoner = IterativeRefinementReasoner(
            llm_client=mock_llm_client,
            vector_store=mock_vector_store,
            max_iterations=3,
        )

        result = await reasoner.reason("query")

        confidences = [step.confidence for step in result.steps]
        for i in range(1, len(confidences)):
            assert confidences[i] >= confidences[i - 1]

    @pytest.mark.asyncio
    async def test_final_answer_from_last_iteration(
        self,
        mock_llm_client: MagicMock,
        mock_vector_store: MagicMock,
    ) -> None:
        """Test that final answer comes from last iteration."""
        reasoner = IterativeRefinementReasoner(
            llm_client=mock_llm_client,
            vector_store=mock_vector_store,
            max_iterations=2,
        )

        result = await reasoner.reason("query")

        assert result.final_answer is not None

    @pytest.mark.asyncio
    async def test_overall_confidence_from_last_step(
        self,
        mock_llm_client: MagicMock,
        mock_vector_store: MagicMock,
    ) -> None:
        """Test overall confidence from last step."""
        reasoner = IterativeRefinementReasoner(
            llm_client=mock_llm_client,
            vector_store=mock_vector_store,
            max_iterations=2,
        )

        result = await reasoner.reason("query")

        assert result.overall_confidence == result.steps[-1].confidence

    @pytest.mark.asyncio
    async def test_max_iterations_in_metadata(
        self,
        mock_llm_client: MagicMock,
        mock_vector_store: MagicMock,
    ) -> None:
        """Test max_iterations is recorded in metadata."""
        reasoner = IterativeRefinementReasoner(
            llm_client=mock_llm_client,
            vector_store=mock_vector_store,
            max_iterations=4,
        )

        result = await reasoner.reason("query")

        assert result.metadata.get("max_iterations") == 4


class TestReasoningExports:
    """Tests for reasoning module exports."""

    def test_all_exports(self) -> None:
        """Test that all expected exports are available."""
        from lexigram.ai.rag import reasoning

        expected = [
            "ChainOfThoughtReasoner",
            "QueryDecomposer",
            "IterativeRefinementReasoner",
        ]
        for name in expected:
            assert hasattr(reasoning, name)
