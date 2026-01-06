"""Retrieval-Augmented Generation pipeline.

Implements a three-stage RAG pipeline:

1. **Embed** — convert the query text into a vector using
   :class:`~lexigram.contracts.ai.llm.EmbeddingClientProtocol`.
2. **Retrieve** — search the vector store for semantically similar documents
   using :class:`~lexigram.contracts.ai.vector.DocumentVectorStoreProtocol`.
3. **Generate** — synthesise an answer from the retrieved context using
   :class:`~lexigram.contracts.ai.llm.LLMClientProtocol`.

Pattern demonstrated:
- Constructor injection of three protocol dependencies
- Chained ``Result[T, E]`` through all three stages
- Citation metadata threaded from retrieved documents to the answer
- Structured logging at each stage
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from lexigram.contracts.ai.exceptions import LLMError, RAGError
from lexigram.contracts.ai.llm import (
    ChatMessage,
    EmbeddingClientProtocol,
    LLMClientProtocol,
    Role,
)
from lexigram.contracts.ai.rag import RetrievalError, SynthesisError
from lexigram.contracts.ai.vector import DocumentVectorStoreProtocol
from lexigram.logging import get_logger
from lexigram.result import Err, Ok, Result

if TYPE_CHECKING:
    from lexigram.contracts.ai.vector import SearchResultProtocol

logger = get_logger(__name__)

_SYNTHESIS_SYSTEM_PROMPT = """\
You are a precise, citation-aware AI assistant.
Answer the user's question using only the provided context documents.
If the context does not contain enough information to answer the question,
say so honestly rather than speculating.
Keep your answer concise and factual.\
"""

_SYNTHESIS_USER_TEMPLATE = """\
Context documents:
{context}

Question: {question}

