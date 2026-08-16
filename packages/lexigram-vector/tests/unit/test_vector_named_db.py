"""Tests for PgVectorConfig.database field and named DB resolution in VectorProvider."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lexigram.vector.config import PgVectorConfig, VectorConfig


def test_pgvector_config_default_database() -> None:
    """PgVectorConfig.database defaults to 'primary'."""
    cfg = PgVectorConfig()
    assert cfg.database == "primary"


def test_pgvector_config_custom_database() -> None:
    """PgVectorConfig.database can be set to any named backend."""
    cfg = PgVectorConfig(database="rag")
    assert cfg.database == "rag"


def test_vector_config_pgvector_database_propagated() -> None:
    """VectorConfig.pgvector.database is accessible."""
    cfg = VectorConfig(backend="pgvector", pgvector=PgVectorConfig(database="rag"))
    assert cfg.pgvector.database == "rag"


@pytest.mark.asyncio
async def test_pgvector_boot_resolves_named_database() -> None:
    """VectorProvider.boot() resolves the named database when backend=pgvector."""

    from lexigram.contracts.data.sql.database import DatabaseProviderProtocol
    from lexigram.di.markers import Named
    from lexigram.vector.di.provider import VectorProvider

    config = VectorConfig(backend="pgvector", pgvector=PgVectorConfig(database="rag"))
    provider = VectorProvider(config=config)

    mock_db = MagicMock(spec=DatabaseProviderProtocol)
    mock_store = MagicMock()
    mock_store.connect = AsyncMock()

    mock_container = MagicMock()

    async def fake_resolve(key: object) -> object:
        from typing import Annotated as Ann
        from typing import get_args, get_origin

        if get_origin(key) is Ann:
            args = get_args(key)
            for item in args[1:]:
                if isinstance(item, Named) and item.name == "rag":
                    return mock_db
        raise ValueError(f"Unexpected resolve call: {key}")

    mock_container.resolve = fake_resolve

    # Patch the source module — PgVectorStore is lazily imported inside boot(),
    # so there is no 'provider.PgVectorStore' module-level name to patch.
    with patch(
        "lexigram.vector.backends.pgvector.PgVectorStore", return_value=mock_store
    ):
        await provider.boot(mock_container)

    mock_store.connect.assert_awaited_once()
    assert provider._store is mock_store


@pytest.mark.asyncio
async def test_pgvector_boot_resolves_primary_database_by_default() -> None:
    """VectorProvider.boot() uses Named('primary') when database defaults to 'primary'."""
    from typing import Annotated

    from lexigram.contracts.data.sql.database import DatabaseProviderProtocol
    from lexigram.di.markers import Named
    from lexigram.vector.di.provider import VectorProvider

    config = VectorConfig(backend="pgvector")  # default database="primary"
    provider = VectorProvider(config=config)
    mock_db = MagicMock(spec=DatabaseProviderProtocol)
    mock_store = MagicMock()
    mock_store.connect = AsyncMock()
    mock_container = MagicMock()

    async def fake_resolve(key: object) -> object:
        from typing import Annotated as Ann, get_args, get_origin

        if get_origin(key) is Ann:
            args = get_args(key)
            for item in args[1:]:
                if isinstance(item, Named) and item.name == "primary":
                    return mock_db
        raise ValueError(f"Unexpected resolve call: {key}")

    mock_container.resolve = fake_resolve

    # Patch the source module — PgVectorStore is lazily imported inside boot(),
    # so there is no 'provider.PgVectorStore' module-level name to patch.
    with patch(
        "lexigram.vector.backends.pgvector.PgVectorStore", return_value=mock_store
    ):
        await provider.boot(mock_container)

    mock_store.connect.assert_awaited_once()
