"""Tests for the deterministic hashing embedder."""

from __future__ import annotations

import math

import pytest

from lexigram.contracts.ai.llm import EmbeddingClientProtocol

from rag_docs.embedder import EMBEDDING_DIMENSION, HashingEmbedder


async def test_implements_embedding_client_protocol() -> None:
    assert isinstance(HashingEmbedder(), EmbeddingClientProtocol)


async def test_dimension_and_l2_norm() -> None:
    embedder = HashingEmbedder()

    vectors = await embedder.embed(["hello world", "second text"])

    assert len(vectors) == 2
    for vector in vectors:
        assert len(vector) == EMBEDDING_DIMENSION
        norm = math.sqrt(sum(component * component for component in vector))
        assert norm == pytest.approx(1.0, abs=1e-9)


async def test_same_text_same_vector_across_instances() -> None:
    first = await HashingEmbedder().embed(["modules export services"])
    second = await HashingEmbedder().embed(["modules export services"])

    assert first[0] == second[0]


async def test_different_text_differs() -> None:
    vectors = await HashingEmbedder().embed(["alpha beta", "gamma delta"])

    assert vectors[0] != vectors[1]


async def test_empty_text_yields_zero_vector() -> None:
    vectors = await HashingEmbedder().embed([""])

    assert all(component == 0.0 for component in vectors[0])
