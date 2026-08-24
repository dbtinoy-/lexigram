"""Tests for KnowledgeGraphBuilder."""

import pytest
pytest.importorskip("lexigram.ai.rag", reason="lexigram-ai-rag not installed")

from lexigram.ai.rag.knowledge_graph import KnowledgeGraph, KnowledgeGraphBuilder
ENTITY_EXTRACTION_RESPONSE = """[
    {"name": "Alice", "type": "PERSON"},
    {"name": "OpenAI", "type": "ORGANIZATION"},
    {"name": "San Francisco", "type": "LOCATION"}
]"""

RELATIONSHIP_EXTRACTION_RESPONSE = """[
    {"source": "Alice", "target": "OpenAI", "type": "WORKS_AT", "confidence": 0.95},
    {"source": "OpenAI", "target": "San Francisco", "type": "LOCATED_IN", "confidence": 0.9}
]"""

try:
    from lexigram.ai.llm.clients.mock import MockLLMClient
except ImportError as e:
    pytest.skip(f"mock llm client unavailable: {e}", allow_module_level=True)


class TestKnowledgeGraphBuilder:
    """Test KnowledgeGraphBuilder."""

    @pytest.mark.asyncio
    async def test_build_from_text(self):
        """Test building graph from text."""
        mock_llm = MockLLMClient(
            responses=[ENTITY_EXTRACTION_RESPONSE, RELATIONSHIP_EXTRACTION_RESPONSE],
        )

        builder = KnowledgeGraphBuilder(llm_client=mock_llm)
        text = "Alice works at OpenAI in San Francisco."

        kg = await builder.build_from_text(text)

        assert len(kg) == 3
        stats = kg.get_stats()
        assert stats["total_relationships"] == 2

    @pytest.mark.asyncio
    async def test_build_from_documents_merged(self):
        """Test building graph from multiple documents (merged)."""
        mock_llm = MockLLMClient(
            responses=[
                ENTITY_EXTRACTION_RESPONSE,
                RELATIONSHIP_EXTRACTION_RESPONSE,
                ENTITY_EXTRACTION_RESPONSE,
                RELATIONSHIP_EXTRACTION_RESPONSE,
            ],
        )

        builder = KnowledgeGraphBuilder(llm_client=mock_llm)
        documents = [
            "Alice works at OpenAI in San Francisco.",
            "Alice works at OpenAI in San Francisco.",
        ]

        kg = await builder.build_from_documents(documents, merge=True)

        assert isinstance(kg, KnowledgeGraph)
        assert len(kg) >= 3

    @pytest.mark.asyncio
    async def test_build_from_documents_separate(self):
        """Test building separate graphs from documents."""
        mock_llm = MockLLMClient(
            responses=[
                ENTITY_EXTRACTION_RESPONSE,
                RELATIONSHIP_EXTRACTION_RESPONSE,
                ENTITY_EXTRACTION_RESPONSE,
                RELATIONSHIP_EXTRACTION_RESPONSE,
            ],
        )

        builder = KnowledgeGraphBuilder(llm_client=mock_llm)
        documents = [
            "Alice works at OpenAI.",
            "Bob works at Google.",
        ]

        graphs = await builder.build_from_documents(documents, merge=False)

        assert isinstance(graphs, list)
        assert len(graphs) == 2
        assert all(isinstance(g, KnowledgeGraph) for g in graphs)
