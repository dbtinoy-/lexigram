"""Tests for lexigram-vector constants."""

from __future__ import annotations

import pytest

from lexigram.vector import constants


class TestVersion:
    def test_version_is_string(self) -> None:
        assert isinstance(constants.__version__, str)

    def test_version_format(self) -> None:
        assert constants.__version__ != ""


class TestEnvironmentConstants:
    def test_env_prefix(self) -> None:
        assert constants.ENV_PREFIX == "LEX_VECTOR__"

    def test_env_nested_delimiter(self) -> None:
        assert constants.ENV_NESTED_DELIMITER == "__"


class TestBatchSizeConstants:
    def test_default_upsert_batch_size(self) -> None:
        assert constants.DEFAULT_UPSERT_BATCH_SIZE == 100

    def test_default_delete_batch_size(self) -> None:
        assert constants.DEFAULT_DELETE_BATCH_SIZE == 1000

    def test_default_query_top_k(self) -> None:
        assert constants.DEFAULT_QUERY_TOP_K == 10

    def test_default_health_check_timeout(self) -> None:
        assert constants.DEFAULT_HEALTH_CHECK_TIMEOUT == 5.0


class TestPgvectorDefaults:
    def test_pgvector_default_lists(self) -> None:
        assert constants.PGVECTOR_DEFAULT_LISTS == 100

    def test_pgvector_default_probes(self) -> None:
        assert constants.PGVECTOR_DEFAULT_PROBES == 10

    def test_pgvector_default_ef_search(self) -> None:
        assert constants.PGVECTOR_DEFAULT_EF_SEARCH == 64


class TestHnswDefaults:
    def test_default_hnsw_m(self) -> None:
        assert constants.DEFAULT_HNSW_M == 16

    def test_default_hnsw_ef_construction(self) -> None:
        assert constants.DEFAULT_HNSW_EF_CONSTRUCTION == 200


class TestConnectionDefaults:
    def test_default_connect_timeout(self) -> None:
        assert constants.DEFAULT_CONNECT_TIMEOUT == 10.0

    def test_default_request_timeout(self) -> None:
        assert constants.DEFAULT_REQUEST_TIMEOUT == 30.0

    def test_default_max_retries(self) -> None:
        assert constants.DEFAULT_MAX_RETRIES == 3

    def test_default_retry_delay(self) -> None:
        assert constants.DEFAULT_RETRY_DELAY == 0.5


class TestBackendIdentifiers:
    def test_backend_memory(self) -> None:
        assert constants.BACKEND_MEMORY == "memory"

    def test_backend_pgvector(self) -> None:
        assert constants.BACKEND_PGVECTOR == "pgvector"

    def test_backend_pinecone(self) -> None:
        assert constants.BACKEND_PINECONE == "pinecone"

    def test_backend_qdrant(self) -> None:
        assert constants.BACKEND_QDRANT == "qdrant"

    def test_backend_chroma(self) -> None:
        assert constants.BACKEND_CHROMA == "chroma"

    def test_backend_weaviate(self) -> None:
        assert constants.BACKEND_WEAVIATE == "weaviate"


class TestExports:
    def test_all_contains_expected(self) -> None:
        expected = [
            "BACKEND_CHROMA",
            "BACKEND_MEMORY",
            "BACKEND_PGVECTOR",
            "BACKEND_PINECONE",
            "BACKEND_QDRANT",
            "BACKEND_WEAVIATE",
            "DEFAULT_CONNECT_TIMEOUT",
            "DEFAULT_DELETE_BATCH_SIZE",
            "DEFAULT_HEALTH_CHECK_TIMEOUT",
            "DEFAULT_HNSW_EF_CONSTRUCTION",
            "DEFAULT_HNSW_M",
            "DEFAULT_QUERY_TOP_K",
            "DEFAULT_REQUEST_TIMEOUT",
            "DEFAULT_RETRY_DELAY",
            "DEFAULT_UPSERT_BATCH_SIZE",
            "ENV_NESTED_DELIMITER",
            "ENV_PREFIX",
            "PGVECTOR_DEFAULT_EF_SEARCH",
            "PGVECTOR_DEFAULT_LISTS",
            "PGVECTOR_DEFAULT_PROBES",
            "__version__",
        ]
        assert constants.__all__ == expected