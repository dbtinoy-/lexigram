"""Ask pipeline: embed, search, strategy rerank, cited synthesis — the **domain service** lesson.

This is the **domain service** — it owns the use-case logic ("embed →
search → rerank → synthesize") and delegates storage to the vector
collection.  No framework imports except ``Result``, ``Registry``, and
logging — the service is framework-agnostic by design.

The ask flow per question:

1. **Embed** — ``HashingEmbedder.embed([query])`` produces a fixed-dimension
   vector using the same IDF weights fitted on the corpus at boot
2. **Search** — ``collection.search(SearchQuery(...))`` retrieves the top-k
   nearest vectors by cosine similarity
3. **Rerank** — the selected ``RetrievalStrategy`` (vector or MMR) re-scores
   and prunes to top-k candidates
4. **Synthesize** — ``ExtractiveSynthesizer`` selects sentences from the
   candidates that answer the question, citing chunk IDs

Citation format: ``<source>#<chunk_index>`` (e.g. ``modules.md#0``).
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import cast

from lexigram.ai.rag.retrieval.strategies.mmr import MMRRetrievalStrategy
from lexigram.ai.rag.retrieval.strategies.vector import VectorRetrievalStrategy
from lexigram.contracts.ai.llm import EmbeddingClientProtocol
from lexigram.contracts.ai.rag import (
    RetrievalStrategyProtocol,
    SynthesizerProtocol,
)
from lexigram.contracts.ai.vector import (
    Document,
    RAGSearchResult,
    SearchResultProtocol,
)
from lexigram.contracts.data.vector.protocols import VectorCollectionProtocol
from lexigram.contracts.data.vector.types import SearchQuery, SearchResult
from lexigram.logging import get_logger
from lexigram.primitives import Registry
from lexigram.result import Err, Ok, Result
from rag_docs.errors import (
    DocsAskError,
    NoResultsError,
    SynthesisFailedError,
    UnknownStrategyError,
)
from rag_docs.repository.index_builder import IndexStats

logger = get_logger(__name__)

# Citation regex: matches ``source#chunk_index`` format produced by synthesis.
CITATION_PATTERN = re.compile(r"^(?P<source>.+)#(?P<index>\d+)$")

# Search/synthesis tuning constants — deliberately conservative for a demo.
_TOP_K_SEARCH = 6  # candidates retrieved from the vector store
_TOP_K_CANDIDATES = 4  # candidates passed to the synthesizer after rerank
_MIN_SCORE = 0.01  # cosine similarity floor (filters noise)


def _to_rag_result(result: SearchResult) -> RAGSearchResult:
    """Adapt a storage-layer hit into the protocol shape synthesizers expect.

    ``MemoryVectorCollection.search()`` returns ``SearchResult`` objects;
    ``SynthesizerProtocol.synthesize()`` expects ``SearchResultProtocol``.
    This adapter bridges the two.

    Args:
        result: Flat ``SearchResult`` returned by the vector collection.

    Returns:
        ``RAGSearchResult`` wrapping the chunk as a contracts ``Document``,
        satisfying ``SearchResultProtocol`` (``.document``, ``.score``,
        ``.metadata``).
    """
    return RAGSearchResult(
        document=Document(
            id=result.id,
            text=result.content or "",
            metadata=dict(result.metadata),
        ),
        score=result.score,
        metadata=dict(result.metadata),
    )


def _build_strategies() -> Registry[str, RetrievalStrategyProtocol]:
    """Framework Registry keyed by strategy id — no if/elif dispatch.

    ``Registry`` is Lexigram's extensible dispatch map.  Adding a new
    strategy means one ``register()`` call — no conditionals to update.
    """
    registry: Registry[str, RetrievalStrategyProtocol] = Registry()
    registry.register("vector", VectorRetrievalStrategy())
    registry.register("mmr", MMRRetrievalStrategy(lambda_param=0.7))
    return registry


# Module-level registry — built at import time.  The provider calls
# ``strategies_snapshot()`` to get a plain dict for the service.
STRATEGIES: Registry[str, RetrievalStrategyProtocol] = _build_strategies()


def strategies_snapshot() -> dict[str, RetrievalStrategyProtocol]:
    """Plain-mapping view of the strategy registry.

    Returns a ``dict`` snapshot so the service doesn't depend on
    ``Registry`` internals — just name → strategy lookup.
    """
    return {key: STRATEGIES.get(key) for key in STRATEGIES}


@dataclass(frozen=True)
class AskAnswer:
    """A synthesized answer with its supporting citations.

    Attributes:
        answer: The extractive answer text.
        citations: Chunk ids cited, each ``<source>#<index>``.
    """

    answer: str
    citations: tuple[str, ...]


class DocsAskService:
    """Result-typed question answering over the indexed docs corpus.

    Constructed by ``DocsAskProvider.boot`` during application startup;
    all collaborators arrive via constructor injection.  The service is
    stateless per request — each ``ask()`` call is independent.

    Args:
        collection: The populated vector collection.
        embedder: The deterministic embedder for queries.
        synthesizer: The extractive synthesizer.
        strategies: Name-to-strategy registry (no if/elif dispatch).
        stats: Corpus statistics captured at index build; defaults to zeros.
    """

    def __init__(
        self,
        collection: VectorCollectionProtocol,
        embedder: EmbeddingClientProtocol,
        synthesizer: SynthesizerProtocol,
        strategies: dict[str, RetrievalStrategyProtocol],
        stats: IndexStats | None = None,
    ) -> None:
        self._collection = collection
        self._embedder = embedder
        self._synthesizer = synthesizer
        self._strategies = strategies
        self.corpus_stats = stats or IndexStats(files=0, chunks=0)

    async def ask(
        self, query: str, strategy: str = "vector"
    ) -> Result[AskAnswer, DocsAskError]:
        """Answer a question with citations from the indexed corpus.

        Flow: embed → search → rerank → synthesize → return.
        Returns ``Ok(AskAnswer)`` on success with cited chunk ids, or
        ``Err``:
        - ``UnknownStrategyError`` — unregistered strategy name
        - ``NoResultsError`` — nothing retrieved above the score floor
        - ``SynthesisFailedError`` — synthesizer returned an error
        """
        if strategy not in self._strategies:
            return Err(UnknownStrategyError(f"unknown strategy {strategy!r}"))

        vector = (await self._embedder.embed([query]))[0]
        results = await self._collection.search(
            SearchQuery(
                vector=vector,
                top_k=_TOP_K_SEARCH,
                include_vectors=True,
                min_score=_MIN_SCORE,
            )
        )
        if not results:
            return Err(NoResultsError(f"nothing retrieved for {query!r}"))

        hits = [_to_rag_result(result) for result in results]
        candidates = await self._strategies[strategy].retrieve(
            query,
            cast("list[SearchResultProtocol]", hits),
            top_k=_TOP_K_CANDIDATES,
        )
        synthesis = await self._synthesizer.synthesize(query, candidates)
        if synthesis.is_err():
            return Err(SynthesisFailedError(str(synthesis.unwrap_err())))

        response = synthesis.unwrap()
        citations = tuple(
            candidate.document.id for candidate in candidates if candidate.document.id
        )
        logger.info(
            "docs_ask_complete",
            strategy=strategy,
            candidates=len(candidates),
            citations=len(citations),
        )
        return Ok(AskAnswer(answer=response.answer, citations=citations))


__all__ = ["CITATION_PATTERN", "STRATEGIES", "AskAnswer", "DocsAskService"]
