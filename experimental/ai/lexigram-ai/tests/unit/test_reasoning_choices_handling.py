"""Tests for handling alternate LLM response shapes (choices, dicts)."""

from __future__ import annotations

from enum import Enum
from types import SimpleNamespace

import pytest


from lexigram.ai.rag.reasoning.base import ReasoningStrategy
from lexigram.ai.rag.reasoning.chain_of_thought import ChainOfThoughtReasoner
from lexigram.ai.rag.reasoning.iterative import IterativeRefinementReasoner


class RespChoices:
    def __init__(self, content):
        self.choices = [SimpleNamespace(message=SimpleNamespace(content=content))]


class _OkResult:
    def __init__(self, value):
        self._value = value

    def is_err(self):
        return False

    def unwrap(self):
        return self._value

    def unwrap_err(self):
        raise AssertionError("_OkResult has no error")


class MockLLMChoices:
    def __init__(self, responses=None):
        self.responses = responses or []
        self.call_count = 0

    async def complete(self, messages, temperature=0.3, max_tokens=None):
        if self.call_count < len(self.responses):
            r = self.responses[self.call_count]
            self.call_count += 1
            if isinstance(r, tuple) and r[0] == "choices":
                return _OkResult(RespChoices(r[1]))
            return _OkResult(SimpleNamespace(content=r))
        return _OkResult(SimpleNamespace(content=""))


class MockVS:
    async def search(self, query, limit=5, filters=None):
        return ["doc"]


@pytest.mark.asyncio
async def test_chain_of_thought_choices_response_parsed():
    resp = ("choices", "Step 1: A\nStep 2: B\nTherefore, result Z")
    llm = MockLLMChoices(responses=[resp])
    reasoner = ChainOfThoughtReasoner(llm)

    res = await reasoner.reason_with_context("Q?", "")

    assert res.strategy == ReasoningStrategy.CHAIN_OF_THOUGHT
    assert len(res.steps) >= 2
    assert "result Z" in res.final_answer


@pytest.mark.asyncio
async def test_iterative_handles_choices_and_answer_marker():
    # Initial answer via choices object
    # Refinement uses 'Answer:' marker
    responses = [
        ("choices", "Initial via choices"),
        "Critique\nAnswer: Refined via Answer marker",
    ]
    llm = MockLLMChoices(responses=responses)
    vs = MockVS()

    reasoner = IterativeRefinementReasoner(llm, vs, max_iterations=2)
    res = await reasoner.reason("Query")

    assert res.total_hops == 2
    assert "Refined via Answer marker" in res.final_answer
