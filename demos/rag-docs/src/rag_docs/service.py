"""Ask pipeline: embed, search, strategy rerank, cited synthesis."""

from __future__ import annotations

from dataclasses import dataclass
import re

from lexigram.ai.rag.retrieval.strategies.mmr import MMRRetrievalStrategy
from lexigram.ai.rag.retrieval.strategies.vector import VectorRetrievalStrategy
from lexigram.contracts.ai.llm import EmbeddingClientProtocol
from lexigram.contracts.ai.rag import (
    RetrievalStrategyProtocol,
    SynthesizerProtocol,
)
from lexigram.contracts.ai.vector import Document, RAGSearchResult
from lexigram.contracts.data.vector.protocols import VectorCollectionProtocol
from lexigram.contracts.data.vector.types import SearchQuery, SearchResult
from lexigram.result import Err, Ok, Result
from rag_docs.errors import (
    DocsAskError,
    NoResultsError,
    SynthesisFailedError,
    UnknownStrategyError,
)
from rag_docs.index_builder import IndexStats

CITATION_PATTERN = re.compile(r"^(?P<source>.+)#(?P<index>\d+)$")

_TOP_K_SEARCH = 6
_TOP_K_CANDIDATES = 4
_MIN_SCORE = 0.01


def _to_rag_result(result: SearchResult) -> RAGSearchResult:
    """Adapt a storage-layer hit into the protocol shape synthesizers expect.

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


STRATEGIES: dict[str, RetrievalStrategyProtocol] = {
    "vector": VectorRetrievalStrategy(),
    "mmr": MMRRetrievalStrategy(lambda_param=0.7),
}


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

        Args:
            query: The natural-language question.
            strategy: Registered retrieval strategy name.

        Returns:
            Ok(AskAnswer) with cited chunk ids, or Err:
            ``UnknownStrategyError`` (unregistered name),
            ``NoResultsError`` (nothing retrieved),
            ``SynthesisFailedError`` (synthesizer failed).
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
            query, hits, top_k=_TOP_K_CANDIDATES
        )
        synthesis = await self._synthesizer.synthesize(query, candidates)
        if synthesis.is_err():
            return Err(SynthesisFailedError(str(synthesis.unwrap_err())))

        response = synthesis.unwrap()
        citations = tuple(
            candidate.document.id for candidate in candidates if candidate.document.id
        )
        return Ok(AskAnswer(answer=response.answer, citations=citations))


__all__ = ["CITATION_PATTERN", "STRATEGIES", "AskAnswer", "DocsAskService"]
