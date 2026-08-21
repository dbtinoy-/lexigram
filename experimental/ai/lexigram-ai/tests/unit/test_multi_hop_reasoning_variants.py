"""Tests for multi-hop reasoning strategy variants and integration."""

from __future__ import annotations

import pytest

pytest.importorskip("lexigram.ai.rag", reason="lexigram-ai-rag not installed")

# Mock LLM Client
from _multi_hop_support import (  # noqa: F401 — shared mocks live beside the suites
    MockDocument,
    MockLLMClient,
    MockResponse,
    MockVectorStore,
)

from lexigram.ai.rag.reasoning import IterativeRefinementReasoner
from lexigram.ai.rag.reasoning.base import (
    ReasoningStrategy,
)
from lexigram.ai.rag.reasoning.chain_of_thought import ChainOfThoughtReasoner
from lexigram.ai.rag.reasoning.decomposition import QueryDecomposer
from lexigram.ai.rag.reasoning.multi_hop import MultiHopReasoner, multi_hop_reason


class TestChainOfThoughtReasoner:
    """Tests for ChainOfThoughtReasoner."""

    @pytest.mark.asyncio
    async def test_creation(self):
        """Test creating chain-of-thought reasoner."""
        llm = MockLLMClient()
        reasoner = ChainOfThoughtReasoner(llm, max_thoughts=5)

        assert reasoner.max_thoughts == 5
        assert reasoner.temperature == 0.3

    @pytest.mark.asyncio
    async def test_reason_without_context(self):
        """Test reasoning without context."""
        llm = MockLLMClient(
            responses=[
                """Step 1: Alice is older than Bob
Step 2: Bob is older than Charlie
Step 3: Therefore Charlie is younger than Bob
Therefore, Charlie is the youngest.""",
            ],
        )

        reasoner = ChainOfThoughtReasoner(llm)
        result = await reasoner.reason(
            "If Alice > Bob and Bob > Charlie, who is youngest?",
        )

        assert result.strategy == ReasoningStrategy.CHAIN_OF_THOUGHT
        assert len(result.steps) > 0
        assert "Charlie" in result.final_answer

    @pytest.mark.asyncio
    async def test_reason_with_context(self):
        """Test reasoning with context."""
        llm = MockLLMClient(
            responses=[
                """1. Looking at the context, we see information about ages
2. Alice is 30, Bob is 25, Charlie is 20
3. Therefore Charlie is the youngest at 20 years old""",
            ],
        )

        reasoner = ChainOfThoughtReasoner(llm)
        context = "Alice is 30. Bob is 25. Charlie is 20."

        result = await reasoner.reason_with_context("Who is youngest?", context)

        assert result.strategy == ReasoningStrategy.CHAIN_OF_THOUGHT
        assert len(result.steps) >= 3
        assert result.overall_confidence == 0.8

    @pytest.mark.asyncio
    async def test_parse_chain_of_thought(self):
        """Test parsing chain of thought."""
        llm = MockLLMClient()
        reasoner = ChainOfThoughtReasoner(llm)

        text = """Step 1: First observation
Step 2: Second observation
Therefore, the answer is X."""

        steps = reasoner._parse_chain_of_thought(text)

        assert len(steps) >= 2
        assert "First observation" in steps[0].reasoning
        assert "Second observation" in steps[1].reasoning


# Tests for QueryDecomposer
class TestQueryDecomposer:
    """Tests for QueryDecomposer."""

    @pytest.mark.asyncio
    async def test_creation(self):
        """Test creating query decomposer."""
        llm = MockLLMClient()
        vector_store = MockVectorStore()

        decomposer = QueryDecomposer(llm, vector_store, max_sub_queries=5)

        assert decomposer.max_sub_queries == 5
        assert decomposer.top_k_per_query == 2

    @pytest.mark.asyncio
    async def test_decompose_query(self):
        """Test query decomposition."""
        llm = MockLLMClient(
            responses=[
                """1. What is the capital of France?
2. What is the population of Paris?
3. What is the capital of Germany?
4. What is the population of Berlin?""",
            ],
        )
        vector_store = MockVectorStore()

        decomposer = QueryDecomposer(llm, vector_store)
        sub_queries = await decomposer._decompose_query(
            "Compare populations of capitals of France and Germany",
        )

        assert len(sub_queries) == 4
        assert "capital of France" in sub_queries[0]
        assert "capital of Germany" in sub_queries[2]

    @pytest.mark.asyncio
    async def test_reason_decomposed(self):
        """Test reasoning with decomposition."""
        llm = MockLLMClient(
            responses=[
                "1. What is X?\n2. What is Y?",  # Decomposition
                "Answer to X",  # Sub-query 1 answer
                "Answer to Y",  # Sub-query 2 answer
                "Combined answer from X and Y",  # Synthesis
            ],
        )
        vector_store = MockVectorStore()

        decomposer = QueryDecomposer(llm, vector_store, max_sub_queries=2)
        result = await decomposer.reason("Complex query about X and Y")

        assert result.strategy == ReasoningStrategy.DECOMPOSITION
        assert result.total_hops == 2
        assert len(result.steps) == 2


