"""Tests for GraphRAGIntegration."""

import pytest
pytest.importorskip("lexigram.ai.rag", reason="lexigram-ai-rag not installed")

from lexigram.ai.rag.knowledge_graph import GraphRAGIntegration
from lexigram.result import Ok
ENTITY_EXTRACTION_RESPONSE = """[
    {"name": "Alice", "type": "PERSON"},
    {"name": "OpenAI", "type": "ORGANIZATION"},
    {"name": "San Francisco", "type": "LOCATION"}
]"""

try:
    from lexigram.ai.llm.clients.mock import MockLLMClient
except ImportError as e:
    pytest.skip(f"mock llm client unavailable: {e}", allow_module_level=True)


class MockVectorStore:
    async def search(self, query, top_k=5):
        class MockResult:
            def __init__(self, id, text):
                self.id = id
                self.text = text

        return Ok(
            list(map(lambda i: MockResult(i, f"Result {i}"), range(top_k))),
        )


class TestGraphRAGIntegration:
    """Test GraphRAGIntegration."""

    @pytest.mark.asyncio
    async def test_expand_query_with_graph(self, populated_graph):
        """Test query expansion using graph."""
        mock_llm = MockLLMClient(responses=[ENTITY_EXTRACTION_RESPONSE])

        integration = GraphRAGIntegration(
            knowledge_graph=populated_graph,
            vector_store=MockVectorStore(),
            llm_client=mock_llm,
        )

        expanded = await integration.expand_query_with_graph(
            "Alice works at OpenAI",
            max_expansions=3,
        )

        assert len(expanded) >= 1
        assert expanded[0] == "Alice works at OpenAI"

    @pytest.mark.asyncio
    async def test_retrieve_with_graph(self, populated_graph):
        """Test graph-enhanced retrieval."""
        mock_llm = MockLLMClient(responses=[ENTITY_EXTRACTION_RESPONSE])

        integration = GraphRAGIntegration(
            knowledge_graph=populated_graph,
            vector_store=MockVectorStore(),
            llm_client=mock_llm,
        )

        results = await integration.retrieve_with_graph(
            "test query", top_k=3, expand=False,
        )

        assert len(results) == 3
