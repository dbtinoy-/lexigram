"""Tests for multi-hop reasoning."""

from __future__ import annotations

from enum import Enum

import pytest
pytest.importorskip("lexigram.ai.rag", reason="lexigram-ai-rag not installed")

from lexigram.ai.rag.reasoning import IterativeRefinementReasoner
from lexigram.ai.rag.reasoning.base import (
    ReasoningResult,
    ReasoningStep,
    ReasoningStrategy,
)
from lexigram.ai.rag.reasoning.chain_of_thought import ChainOfThoughtReasoner
from lexigram.ai.rag.reasoning.decomposition import QueryDecomposer
from lexigram.ai.rag.reasoning.multi_hop import MultiHopReasoner, multi_hop_reason


# Mock LLM Client
class MockLLMClient:
    """Mock LLM client for testing."""

    def __init__(self, responses=None):
        self.responses = responses or []
        self.call_count = 0

    async def complete(self, messages, temperature=0.7, max_tokens=None):
        """Return mock response."""
        if self.call_count < len(self.responses):
            response = self.responses[self.call_count]
            self.call_count += 1
            return MockResponse(response)
        return MockResponse("Default response")


class MockResponse:
    """Mock response object."""

    def __init__(self, content):
        self.content = content

    def is_err(self):
        return False

    def unwrap(self):
        return self

    def unwrap_err(self):
        raise AssertionError("MockResponse has no error")


# Mock Vector Store
class MockVectorStore:
    """Mock vector store for testing."""

    def __init__(self, documents=None):
        self.documents = documents or []

    async def search(self, query, limit=5, filters=None):
        """Return mock search results."""
        # Return different docs based on query
        if "founder" in query.lower() or "tesla" in query.lower():
            return [
                MockDocument("Elon Musk is the founder of Tesla, Inc."),
                MockDocument("Tesla was founded in 2003."),
            ]
        elif "elon" in query.lower() or "born" in query.lower():
            return [
                MockDocument("Elon Musk was born on June 28, 1971."),
                MockDocument("Elon Musk is a South African entrepreneur."),
            ]
        elif "capital" in query.lower() and "france" in query.lower():
            return [MockDocument("Paris is the capital of France.")]
        elif "capital" in query.lower() and "germany" in query.lower():
            return [MockDocument("Berlin is the capital of Germany.")]
        elif "population" in query.lower() and "paris" in query.lower():
            return [
                MockDocument("Paris has a population of approximately 2.1 million."),
            ]
        elif "population" in query.lower() and "berlin" in query.lower():
            return [
                MockDocument("Berlin has a population of approximately 3.6 million."),
            ]
        elif "quantum" in query.lower():
            return [
                MockDocument("Quantum computing uses quantum mechanics principles."),
                MockDocument("Quantum computers use qubits instead of bits."),
                MockDocument(
                    "Quantum computing can solve certain problems exponentially faster.",
                ),
            ]
        return self.documents[:limit]


class MockDocument:
    """Mock document object."""

    def __init__(self, content):
        self.content = content


# Tests for ReasoningStep
class TestReasoningStep:
    """Tests for ReasoningStep."""

    def test_creation(self):
        """Test creating a reasoning step."""
        step = ReasoningStep(
            step_number=1,
            question="What is the capital of France?",
            reasoning="Looking for capital city information",
            answer="Paris",
            confidence=0.9,
        )

        assert step.step_number == 1
        assert step.question == "What is the capital of France?"
        assert step.reasoning == "Looking for capital city information"
        assert step.answer == "Paris"
        assert step.confidence == 0.9
        assert step.context == []
        assert step.metadata == {}

    def test_with_context(self):
        """Test step with context."""
        docs = [MockDocument("Paris is the capital")]

        step = ReasoningStep(
            step_number=1,
            question="Capital?",
            context=docs,
        )

        assert len(step.context) == 1
        assert step.context[0].content == "Paris is the capital"

    def test_repr(self):
        """Test string representation."""
        step = ReasoningStep(
            step_number=1,
            question="What is AI?",
            confidence=0.75,
        )

        repr_str = repr(step)
        assert "step=1" in repr_str
        assert "confidence=0.75" in repr_str


