"""Tests for DbSearchBackendRegistry."""

from __future__ import annotations

import pytest

from lexigram.search.backends.db_registry import DbSearchBackendRegistry
from lexigram.search.backends.mysql import MySQLDatabaseSearchBackend
from lexigram.search.backends.postgres import PostgresDatabaseSearchBackend
from lexigram.search.config import BackendType


class FakeDBProvider:
    """Minimal stand-in for DatabaseProviderProtocol."""


def test_postgres_resolves_to_postgres_backend() -> None:
    registry = DbSearchBackendRegistry.with_defaults()
    backend = registry.create_db_backend(BackendType.POSTGRES, FakeDBProvider())
    assert isinstance(backend, PostgresDatabaseSearchBackend)


def test_mysql_resolves_to_mysql_backend() -> None:
    registry = DbSearchBackendRegistry.with_defaults()
    backend = registry.create_db_backend(BackendType.MYSQL, FakeDBProvider())
    assert isinstance(backend, MySQLDatabaseSearchBackend)


def test_non_db_backend_raises_runtime_error() -> None:
    registry = DbSearchBackendRegistry.with_defaults()
    with pytest.raises(RuntimeError, match="Unsupported DB-backed search backend"):
        registry.create_db_backend(BackendType.MEILISEARCH, FakeDBProvider())
