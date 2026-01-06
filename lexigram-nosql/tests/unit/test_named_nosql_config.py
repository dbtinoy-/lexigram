"""Tests for NamedNoSQLConfig and NoSQLConfig.backends."""

from __future__ import annotations

import pytest

from lexigram.contracts.exceptions import ValidationError
from lexigram.nosql.config import MongoDBConfig, NamedNoSQLConfig, NoSQLConfig


class TestNamedNoSQLConfig:
    def test_requires_name(self) -> None:
        """NamedNoSQLConfig.name is mandatory."""
        with pytest.raises(ValidationError):
            NamedNoSQLConfig()  # type: ignore[call-arg]

    def test_defaults(self) -> None:
        """NamedNoSQLConfig defaults: driver=mongodb, primary=False."""
        cfg = NamedNoSQLConfig(name="primary")
        assert cfg.name == "primary"
        assert cfg.driver == "mongodb"
        assert cfg.primary is False
        assert isinstance(cfg.mongodb, MongoDBConfig)

    def test_primary_flag(self) -> None:
        """primary=True marks the backend as the default binding."""
        cfg = NamedNoSQLConfig(name="main", primary=True)
        assert cfg.primary is True

    def test_custom_mongodb_config(self) -> None:
        """NamedNoSQLConfig passes custom MongoDBConfig through."""
        mongo = MongoDBConfig(uri="mongodb://remote:27017", database="mydb")
        cfg = NamedNoSQLConfig(name="analytics", mongodb=mongo)
        assert cfg.mongodb.uri == "mongodb://remote:27017"
        assert cfg.mongodb.database == "mydb"


class TestNoSQLConfigBackends:
    def test_backends_defaults_to_empty(self) -> None:
        """NoSQLConfig.backends is an empty list by default."""
        cfg = NoSQLConfig()
        assert cfg.backends == []

    def test_backends_accepts_named_entries(self) -> None:
        """NoSQLConfig.backends accepts a list of NamedNoSQLConfig."""
        primary = NamedNoSQLConfig(name="primary", primary=True)
        analytics = NamedNoSQLConfig(name="analytics")
        cfg = NoSQLConfig(backends=[primary, analytics])
        assert len(cfg.backends) == 2
        assert cfg.backends[0].name == "primary"
        assert cfg.backends[1].name == "analytics"

    def test_from_named_builds_single_backend_config(self) -> None:
        """NoSQLConfig.from_named() creates a single-backend config from an entry."""
        entry = NamedNoSQLConfig(
            name="analytics",
            mongodb=MongoDBConfig(
                uri="mongodb://analytics:27017", database="analytics_db"
            ),
        )
        base = NoSQLConfig(enabled=True)
        result = NoSQLConfig.from_named(entry, base=base)
        assert result.enabled is True
        assert result.driver == "mongodb"
        assert result.mongodb.uri == "mongodb://analytics:27017"
        assert result.mongodb.database == "analytics_db"
        assert result.backends == []  # no recursion

    def test_from_named_without_base(self) -> None:
        """NoSQLConfig.from_named() works without a base config."""
        entry = NamedNoSQLConfig(name="primary")
        result = NoSQLConfig.from_named(entry)
        assert result.driver == "mongodb"
        assert result.backends == []
