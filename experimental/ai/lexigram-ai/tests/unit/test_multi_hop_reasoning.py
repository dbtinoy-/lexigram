"""Tests for multi-hop reasoning core step/result types and MultiHopReasoner."""

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

from lexigram.ai.rag.reasoning.base import (
    ReasoningResult,
    ReasoningStep,
    ReasoningStrategy,
)
from lexigram.ai.rag.reasoning.multi_hop import MultiHopReasoner


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
