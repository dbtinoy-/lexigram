"""Additional edge-case tests for reasoning modules."""

from __future__ import annotations

from enum import Enum

import pytest
pytest.importorskip("lexigram.ai.rag", reason="lexigram-ai-rag not installed")

from lexigram.ai.rag.reasoning.chain_of_thought import ChainOfThoughtReasoner
from lexigram.ai.rag.reasoning.iterative import IterativeRefinementReasoner


class MockLLM:
    def __init__(self, responses=None):
        self.responses = responses or []
        self.call_count = 0

    async def complete(self, messages, temperature=0.3, max_tokens=None):
        if self.call_count < len(self.responses):
            r = self.responses[self.call_count]
            self.call_count += 1
            return MockResp(r)
        return MockResp("")


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
    async def search(self, query, limit=5, filters=None):
        return ["doc1", {"content": "doc2"}, "doc3"]


@pytest.mark.asyncio
async def test_iterative_confidence_cap():
    # Large number of iterations should cap confidence at 0.95
    responses = list(map(lambda i: f"Answer {i}", range(1, 12)))
    llm = MockLLM(responses=responses)
    vs = MockVS()

    reasoner = IterativeRefinementReasoner(llm, vs, max_iterations=10)
    res = await reasoner.reason("Test cap")

    assert res.total_hops == 10
    assert res.steps[-1].confidence == pytest.approx(0.95, 0.001)


def test_chain_of_thought_parse_various_markers():
    text = (
        "- First observation\n"
        "• Second observation continued\n"
        "Thought 3: Third observation\n"
        "Additional detail for third\n"
        "Thus, final conclusion here which is lengthy enough to be chosen."
    )

    reasoner = ChainOfThoughtReasoner(None)
    steps = reasoner._parse_chain_of_thought(text)

    assert len(steps) >= 3
    assert "First observation" in steps[0].reasoning
    assert "Second observation" in steps[1].reasoning
    assert "Third observation" in steps[2].reasoning

    # When no explicit conclusion marker, extract final answer from last long line
    final = reasoner._extract_final_answer(text, steps)
    assert "final conclusion" in final


def test_chain_of_thought_no_steps_and_short_lines():
    text = "Short line\nTiny\nA short phrase"
    reasoner = ChainOfThoughtReasoner(None)
    steps = reasoner._parse_chain_of_thought(text)

    assert steps == []
    final = reasoner._extract_final_answer(text, steps)
    assert final == "Unable to extract final answer."
