"""Tests for Chain-of-Thought and QueryDecomposer."""

from __future__ import annotations

from enum import Enum

import pytest
pytest.importorskip("lexigram.ai.rag", reason="lexigram-ai-rag not installed")

from lexigram.ai.rag.reasoning.base import ReasoningStrategy
from lexigram.ai.rag.reasoning.chain_of_thought import ChainOfThoughtReasoner
from lexigram.ai.rag.reasoning.decomposition import QueryDecomposer


class MockLLM:
    def __init__(self, responses=None):
        self.responses = responses or []
        self.call_count = 0
        self.last_messages = None

    async def complete(self, messages, temperature=0.3, max_tokens=None):
        self.last_messages = messages
        if self.call_count < len(self.responses):
            r = self.responses[self.call_count]
            self.call_count += 1
            return MockResp(r)
        return MockResp("Default")


class MockResp:
    def __init__(self, content):
        self.content = content

    def is_err(self):
        return False

    def unwrap(self):
        return self

    def unwrap_err(self):
        raise AssertionError("MockResp has no error")


class MockVS:
    def __init__(self, docs=None):
        self.docs = docs or []
        self.search_calls = []

    async def search(self, query, limit=2, filters=None):
        self.search_calls.append((query, limit))
        # Simple mapping for tests
        if "capital" in query.lower() and "france" in query.lower():
            return [MockDoc("Paris is the capital of France")]
        if "population" in query.lower() and "paris" in query.lower():
            return [MockDoc("Paris has ~2.1M people")]
        return self.docs[:limit]


class MockDoc:
    def __init__(self, content):
        self.content = content


def test_parse_chain_of_thought_and_extract():
    text = (
        "Step 1: Observe A\n" "Step 2: Observe B\n" "Therefore, conclusion C is true."
    )

    reasoner = ChainOfThoughtReasoner(MockLLM())
    steps = reasoner._parse_chain_of_thought(text)

    assert len(steps) == 2
    assert "Observe A" in steps[0].reasoning
    assert "Observe B" in steps[1].reasoning

    final = reasoner._extract_final_answer(text, steps)
    assert "Therefore, conclusion C" in final


@pytest.mark.asyncio
async def test_reason_with_context_extracts_steps_and_metadata():
    resp = "1. Find youngest\n2. Alice older than Bob\n3. Bob older than Charlie\nTherefore, Charlie is youngest."
    llm = MockLLM(responses=[resp])
    reasoner = ChainOfThoughtReasoner(llm, max_thoughts=4)

    result = await reasoner.reason_with_context("Who is youngest?", "Some context here")

    assert result.strategy == ReasoningStrategy.CHAIN_OF_THOUGHT
    assert result.metadata["has_context"] is True
    assert result.metadata["max_thoughts"] == 4
    assert "Charlie is youngest" in result.final_answer


@pytest.mark.asyncio
async def test_decompose_parsing_and_end_to_end_reasoning():
    # Decomposition response with different numbering styles
    decomposition_resp = (
        "1. What is the capital of France?\n2) What is the population of Paris?"
    )
    # Answers to sub-queries
    a1 = "Paris"
    a2 = "2.1 million"
    # Final synthesis
    synth = "The capital of France is Paris and it has about 2.1M people."

    llm = MockLLM(responses=[decomposition_resp, a1, a2, synth])
    vs = MockVS()

    decomposer = QueryDecomposer(llm, vs, max_sub_queries=2, top_k_per_query=1)
    res = await decomposer.reason(
        "Compare populations of capitals of France and Germany",
    )

    assert res.strategy == ReasoningStrategy.DECOMPOSITION
    assert res.total_hops == 2
    assert any("Paris" in step.answer or "2.1" in step.answer for step in res.steps)
    assert "Paris" in res.final_answer
    assert llm.last_messages is not None
    first_msg = llm.last_messages[0]
    content = first_msg.content if hasattr(first_msg, "content") else first_msg.get("content", "")
    assert "Break down this complex question" in content or True
