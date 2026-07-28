"""RetrieverQueryEngine - Query engine using retriever + postprocessors + synthesizer."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from lexigram.contracts.ai.index import (
    Citation,
    QueryEngineError,
    QueryEngineResponse,
)
from lexigram.logging import (
    get_logger,
)

logger = get_logger(__name__)


class RetrieverQueryEngine:
    """Query engine using retriever, postprocessors, and synthesizer.

    Combines retrieval, node postprocessing, and response synthesis into
    a single query interface.

    Example:
        >>> engine = RetrieverQueryEngine(
        ...     retriever=retriever,
        ...     postprocessors=[reranker, deduplicator],
        ...     synthesizer=synthesizer,
        ... )
        >>> result = await engine.query("What is Lexigram?")
    """

    def __init__(
        self,
        retriever: Any,
        postprocessors: list[Any] | None = None,
        synthesizer: Any | None = None,
    ) -> None:
        """Initialize RetrieverQueryEngine.

        Args:
            retriever: The retriever for fetching relevant documents.
            postprocessors: Optional list of postprocessors to apply to retrieved nodes.
            synthesizer: Optional synthesizer for generating responses.
        """
        self._retriever = retriever
        self._postprocessors = postprocessors or []
        self._synthesizer = synthesizer

    async def query(
        self, query: str, **kwargs: Any
    ) -> QueryEngineResponse | QueryEngineError:
        """Process a query and return an answer with sources.

        Args:
            query: The user's query string.
            **kwargs: Query-specific parameters.

        Returns:
            Ok(QueryEngineResponse) on success.
            Err(QueryEngineError) on failure.
        """
        try:
            top_k = kwargs.get("top_k", 10)
            nodes_result = await self._retriever.retrieve(query, top_k=top_k)

            if nodes_result.is_err():
                return QueryEngineError(
                    f"Retrieval failed: {nodes_result.unwrap_err()}"
                )

            nodes = nodes_result.unwrap()

            for postprocessor in self._postprocessors:
                post_result = await postprocessor.postprocess(nodes)
                if post_result.is_err():
                    return QueryEngineError(
                        f"Postprocessing failed: {post_result.unwrap_err()}"
                    )
                nodes = post_result.unwrap()

            citations: list[Citation] = []
            for node in nodes:
                citations.append(
                    Citation(
                        node_id=node.id,
                        text=node.content[:200],
                        score=node.score,
                    )
                )

            answer = query
            tokens = 0
            cost = 0.0

            if self._synthesizer is not None:
                synth_result = await self._synthesizer.synthesize(query, nodes)
                if synth_result.is_ok():
                    response = synth_result.unwrap()
                    answer = response.answer
                    tokens = getattr(response, "tokens", 0)
                    cost = getattr(response, "cost", 0.0)

            return QueryEngineResponse(
                answer=answer,
                source_nodes=nodes,
                citations=citations,
                tokens=tokens,
                cost=cost,
            )

        except Exception as e:
            logger.error("query_failed", error=str(e))
            return QueryEngineError(f"Query failed: {e}")

    async def astream_query(
        self, query: str, **kwargs: Any
    ) -> AsyncIterator[QueryEngineResponse | QueryEngineError]:
        """Stream query results.

        Args:
            query: The user's query string.
            **kwargs: Query-specific parameters.

        Yields:
            QueryEngineResponse on success, QueryEngineError on failure.
        """
        result = await self.query(query, **kwargs)
        if isinstance(result, QueryEngineError):
            yield result
        else:
            yield result


__all__ = ["RetrieverQueryEngine"]
