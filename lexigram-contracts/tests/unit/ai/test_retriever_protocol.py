"""Tests for Retriever contracts."""
from __future__ import annotations


def test_base_retriever():
    """BaseRetriever should have get_relevant_documents."""
    from lexigram.contracts.ai.retriever import BaseRetriever
    
    class FakeRetriever(BaseRetriever):
        def _get_relevant_documents(self, query: str) -> list[Any]:
            return []
    
    retriever = FakeRetriever()
    assert hasattr(retriever, 'get_relevant_documents')


def test_retriever_invoke():
    """Retriever should support invoke."""
    from lexigram.contracts.ai.retriever import BaseRetriever
    
    class FakeRetriever(BaseRetriever):
        def _get_relevant_documents(self, query: str) -> list[str]:
            return ["doc1", "doc2"]
    
    retriever = FakeRetriever()
    result = retriever.invoke("query")
    assert len(result) == 2