# Tests for IterativeRefinementReasoner
class TestIterativeRefinementReasoner:
    """Tests for IterativeRefinementReasoner."""

    @pytest.mark.asyncio
    async def test_creation(self):
        """Test creating iterative refinement reasoner."""
        llm = MockLLMClient()
        vector_store = MockVectorStore()

        reasoner = IterativeRefinementReasoner(llm, vector_store, max_iterations=3)

        assert reasoner.max_iterations == 3
        assert reasoner.top_k == 5

    @pytest.mark.asyncio
    async def test_single_iteration(self):
        """Test single iteration."""
        llm = MockLLMClient(responses=["Initial answer"])
        vector_store = MockVectorStore()

        reasoner = IterativeRefinementReasoner(llm, vector_store, max_iterations=1)
        result = await reasoner.reason("Test query")

        assert result.strategy == ReasoningStrategy.ITERATIVE_REFINEMENT
        assert result.total_hops == 1
        assert result.steps[0].answer == "Initial answer"

    @pytest.mark.asyncio
    async def test_multiple_iterations(self):
        """Test multiple iterations."""
        llm = MockLLMClient(
            responses=[
                "Initial answer",
                "Improved answer with more details",
                "Final refined answer with examples",
            ],
        )
        vector_store = MockVectorStore()

        reasoner = IterativeRefinementReasoner(llm, vector_store, max_iterations=3)
        result = await reasoner.reason("Explain quantum computing")

        assert result.total_hops == 3
        assert len(result.steps) == 3
        # Confidence should increase with iterations
        assert result.steps[2].confidence > result.steps[0].confidence

    @pytest.mark.asyncio
    async def test_refinement_with_critique(self):
        """Test refinement with critique."""
        llm = MockLLMClient(
            responses=[
                "Initial answer",
                "Some critique here\nRefined Answer: Better answer",
            ],
        )
        vector_store = MockVectorStore()

        reasoner = IterativeRefinementReasoner(llm, vector_store, max_iterations=2)
        result = await reasoner.reason("Test")

        assert result.total_hops == 2
        assert "Better answer" in result.final_answer


# Tests for convenience function
class TestConvenienceFunction:
    """Tests for multi_hop_reason convenience function."""

    @pytest.mark.asyncio
    async def test_multi_hop_strategy(self):
        """Test with multi-hop strategy."""
        llm = MockLLMClient(
            responses=["REASONING: Test\nANSWER: A\nCONFIDENCE: 0.9\nIS_FINAL: yes"],
        )
        vector_store = MockVectorStore()

        result = await multi_hop_reason(
            "Test query",
            llm_client=llm,
            vector_store=vector_store,
            strategy=ReasoningStrategy.MULTI_HOP,
            max_hops=1,
        )

        assert result.strategy == ReasoningStrategy.MULTI_HOP
        assert result.total_hops == 1

    @pytest.mark.asyncio
    async def test_chain_of_thought_strategy(self):
        """Test with chain-of-thought strategy."""
        llm = MockLLMClient(responses=["Step 1: Think\nTherefore: Answer"])
        vector_store = MockVectorStore()

        result = await multi_hop_reason(
            "Test query",
            llm_client=llm,
            vector_store=vector_store,
            strategy=ReasoningStrategy.CHAIN_OF_THOUGHT,
        )

        assert result.strategy == ReasoningStrategy.CHAIN_OF_THOUGHT

    @pytest.mark.asyncio
    async def test_decomposition_strategy(self):
        """Test with decomposition strategy."""
        llm = MockLLMClient(
            responses=[
                "1. Sub Q1\n2. Sub Q2",
                "Answer 1",
                "Answer 2",
                "Final answer",
            ],
        )
        vector_store = MockVectorStore()

        result = await multi_hop_reason(
            "Test query",
            llm_client=llm,
            vector_store=vector_store,
            strategy=ReasoningStrategy.DECOMPOSITION,
        )

        assert result.strategy == ReasoningStrategy.DECOMPOSITION

    @pytest.mark.asyncio
    async def test_iterative_strategy(self):
        """Test with iterative refinement strategy."""
        llm = MockLLMClient(responses=["Answer 1", "Answer 2"])
        vector_store = MockVectorStore()

        result = await multi_hop_reason(
            "Test query",
            llm_client=llm,
            vector_store=vector_store,
            strategy=ReasoningStrategy.ITERATIVE_REFINEMENT,
            max_iterations=2,
        )

        assert result.strategy == ReasoningStrategy.ITERATIVE_REFINEMENT

    @pytest.mark.asyncio
    async def test_invalid_strategy(self):
        """Test with invalid strategy."""
        llm = MockLLMClient()
        vector_store = MockVectorStore()

        with pytest.raises(ValueError, match="Unknown reasoning strategy"):
            await multi_hop_reason(
                "Test",
                llm_client=llm,
                vector_store=vector_store,
                strategy="invalid",
            )


