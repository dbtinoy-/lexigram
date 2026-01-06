"""Tests for NamedSearchConfig, SearchConfig.backends, and SearchConfig.from_named()."""

from __future__ import annotations

import pytest

from lexigram.search.config import (
    BackendType,
    MeiliSearchConfig,
    NamedSearchConfig,
    PostgresSearchConfig,
    SearchConfig,
)


class TestNamedSearchConfigDefaults:
    """Test 1: NamedSearchConfig with only name uses defaults."""

    def test_defaults(self) -> None:
        entry = NamedSearchConfig(name="default_backend")

        assert entry.name == "default_backend"
        assert entry.primary is False
        assert entry.backend_type == BackendType.MEMORY
        assert entry.database is None
        assert entry.meilisearch is None
        assert entry.elasticsearch is None
        assert entry.typesense is None
        assert entry.postgres is None
        assert entry.mysql is None
        assert entry.sqlite is None
        assert entry.mongo is None


class TestNamedSearchConfigPrimary:
    """Test 2: NamedSearchConfig with primary=True."""

    def test_primary_flag(self) -> None:
        entry = NamedSearchConfig(name="primary", primary=True)

        assert entry.primary is True
        assert entry.name == "primary"


class TestNamedSearchConfigMeilisearch:
    """Test 3: NamedSearchConfig with meilisearch backend_type and config."""

    def test_meilisearch_entry(self) -> None:
        meili_cfg = MeiliSearchConfig(url="http://search.example.com:7700")
        entry = NamedSearchConfig(
            name="meili",
            backend_type=BackendType.MEILISEARCH,
            meilisearch=meili_cfg,
        )

        assert entry.backend_type == BackendType.MEILISEARCH
        assert entry.meilisearch is meili_cfg
        assert entry.meilisearch.url == "http://search.example.com:7700"


class TestNamedSearchConfigPostgres:
    """Test 4: NamedSearchConfig with postgres backend_type and database field."""

    def test_postgres_entry_with_database(self) -> None:
        entry = NamedSearchConfig(
            name="pg_search",
            backend_type=BackendType.POSTGRES,
            database="primary",
        )

        assert entry.backend_type == BackendType.POSTGRES
        assert entry.database == "primary"
        assert entry.postgres is None  # not set, caller can set as needed


class TestSearchConfigBackendsDefault:
    """Test 5: SearchConfig.backends defaults to empty list."""

    def test_backends_default_empty(self) -> None:
        config = SearchConfig()

        assert config.backends == []
        assert isinstance(config.backends, list)


class TestSearchConfigBackendsPopulated:
    """Test 6: SearchConfig with backends list populated."""

    def test_backends_list(self) -> None:
        backends = [
            NamedSearchConfig(name="primary", primary=True, backend_type=BackendType.MEMORY),
            NamedSearchConfig(name="secondary", backend_type=BackendType.SQLITE),
        ]
        config = SearchConfig(backends=backends)

        assert len(config.backends) == 2
        assert config.backends[0].name == "primary"
        assert config.backends[1].name == "secondary"
        assert config.backends[0].primary is True


class TestSearchConfigFromNamedMeilisearch:
    """Test 7: SearchConfig.from_named() with meilisearch entry."""

    def test_from_named_meilisearch(self) -> None:
        meili_cfg = MeiliSearchConfig(url="http://meili:7700")
        entry = NamedSearchConfig(
            name="meili_primary",
            primary=True,
            backend_type=BackendType.MEILISEARCH,
            meilisearch=meili_cfg,
        )

        result = SearchConfig.from_named(entry)

        assert result.backend_type == BackendType.MEILISEARCH
        assert result.meilisearch.url == "http://meili:7700"
        assert result.backends == []  # no recursion


class TestSearchConfigFromNamedPostgres:
    """Test 8: SearchConfig.from_named() with postgres entry preserves database on entry."""

    def test_from_named_postgres_database_accessible_on_entry(self) -> None:
        pg_cfg = PostgresSearchConfig()
        entry = NamedSearchConfig(
            name="pg_primary",
            backend_type=BackendType.POSTGRES,
            database="primary",
            postgres=pg_cfg,
        )

        # The database field is carried on the entry itself
        assert entry.database == "primary"

        result = SearchConfig.from_named(entry)

        assert result.backend_type == BackendType.POSTGRES
        assert result.backends == []  # no recursion


class TestNamedSearchConfigExported:
    """Test 9: NamedSearchConfig is exported from lexigram.search."""

    def test_export(self) -> None:
        import lexigram.search as search_pkg

        cls = getattr(search_pkg, "NamedSearchConfig")

        assert cls is NamedSearchConfig

    def test_in_all(self) -> None:
        import lexigram.search as search_pkg

        assert "NamedSearchConfig" in search_pkg.__all__
