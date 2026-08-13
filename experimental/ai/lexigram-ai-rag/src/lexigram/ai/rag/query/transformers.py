from __future__ import annotations

from collections.abc import Callable

from lexigram.ai.rag.query.base import (
    AbstractQueryTransformer,
    TransformationStrategy,
    TransformedQuery,
)
from lexigram.contracts import (
    ChatMessage,
    LLMClientProtocol,
)
from lexigram.logging import (
    get_logger,
)

logger = get_logger(__name__)


class QueryExpander(AbstractQueryTransformer):
    """Expand queries with synonyms and related terms."""

    def __init__(
        self,
        expansion_terms: dict | None = None,
        llm_client: LLMClientProtocol | None = None,
        max_expansions: int = 5,
        include_original: bool = True,
    ):
        self.expansion_terms = expansion_terms or {}
        self.llm_client = llm_client
        self.max_expansions = max_expansions
        self.include_original = include_original

    async def transform(self, query: str) -> TransformedQuery:
        expanded = []
        if self.include_original:
            expanded.append(query)

        for term, expansions in self.expansion_terms.items():
            if term.lower() in query.lower():
                for expansion in expansions[: self.max_expansions]:
                    expanded_query = query.replace(term, expansion)
                    if expanded_query not in expanded:
                        expanded.append(expanded_query)

        if self.llm_client and len(expanded) < self.max_expansions + 1:
            llm_expansions = await self._llm_expand(query)
            for exp in llm_expansions:
                if exp not in expanded and len(expanded) < self.max_expansions + 1:
                    expanded.append(exp)

        return TransformedQuery(
            original=query,
            transformed=expanded,
            strategy=TransformationStrategy.EXPANSION,
            metadata={"method": "hybrid" if self.llm_client else "predefined"},
        )

    async def _llm_expand(self, query: str) -> list[str]:
        if not self.llm_client:
            return []

        prompt = f"""Generate {self.max_expansions} alternative phrasings of this search query.
Each alternative should maintain the same intent but use different words or structure.

Query: {query}

Alternative queries (one per line):"""

        messages = [ChatMessage(role="user", content=prompt)]

        try:
            result = await self.llm_client.complete(
                messages=messages,
                temperature=0.7,
                max_tokens=200,
            )
            if result.is_err():
                raise result.unwrap_err()
            response = result.unwrap()

            text_response = response if isinstance(response, str) else response.content

            lines = [
                line.strip()
                for line in text_response.strip().split("\n")
                if line.strip()
            ]
            expansions = []
            for line in lines:
                cleaned = line.lstrip("0123456789.-) ")
                if cleaned and cleaned != query:
                    expansions.append(cleaned)

            return expansions[: self.max_expansions]
        except Exception as e:  # noqa: BLE001 — broadened intentionally; LLM expansion must not crash caller
            logger.error("query_expansion_failed", error=str(e), exc_info=True)
            return []

    @property
    def strategy(self) -> TransformationStrategy:
        return TransformationStrategy.EXPANSION


class MultiQueryGenerator(AbstractQueryTransformer):
    """Generate multiple query variations for parallel search."""

    def __init__(
        self,
        llm_client: LLMClientProtocol,
        num_queries: int = 3,
        include_original: bool = True,
        temperature: float = 0.8,
    ):
        self.llm_client = llm_client
        self.num_queries = num_queries
        self.include_original = include_original
        self.temperature = temperature

    async def transform(self, query: str) -> TransformedQuery:
        queries = []
        if self.include_original:
            queries.append(query)

        prompt = f"""You are an AI assistant helping to improve search queries.
Generate {self.num_queries} different versions of the following query.
Each version should:
- Maintain the original intent
- Use different keywords and phrasings
- Cover different aspects of the question

Original query: {query}

Generate {self.num_queries} alternative queries (one per line):"""

        messages = [ChatMessage(role="user", content=prompt)]

        try:
            result = await self.llm_client.complete(
                messages=messages,
                temperature=self.temperature,
                max_tokens=300,
            )
            if result.is_err():
                raise result.unwrap_err()
            response = result.unwrap()

            text_response = response if isinstance(response, str) else response.content

            lines = [
                line.strip()
                for line in text_response.strip().split("\n")
                if line.strip()
            ]
            for line in lines:
                cleaned = line.lstrip("0123456789.-) ")
                if cleaned and cleaned not in queries:
                    queries.append(cleaned)
                    if len(queries) >= self.num_queries + (
                        1 if self.include_original else 0
                    ):
                        break

        except (ValueError, TypeError, RuntimeError, OSError):
            if not queries:
                queries.append(query)

        return TransformedQuery(
            original=query,
            transformed=queries,
            strategy=TransformationStrategy.MULTI_QUERY,
            metadata={
                "temperature": self.temperature,
                "target_count": self.num_queries,
            },
        )

    @property
    def strategy(self) -> TransformationStrategy:
        return TransformationStrategy.MULTI_QUERY