# Integration tests
class TestIntegration:
    """Integration tests for multi-hop reasoning."""

    @pytest.mark.asyncio
    async def test_full_multi_hop_workflow(self):
        """Test full multi-hop workflow."""
        llm = MockLLMClient(
            responses=[
                "REASONING: Looking for founder\nANSWER: Elon Musk\nCONFIDENCE: 0.9\nIS_FINAL: no\nNEXT_QUESTION: When was Elon Musk born?",
                "REASONING: Found birth year\nANSWER: 1971\nCONFIDENCE: 0.95\nIS_FINAL: yes",
                "Elon Musk, the founder of Tesla, was born in 1971.",
            ],
        )
        vector_store = MockVectorStore()

        reasoner = MultiHopReasoner(llm, vector_store, max_hops=3)
        result = await reasoner.reason("When was the founder of Tesla born?")

        # Verify result structure
        assert result.query == "When was the founder of Tesla born?"
        assert result.total_hops == 2
        assert len(result.steps) == 2

        # Verify first hop
        assert "Musk" in result.steps[0].answer
        assert result.steps[0].confidence == 0.9

        # Verify second hop
        assert "1971" in result.steps[1].answer
        assert result.steps[1].confidence == 0.95

        # Verify final answer
        assert "1971" in result.final_answer

        # Verify reasoning chain
        chain = result.get_reasoning_chain()
        assert "Step 1:" in chain
        assert "Step 2:" in chain

    @pytest.mark.asyncio
    async def test_chain_of_thought_workflow(self):
        """Test chain-of-thought workflow."""
        llm = MockLLMClient(
            responses=[
                """Let me think through this step by step:
1. We need to identify who is youngest
2. Alice is older than Bob means Alice > Bob
3. Bob is older than Charlie means Bob > Charlie
4. This creates a chain: Alice > Bob > Charlie
Therefore, Charlie is the youngest person.""",
            ],
        )

        reasoner = ChainOfThoughtReasoner(llm)
        result = await reasoner.reason(
            "If Alice is older than Bob and Bob is older than Charlie, who is youngest?",
        )

        assert result.strategy == ReasoningStrategy.CHAIN_OF_THOUGHT
        assert len(result.steps) >= 4
        assert "charlie" in result.final_answer.lower()

    @pytest.mark.asyncio
    async def test_query_decomposition_workflow(self):
        """Test query decomposition workflow."""
        llm = MockLLMClient(
            responses=[
                "1. What is the capital of France?\n2. What is the population of the capital?",
                "Paris",
                "2.1 million",
                "The capital of France is Paris, with a population of 2.1 million.",
            ],
        )
        vector_store = MockVectorStore()

        decomposer = QueryDecomposer(llm, vector_store, max_sub_queries=2)
        result = await decomposer.reason(
            "What is the population of France's capital?",
        )

        assert result.strategy == ReasoningStrategy.DECOMPOSITION
        assert result.total_hops == 2
        assert "Paris" in result.steps[0].answer or "Paris" in result.final_answer
