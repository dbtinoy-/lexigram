"""End-to-end smoke test for AI parity features."""

from __future__ import annotations

import pytest

from lexigram.contracts.ai.evaluation import EvaluationDataset, EvaluationSample
from lexigram.contracts.ai.llm import Role
from lexigram.contracts.ai.retrievers import RetrievalQuery, RetrievedNode
from lexigram.ai.evaluation.harness.runner import EvaluationHarness
from lexigram.ai.evaluation.evaluators.criteria import CriteriaEvaluator
from lexigram.ai.llm.parsers import JSONOutputParser
from lexigram.ai.llm.runnable import RunnableLambda


@pytest.mark.asyncio
async def test_parity_end_to_end():
    """One test, every façade, governance preserved."""

    # Runnable composition using RunnableSequence
    def add_one(x: int) -> int:
        return x + 1

    def multiply_two(x: int) -> int:
        return x * 2

    from lexigram.ai.llm.runnable import RunnableLambda, RunnableSequence

    r1 = RunnableLambda(add_one)
    r2 = RunnableLambda(multiply_two)
    chain = RunnableSequence(r1, r2)
    result = chain.invoke(3)
    assert result == 8  # (3 + 1) * 2 = 8

    # JSON Parser
    parser = JSONOutputParser()
    result = parser.parse('{"name": "test", "value": 42}')
    assert result == {"name": "test", "value": 42}

    # Evaluation harness
    harness = EvaluationHarness()
    dataset = EvaluationDataset(
        name="smoke_test",
        samples=[
            EvaluationSample(
                id="1",
                input="What is 2+2?",
                reference="4",
                metadata={},
            )
        ],
        metadata={},
    )
    evaluator = CriteriaEvaluator()
    report = await harness.run(dataset, evaluator)
    assert report.total_samples == 1
    assert report.dataset_name == "smoke_test"


@pytest.mark.asyncio
async def test_retriever_protocol():
    """Test RetrieverProtocol compliance."""
    from lexigram.contracts.ai.retrievers import RetrieverProtocol, RetrieverError

    class MockRetriever:
        async def retrieve(self, query: RetrievalQuery):
            from lexigram.result import Ok

            return Ok(
                [
                    RetrievedNode(
                        id="1",
                        content="test content",
                        score=0.9,
                        metadata={},
                    )
                ]
            )

    retriever = MockRetriever()
    assert isinstance(retriever, RetrieverProtocol)

    result = await retriever.retrieve(RetrievalQuery(query="test", top_k=10))
    assert result.is_ok()
    nodes = result.unwrap()
    assert len(nodes) == 1
    assert nodes[0].content == "test content"


@pytest.mark.asyncio
async def test_callback_manager():
    """Test CallbackManagerImpl basic functionality."""
    from lexigram.ai.observability.callbacks.manager import CallbackManagerImpl

    manager = CallbackManagerImpl()

    class MockHandler:
        async def on_llm_start(self, run_id, parent_run_id, prompt, model):
            pass

        async def on_llm_new_token(self, run_id, token):
            pass

        async def on_llm_end(self, run_id, response):
            pass

        async def on_llm_error(self, run_id, error):
            pass

        async def on_chain_start(self, run_id, name, inputs):
            pass

        async def on_chain_end(self, run_id, outputs):
            pass

        async def on_tool_start(self, run_id, tool_name, inputs):
            pass

        async def on_tool_end(self, run_id, outputs):
            pass

        async def on_agent_action(self, run_id, action):
            pass

        async def on_agent_finish(self, run_id, output):
            pass

        async def on_retriever_start(self, run_id, query):
            pass

        async def on_retriever_end(self, run_id, results):
            pass

    handler = MockHandler()
    manager.register(handler)
    assert handler in manager._handlers

    child = manager.child("parent-1")
    assert child._parent is not None
    assert handler in child._handlers
