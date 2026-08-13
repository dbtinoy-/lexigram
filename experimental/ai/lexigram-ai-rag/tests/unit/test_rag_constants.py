"""Unit tests for RAG constants."""

from __future__ import annotations

import pytest


class TestRagConstants:
    """Test all RAG constant values."""

    def test_default_chunk_size(self) -> None:
        from lexigram.ai.rag.constants import DEFAULT_CHUNK_SIZE

        assert DEFAULT_CHUNK_SIZE == 512

    def test_default_chunk_overlap(self) -> None:
        from lexigram.ai.rag.constants import DEFAULT_CHUNK_OVERLAP

        assert DEFAULT_CHUNK_OVERLAP == 50

    def test_default_top_k(self) -> None:
        from lexigram.ai.rag.constants import DEFAULT_TOP_K

        assert DEFAULT_TOP_K == 5

    def test_default_similarity_threshold(self) -> None:
        from lexigram.ai.rag.constants import DEFAULT_SIMILARITY_THRESHOLD

        assert DEFAULT_SIMILARITY_THRESHOLD == 0.7

    def test_default_reranking_top_n(self) -> None:
        from lexigram.ai.rag.constants import DEFAULT_RERANKING_TOP_N

        assert DEFAULT_RERANKING_TOP_N == 3

    def test_default_query_cache_ttl(self) -> None:
        from lexigram.ai.rag.constants import DEFAULT_QUERY_CACHE_TTL_S

        assert DEFAULT_QUERY_CACHE_TTL_S == 3600

    def test_default_embedding_cache_size(self) -> None:
        from lexigram.ai.rag.constants import DEFAULT_EMBEDDING_CACHE_SIZE

        assert DEFAULT_EMBEDDING_CACHE_SIZE == 10_000

    def test_metric_rag_pipeline_duration_ms(self) -> None:
        from lexigram.ai.rag.constants import METRIC_RAG_PIPELINE_DURATION_MS

        assert METRIC_RAG_PIPELINE_DURATION_MS == "ai.rag.pipeline.duration_ms"

    def test_metric_rag_retrieved_chunks(self) -> None:
        from lexigram.ai.rag.constants import METRIC_RAG_RETRIEVED_CHUNKS

        assert METRIC_RAG_RETRIEVED_CHUNKS == "ai.rag.retrieved.chunks"

    def test_metric_rag_cache_hits(self) -> None:
        from lexigram.ai.rag.constants import METRIC_RAG_CACHE_HITS

        assert METRIC_RAG_CACHE_HITS == "ai.rag.cache.hits"

    def test_env_prefix(self) -> None:
        from lexigram.ai.rag.constants import ENV_PREFIX

        assert ENV_PREFIX == "LEX_AI_RAG__"

    def test_env_nested_delimiter(self) -> None:
        from lexigram.ai.rag.constants import ENV_NESTED_DELIMITER

        assert ENV_NESTED_DELIMITER == "__"

    def test_version_is_string(self) -> None:
        from lexigram.ai.rag.constants import __version__

        assert isinstance(__version__, str)
        assert len(__version__) > 0