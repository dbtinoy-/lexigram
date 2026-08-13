"""Unit tests for IterativeRefinementReasoner."""

from __future__ import annotations

from enum import Enum

import pytest
pytest.importorskip("lexigram.ai.rag", reason="lexigram-ai-rag not installed")

from lexigram.ai.rag.reasoning.base import ReasoningStrategy
from lexigram.ai.rag.reasoning.iterative import IterativeRefinementReasoner


class MockLLMClient:
    def __init__(self, responses=None):
        self.responses = responses or []
        self.call_count = 0
        self.last_messages = None

    async def complete(self, messages, temperature=0.5, max_tokens=None):
        self.last_messages = messages
        if self.call_count < len(self.responses):
            resp = self.responses[self.call_count]
            self.call_count += 1
            return MockResponse(resp)
        return MockResponse("Default")


class MockResponse:
    def __init__(self, content):
        self.content = content

    def is_err(self):
        return False

    def unwrap(self):
        return self

    def unwrap_err(self):
        raise AssertionError("MockResponse has no error")


class MockVectorStore:
    def __init__(self, documents=None):
        self.docs = documents or []
        self.search_calls = []

    async def search(self, query, limit=5, filters=None):
        self.search_calls.append((query, limit))
        # return some simple docs when relevant keywords appear
        if "quantum" in query.lower():
            return [
                MockDoc("Quantum computing uses qubits."),
                MockDoc("Qubits are quantum bits."),
            ]
        return self.docs[:limit]


class MockDoc:
    def __init__(self, content):
        self.content = content


@pytest.mark.asyncio
async def test_single_iteration_initial_answer():
    llm = MockLLMClient(responses=["Initial answer"])
    vs = MockVectorStore(documents=[MockDoc("ctx1")])

    reasoner = IterativeRefinementReasoner(llm, vs, max_iterations=1)
    res = await reasoner.reason("Test query")

    assert res.strategy == ReasoningStrategy.ITERATIVE_REFINEMENT
    assert res.total_hops == 1
    assert len(res.steps) == 1
    assert res.steps[0].answer == "Initial answer"
    assert pytest.approx(res.steps[0].confidence, 0.01) == 0.65
    assert res.metadata["max_iterations"] == 1
    assert "timestamp" in res.metadata


@pytest.mark.asyncio
async def test_multiple_iterations_confidence_increase():
    llm = MockLLMClient(responses=["Initial", "Improved", "Final"])
    vs = MockVectorStore()

    reasoner = IterativeRefinementReasoner(llm, vs, max_iterations=3)
    res = await reasoner.reason("Explain quantum computing")

    assert res.total_hops == 3
    assert len(res.steps) == 3
    assert res.steps[-1].confidence > res.steps[0].confidence
    assert res.final_answer == "Final"


@pytest.mark.asyncio
async def test_refinement_parses_refined_answer_block():
    llm = MockLLMClient(
        responses=["Initial answer", "Some critique\nRefined Answer: Better answer"],
    )
    vs = MockVectorStore()

    reasoner = IterativeRefinementReasoner(llm, vs, max_iterations=2)
    res = await reasoner.reason("Test")

    assert res.total_hops == 2
    assert "Better answer" in res.final_answer


@pytest.mark.asyncio
async def test_initial_context_included_in_prompt():
    # verify that initial_context content is passed in the prompt messages
    llm = MockLLMClient(responses=["Initial answer"])
    vs = MockVectorStore()

    initial_context = [MockDoc("Alpha context"), "Extra context string"]

    reasoner = IterativeRefinementReasoner(llm, vs, max_iterations=1)
    res = await reasoner.reason("Test query", initial_context=initial_context)

    # The mock LLM client recorded the last messages argument
    assert llm.last_messages is not None
    joined_parts = []
    for m in llm.last_messages:
        role = m.role if hasattr(m, "role") else m.get("role", "")
        if role == "user":
            content = m.content if hasattr(m, "content") else m.get("content", "")
            joined_parts.append(content)
    joined = "\n\n".join(joined_parts)
    assert "Alpha context" in joined
    assert "Extra context string" in joined
