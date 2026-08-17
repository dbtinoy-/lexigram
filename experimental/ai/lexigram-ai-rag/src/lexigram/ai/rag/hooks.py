"""Root hook payload surface for lexigram-ai-rag.

Defines canonical payload dataclasses for RAG pipeline lifecycle hook points.
Actual hook registration and invocation use the framework's string-keyed
``HookRegistryProtocol`` action/filter APIs.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "RAGAnswerSynthesizedHook",
    "RAGDocumentsRetrievedHook",
    "RAGPipelineStartedHook",
]


@dataclass(frozen=True, kw_only=True)
class RAGPipelineStartedHook:
    """Payload fired when a RAG pipeline begins processing a query.

    Attributes:
        pipeline_name: Name or identifier of the pipeline that started.
    """

    pipeline_name: str


@dataclass(frozen=True, kw_only=True)
class RAGDocumentsRetrievedHook:
    """Payload fired after the retrieval stage returns candidate chunks.

    Attributes:
        chunk_count: Number of chunks returned by the retrieval step.
    """

    chunk_count: int


@dataclass(frozen=True, kw_only=True)
class RAGAnswerSynthesizedHook:
    """Payload fired after the synthesis stage produces a final answer.

    Attributes:
        pipeline_name: Name or identifier of the pipeline that synthesised
            the answer.
    """

    pipeline_name: str