Answer:\
"""


@dataclass(frozen=True)
class RagQuery:
    """Input for a single RAG query.

    Attributes:
        query: The user's question in natural language.
        top_k: Maximum number of documents to retrieve.
        score_threshold: Minimum relevance score for inclusion.
        session_id: Optional session identifier for tracing.
        filters: Optional metadata filters forwarded to the vector store.
    """

    query: str
    top_k: int = 5
    score_threshold: float = 0.5
    session_id: str | None = None
    filters: dict[str, Any] | None = None


@dataclass(frozen=True)
class SourceDocument:
    """A retrieved document used as evidence in a RAG answer.

    Attributes:
        text: Document text content.
        score: Relevance score from the vector search.
        metadata: Document-level metadata (e.g. source URL, title).
    """

    text: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RagAnswer:
    """Output of a successful RAG query.

    Attributes:
        answer: The synthesised answer text.
        model: Model that generated the answer.
        sources: Retrieved documents used as context.
        query: The original query this answer addresses.
    """

    answer: str
    model: str
    sources: list[SourceDocument]
    query: str


class RAGPipeline:
    """Three-stage RAG pipeline: embed → retrieve → generate.

    Composes an embedding client, a vector store, and an LLM client into a
    single callable.  All three dependencies are injected via the constructor
    so they can be swapped freely in tests and between environments.

    Args:
        llm: LLM client for answer synthesis.
        embedder: Embedding client for query vectorisation.
        vector_store: Document vector store for semantic retrieval.
    """

    def __init__(
        self,
        llm: LLMClientProtocol,
        embedder: EmbeddingClientProtocol,
        vector_store: DocumentVectorStoreProtocol,
    ) -> None:
        self._llm = llm
        self._embedder = embedder
        self._vector_store = vector_store

    async def run(
        self,
        query: RagQuery,
    ) -> Result[RagAnswer, RAGError | LLMError]:
        """Execute the full RAG pipeline for *query*.

        Stages run sequentially:
        1. Embed the query text.
        2. Search the vector store for the top-k most relevant documents.
        3. Build a synthesis prompt and generate the answer.

        Args:
            query: RAG query containing the question and retrieval settings.

        Returns:
            ``Ok(RagAnswer)`` on success.
            ``Err(RetrievalError)`` when embedding or retrieval fails.
            ``Err(SynthesisError)`` when the LLM synthesis step fails.
        """
        logger.info(
            "rag_pipeline.running",
            query_length=len(query.query),
            top_k=query.top_k,
            session_id=query.session_id,
        )

        # Stage 1: Embed
        embed_result = await self._embed_query(query.query)
        if embed_result.is_err():
            return Err(embed_result.unwrap_err())

        query_vector = embed_result.unwrap()

        # Stage 2: Retrieve
        retrieve_result = await self._retrieve(
            query_vector,
            top_k=query.top_k,
            score_threshold=query.score_threshold,
            filters=query.filters,
        )
        if retrieve_result.is_err():
            return Err(retrieve_result.unwrap_err())

        hits = retrieve_result.unwrap()

        logger.info(
            "rag_pipeline.retrieved",
            hit_count=len(hits),
            session_id=query.session_id,
        )

        # Stage 3: Generate
        generate_result = await self._synthesise(query.query, hits)
        if generate_result.is_err():
            return Err(generate_result.unwrap_err())

        content, model = generate_result.unwrap()

        sources = [
            SourceDocument(
                text=hit.document.text,
                score=hit.score,
                metadata=hit.document.metadata,
            )
            for hit in hits
        ]

        logger.info(
            "rag_pipeline.completed",
            model=model,
            sources=len(sources),
            session_id=query.session_id,
        )

        return Ok(
            RagAnswer(
                answer=content,
                model=model,
                sources=sources,
                query=query.query,
            )
        )

    # ------------------------------------------------------------------
    # Private stage helpers
    # ------------------------------------------------------------------

    async def _embed_query(
        self, text: str
    ) -> Result[list[float], RetrievalError]:
        """Vectorise *text* using the embedding client.

        Args:
            text: Query text to embed.

        Returns:
            ``Ok(vector)`` on success, ``Err(RetrievalError)`` on failure.
        """
        try:
            vectors = await self._embedder.embed([text])
        except Exception as exc:
            logger.warning("rag_pipeline.embed_failed", error=str(exc))
            return Err(
                RetrievalError(
                    f"Embedding failed: {exc}",
                    details={"query_length": len(text)},
                )
            )

        if not vectors:
            return Err(RetrievalError("Embedding returned empty result"))

        return Ok(vectors[0])

    async def _retrieve(
        self,
        query_vector: list[float],
        *,
        top_k: int,
        score_threshold: float,
        filters: dict[str, Any] | None,
    ) -> Result[list[SearchResultProtocol], RetrievalError]:
        """Search the vector store for documents similar to *query_vector*.

        Args:
            query_vector: Query embedding vector.
            top_k: Maximum number of results to return.
            score_threshold: Minimum relevance score.
            filters: Optional metadata filters.

        Returns:
            ``Ok(hits)`` on success, ``Err(RetrievalError)`` on failure.
        """
        result = await self._vector_store.search(
            query_vector,
            top_k=top_k,
            filters=filters,
            score_threshold=score_threshold,
        )

        if result.is_err():
            error = result.unwrap_err()
            logger.warning("rag_pipeline.retrieval_failed", error=str(error))
            return Err(
                RetrievalError(
                    f"Vector store search failed: {error}",
                    details={"top_k": top_k},
                )
            )

        hits = result.unwrap()
        return Ok(hits)

    async def _synthesise(
        self,
        question: str,
        hits: list[SearchResultProtocol],
    ) -> Result[tuple[str, str], SynthesisError]:
        """Generate an answer from the retrieved documents.

        Args:
            question: The original user question.
            hits: Retrieved search results used as context.

        Returns:
            ``Ok((answer_text, model_name))`` on success,
            ``Err(SynthesisError)`` when the LLM call fails.
        """
        context = self._format_context(hits)

        messages: list[ChatMessage] = [
            ChatMessage(role=Role.SYSTEM, content=_SYNTHESIS_SYSTEM_PROMPT),
            ChatMessage(
                role=Role.USER,
                content=_SYNTHESIS_USER_TEMPLATE.format(
                    context=context, question=question
                ),
            ),
        ]

        result = await self._llm.complete(messages)

        if result.is_err():
            error = result.unwrap_err()
            logger.warning("rag_pipeline.synthesis_failed", error=str(error))
            return Err(
                SynthesisError(
                    f"LLM synthesis failed: {error}",
                    details={"source_count": len(hits)},
                )
            )

        completion = result.unwrap()
        return Ok((completion.content, completion.model))

    @staticmethod
    def _format_context(hits: list[SearchResultProtocol]) -> str:
        """Format retrieved documents into a numbered context string.

        Args:
            hits: Search results to format.

        Returns:
            Numbered, newline-delimited context string.
        """
        if not hits:
            return "(No relevant documents found.)"

        parts = [
            f"[{i + 1}] (score={hit.score:.3f})\n{hit.document.text}"
            for i, hit in enumerate(hits)
        ]
        return "\n\n".join(parts)


__all__ = [
    "RAGPipeline",
    "RagAnswer",
    "RagQuery",
    "SourceDocument",
]
