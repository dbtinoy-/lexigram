"""SubQuestionQueryEngine - Query engine using multi-source decomposition."""

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


class SubQuestionQueryEngine:
    """Query engine that decomposes complex queries into sub-questions.

    For multi-hop or multi-source queries, this engine decomposes the
    original query into sub-questions, answers each, and synthesizes
    a final response.

    Example:
        >>> engine = SubQuestionQueryEngine(
        ...     query_engines={"docs": doc_engine, "web": web_engine},
        ...     llm_client=llm_client,
        ... )
        >>> result = await engine.query("Compare X and Y from docs and web")
    """

    def __init__(
        self,
        query_engines: dict[str, Any],
        llm_client: Any | None = None,
        max_sub_questions: int = 5,
    ) -> None:
        """Initialize SubQuestionQueryEngine.

        Args:
            query_engines: Mapping of source names to query engine instances.
            llm_client: Optional LLM client for query decomposition.
            max_sub_questions: Maximum number of sub-questions to generate.
        """
        self._query_engines = query_engines
        self._llm_client = llm_client
        self._max_sub_questions = max_sub_questions

    async def query(
        self, query: str, **kwargs: Any
    ) -> QueryEngineResponse | QueryEngineError:
        """Process a query by decomposing into sub-questions.

        Args:
            query: The user's query string.
            **kwargs: Query-specific parameters.

        Returns:
            Ok(QueryEngineResponse) on success.
            Err(QueryEngineError) on failure.
        """
        try:
            sub_questions = await self._decompose_query(query)

            if not sub_questions:
                return QueryEngineError("Failed to decompose query into sub-questions")

            all_sources = []
            all_citations: list[Citation] = []
            answers: list[str] = []

            for sq in sub_questions[: self._max_sub_questions]:
                source_name = self._assign_to_source(sq)
                engine = self._query_engines.get(source_name)

                if engine is None:
                    logger.warning("no_engine_for_source", source=source_name)
                    continue

                result = await engine.query(sq, **kwargs)
                if isinstance(result, QueryEngineError):
                    logger.warning("sub_query_failed", query=sq, error=str(result))
                    continue

                answers.append(result.answer)
                all_sources.extend(result.source_nodes)
                all_citations.extend(result.citations)

            final_answer = " ".join(answers) if answers else query

            all_results: list[QueryEngineResponse] = []
            for sq in sub_questions[: self._max_sub_questions]:
                source_name = self._assign_to_source(sq)
                engine = self._query_engines.get(source_name)
                if engine:
                    result = await engine.query(sq, **kwargs)
                    if not isinstance(result, QueryEngineError):
                        all_results.append(result)

            total_tokens = sum(getattr(r, "tokens", 0) for r in all_results)
            total_cost = sum(getattr(r, "cost", 0.0) for r in all_results)

            return QueryEngineResponse(
                answer=final_answer,
                source_nodes=all_sources,
                citations=all_citations,
                tokens=total_tokens,
                cost=total_cost,
            )

        except Exception as e:
            logger.error("sub_question_query_failed", error=str(e))
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

    async def _decompose_query(self, query: str) -> list[str]:
        """Decompose a complex query into sub-questions.

        Args:
            query: The original query.

        Returns:
            List of sub-questions.
        """
        if self._llm_client is None:
            return [query]

        prompt = f"""Decompose the following question into 2-5 simpler sub-questions that can be answered independently.
Each sub-question should focus on one aspect of the original question.

Original question: {query}

Sub-questions (one per line):"""

        try:
            response = await self._llm_client.complete(prompt)
            text = response.content if hasattr(response, "content") else str(response)
            sub_questions = [q.strip() for q in text.split("\n") if q.strip()]
            return sub_questions[: self._max_sub_questions]
        except Exception as e:
            logger.warning("query_decomposition_failed", error=str(e))
            return [query]

    def _assign_to_source(self, sub_question: str) -> str:
        """Assign a sub-question to the appropriate source.

        Args:
            sub_question: The sub-question to assign.

        Returns:
            Source name.
        """
        sub_lower = sub_question.lower()
        for source_name in self._query_engines:
            if source_name in sub_lower:
                return source_name
        return (
            next(iter(self._query_engines.keys())) if self._query_engines else "default"
        )


__all__ = ["SubQuestionQueryEngine"]