class HyDEGenerator(AbstractQueryTransformer):
    """Generate hypothetical documents (HyDE) for the query."""

    def __init__(
        self,
        llm_client: LLMClientProtocol,
        num_documents: int = 1,
        doc_length: str = "medium",
        temperature: float = 0.7,
    ):
        self.llm_client = llm_client
        self.num_documents = num_documents
        self.doc_length = doc_length
        self.temperature = temperature

    async def transform(self, query: str) -> TransformedQuery:
        documents = []
        max_tokens = {"short": 150, "medium": 300, "long": 500}.get(
            self.doc_length,
            300,
        )

        prompt = f"""Write a detailed answer to the following question.
Provide a comprehensive response as if you were writing documentation or a textbook.

Question: {query}

Answer:"""

        messages = [ChatMessage(role="user", content=prompt)]

        for _ in range(self.num_documents):
            try:
                result = await self.llm_client.complete(
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=max_tokens,
                )
                if result.is_err():
                    raise result.unwrap_err()
                response = result.unwrap()

                text_response = (
                    response if isinstance(response, str) else response.content
                )

                if text_response and text_response.strip():
                    documents.append(text_response.strip())
            except (ValueError, TypeError, RuntimeError, OSError) as e:
                logger.debug("One generation failed while transforming queries: %s", e)
                continue

        if not documents:
            documents.append(query)

        return TransformedQuery(
            original=query,
            transformed=documents,
            strategy=TransformationStrategy.HYDE,
            metadata={
                "doc_length": self.doc_length,
                "temperature": self.temperature,
                "target_count": self.num_documents,
            },
        )

    @property
    def strategy(self) -> TransformationStrategy:
        return TransformationStrategy.HYDE


class QueryRewriter(AbstractQueryTransformer):
    """Rewrite queries for better retrieval."""

    def __init__(
        self,
        llm_client: LLMClientProtocol,
        instructions: str | None = None,
        temperature: float = 0.3,
    ):
        self.llm_client = llm_client
        self.instructions = instructions or self._default_instructions()
        self.temperature = temperature

    def _default_instructions(self) -> str:
        return """Rewrite the query to be more clear, specific, and effective for search.
- Fix spelling and grammar
- Expand abbreviations
- Add relevant context
- Make the intent explicit
- Keep it concise"""

    async def transform(self, query: str) -> TransformedQuery:
        prompt = f"""{self.instructions}

Original query: {query}

Rewritten query:"""

        messages = [ChatMessage(role="user", content=prompt)]

        try:
            result = await self.llm_client.complete(
                messages=messages,
                temperature=self.temperature,
                max_tokens=100,
            )
            if result.is_err():
                raise result.unwrap_err()
            response = result.unwrap()

            rewritten = response if isinstance(response, str) else response.content
            rewritten = rewritten.strip()

            if not rewritten or len(rewritten) < 3:
                rewritten = query
        except (ValueError, TypeError, RuntimeError, OSError):
            rewritten = query

        return TransformedQuery(
            original=query,
            transformed=[rewritten],
            strategy=TransformationStrategy.REWRITE,
            metadata={"instructions_used": bool(self.instructions)},
        )

    @property
    def strategy(self) -> TransformationStrategy:
        return TransformationStrategy.REWRITE


class CustomQueryTransformer(AbstractQueryTransformer):
    """Custom query transformer using user-defined function."""

    def __init__(
        self,
        transform_fn: Callable[[str], list[str]],
        strategy_name: str = "custom",
    ):
        self.transform_fn = transform_fn
        self.strategy_name = strategy_name

    async def transform(self, query: str) -> TransformedQuery:
        try:
            transformed = self.transform_fn(query)
            if not isinstance(transformed, list):
                transformed = [transformed]
        except (ValueError, TypeError, RuntimeError, OSError):
            transformed = [query]

        return TransformedQuery(
            original=query,
            transformed=transformed,
            strategy=TransformationStrategy.CUSTOM,
            metadata={"strategy_name": self.strategy_name},
        )

    @property
    def strategy(self) -> TransformationStrategy:
        return TransformationStrategy.CUSTOM


def create_transformer(
    strategy: TransformationStrategy,
    llm_client: LLMClientProtocol | None = None,
    **kwargs,
) -> AbstractQueryTransformer:
    """Factory function to create query transformers."""
    if strategy == TransformationStrategy.EXPANSION:
        return QueryExpander(llm_client=llm_client, **kwargs)
    if strategy == TransformationStrategy.MULTI_QUERY:
        if not llm_client:
            msg = "MULTI_QUERY requires llm_client"
            raise ValueError(msg)
        return MultiQueryGenerator(llm_client=llm_client, **kwargs)
    if strategy == TransformationStrategy.HYDE:
        if not llm_client:
            msg = "HYDE requires llm_client"
            raise ValueError(msg)
        return HyDEGenerator(llm_client=llm_client, **kwargs)
    if strategy == TransformationStrategy.REWRITE:
        if not llm_client:
            msg = "REWRITE requires llm_client"
            raise ValueError(msg)
        return QueryRewriter(llm_client=llm_client, **kwargs)
    msg = f"Unknown strategy: {strategy}"
    raise ValueError(msg)