# Tests for ReasoningResult
class TestReasoningResult:
    """Tests for ReasoningResult."""

    def test_creation(self):
        """Test creating reasoning result."""
        steps = [
            ReasoningStep(1, "First question", answer="First answer"),
            ReasoningStep(2, "Second question", answer="Second answer"),
        ]

        result = ReasoningResult(
            query="Original query",
            final_answer="Final answer",
            steps=steps,
            strategy=ReasoningStrategy.MULTI_HOP,
            total_hops=2,
            overall_confidence=0.8,
        )

        assert result.query == "Original query"
        assert result.final_answer == "Final answer"
        assert len(result.steps) == 2
        assert result.strategy == ReasoningStrategy.MULTI_HOP
        assert result.total_hops == 2
        assert result.overall_confidence == 0.8

    def test_get_reasoning_chain(self):
        """Test getting formatted reasoning chain."""
        steps = [
            ReasoningStep(
                1,
                "What is AI?",
                reasoning="Looking for AI definition",
                answer="Artificial Intelligence",
                confidence=0.9,
            ),
        ]

        result = ReasoningResult(
            query="Explain AI",
            final_answer="AI is artificial intelligence",
            steps=steps,
        )

        chain = result.get_reasoning_chain()
        assert "Query: Explain AI" in chain
        assert "Step 1:" in chain
        assert "What is AI?" in chain
        assert "Artificial Intelligence" in chain
        assert "Final Answer: AI is artificial intelligence" in chain

    def test_repr(self):
        """Test string representation."""
        result = ReasoningResult(
            query="Test",
            final_answer="Answer",
            total_hops=3,
            overall_confidence=0.85,
        )

        repr_str = repr(result)
        assert "hops=3" in repr_str
        assert "confidence=0.85" in repr_str


# Tests for MultiHopReasoner
class TestMultiHopReasoner:
    """Tests for MultiHopReasoner."""

    @pytest.mark.asyncio
    async def test_creation(self):
        """Test creating multi-hop reasoner."""
        llm = MockLLMClient()
        vector_store = MockVectorStore()

        reasoner = MultiHopReasoner(
            llm_client=llm,
            vector_store=vector_store,
            max_hops=3,
            top_k_per_hop=2,
        )

        assert reasoner.max_hops == 3
        assert reasoner.top_k_per_hop == 2
        assert reasoner.confidence_threshold == 0.5

    @pytest.mark.asyncio
    async def test_single_hop(self):
        """Test single hop reasoning."""
        llm = MockLLMClient(
            responses=[
                "REASONING: Direct answer available\nANSWER: Elon Musk\nCONFIDENCE: 0.9\nIS_FINAL: yes",
            ],
        )
        vector_store = MockVectorStore()

        reasoner = MultiHopReasoner(llm, vector_store, max_hops=1)
        result = await reasoner.reason("Who founded Tesla?")

        assert result.total_hops == 1
        assert len(result.steps) == 1
        assert result.steps[0].answer == "Elon Musk"

    @pytest.mark.asyncio
    async def test_multi_hop(self):
        """Test multi-hop reasoning."""
        llm = MockLLMClient(
            responses=[
                "REASONING: Need to find founder first\nANSWER: Elon Musk\nCONFIDENCE: 0.9\nIS_FINAL: no\nNEXT_QUESTION: When was Elon Musk born?",
                "REASONING: Found birth year\nANSWER: 1971\nCONFIDENCE: 0.95\nIS_FINAL: yes",
                "1971",  # Final synthesis
            ],
        )
        vector_store = MockVectorStore()

        reasoner = MultiHopReasoner(llm, vector_store, max_hops=3)
        result = await reasoner.reason("What year was Tesla's founder born?")

        assert result.total_hops == 2
        assert len(result.steps) == 2
        assert result.steps[0].answer == "Elon Musk"
        assert result.steps[1].answer == "1971"

    @pytest.mark.asyncio
    async def test_confidence_threshold(self):
        """Test stopping at confidence threshold."""
        llm = MockLLMClient(
            responses=[
                "REASONING: Low confidence\nANSWER: Maybe X\nCONFIDENCE: 0.3\nIS_FINAL: no\nNEXT_QUESTION: Next?",
                "Final answer",
            ],
        )
        vector_store = MockVectorStore()

        reasoner = MultiHopReasoner(
            llm,
            vector_store,
            max_hops=3,
            confidence_threshold=0.5,
        )
        result = await reasoner.reason("Test query")

        assert result.total_hops == 1  # Stopped at low confidence
        assert result.steps[0].confidence == 0.3

    @pytest.mark.asyncio
    async def test_max_hops_limit(self):
        """Test max hops limit."""
        llm = MockLLMClient(
            responses=[
                "REASONING: Step 1\nANSWER: A1\nCONFIDENCE: 0.8\nIS_FINAL: no\nNEXT_QUESTION: Q2",
                "REASONING: Step 2\nANSWER: A2\nCONFIDENCE: 0.8\nIS_FINAL: no\nNEXT_QUESTION: Q3",
                "REASONING: Step 3\nANSWER: A3\nCONFIDENCE: 0.8\nIS_FINAL: no\nNEXT_QUESTION: Q4",
                "Final answer",
            ],
        )
        vector_store = MockVectorStore()

        reasoner = MultiHopReasoner(llm, vector_store, max_hops=2)
        result = await reasoner.reason("Test query")

        assert result.total_hops == 2  # Limited to max_hops


# Tests for ChainOfThoughtReasoner
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
