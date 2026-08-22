"""Tests for the ask pipeline: search -> strategy -> cited synthesis."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from lexigram.ai.rag.retrieval.strategies.mmr import MMRRetrievalStrategy
from lexigram.ai.rag.retrieval.strategies.vector import VectorRetrievalStrategy
from lexigram.ai.rag.synthesis.synthesizers.extractive import (
    ExtractiveSynthesizer,
)
from lexigram.contracts.ai.exceptions import RAGError
from lexigram.result import Err

from rag_docs.repository.embedder import HashingEmbedder
from rag_docs.errors import (
    NoResultsError,
    SynthesisFailedError,
    UnknownStrategyError,
)
from rag_docs.repository.index_builder import build_docs_store
from rag_docs.services.docs_ask import (
    CITATION_PATTERN,
    STRATEGIES,
    DocsAskService,
    strategies_snapshot,
)

QUESTION = "how do modules export services?"


def make_corpus(root: Path) -> Path:
    docs = root / "docs"
    docs.mkdir(parents=True)
    (docs / "modules.md").write_text(
        "# Modules\n\nModules export services through the exports list.\n"
        "Consumers resolve exported contracts from the container.\n"
        "Providers register services during application boot.\n"
    )
    return docs


async def make_service(tmp_path: Path) -> DocsAskService:
    # One shared embedder: build fits it on the corpus, the service queries
    # with the same IDF geometry (mirrors DocsAskProvider.boot).
    embedder = HashingEmbedder()
    _, collection, _ = await build_docs_store(make_corpus(tmp_path), embedder)
    return DocsAskService(
        collection=collection,
        embedder=embedder,
        synthesizer=ExtractiveSynthesizer(max_sentences=4),
        strategies=strategies_snapshot(),
    )


async def test_registry_has_vector_and_mmr() -> None:
    assert set(STRATEGIES) == {"vector", "mmr"}
    assert isinstance(STRATEGIES.get("vector"), VectorRetrievalStrategy)
    assert isinstance(STRATEGIES.get("mmr"), MMRRetrievalStrategy)


async def test_ask_returns_answer_with_citations(tmp_path: Path) -> None:
    service = await make_service(tmp_path)

    result = await service.ask(QUESTION)

    assert result.is_ok()
    answer = result.unwrap()
    assert answer.answer.strip()
    assert len(answer.citations) >= 1
    for citation in answer.citations:
        assert CITATION_PATTERN.match(citation), citation


async def test_ask_is_deterministic(tmp_path: Path) -> None:
    service = await make_service(tmp_path)

    first = await service.ask(QUESTION)
    second = await service.ask(QUESTION)

    assert first.unwrap() == second.unwrap()


async def test_mmr_strategy_also_answers(tmp_path: Path) -> None:
    service = await make_service(tmp_path)

    result = await service.ask(QUESTION, strategy="mmr")

    assert result.is_ok()
    assert result.unwrap().citations


async def test_unknown_strategy_is_err(tmp_path: Path) -> None:
    service = await make_service(tmp_path)

    result = await service.ask(QUESTION, strategy="bm25")

    assert result.is_err()
    assert isinstance(result.unwrap_err(), UnknownStrategyError)


async def test_no_match_is_err(tmp_path: Path) -> None:
    service = await make_service(tmp_path)

    result = await service.ask("zzzz qqqq xyzzy")

    assert result.is_err()
    assert isinstance(result.unwrap_err(), NoResultsError)


async def test_synthesis_failure_maps_to_err(
    tmp_path: Path, monkeypatch: Any
) -> None:
    service = await make_service(tmp_path)

    class FailingSynthesizer:
        async def synthesize(self, query: str, context: Any) -> Any:
            return Err(RAGError("boom"))

    monkeypatch.setattr(service, "_synthesizer", FailingSynthesizer())
    result = await service.ask(QUESTION)

    assert result.is_err()
    assert isinstance(result.unwrap_err(), SynthesisFailedError)
