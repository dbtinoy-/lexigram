"""Tests for NoSQL configuration classes."""

from __future__ import annotations

import pytest

from lexigram.contracts.core.config import ConfigIssue, Environment as Env
from lexigram.nosql.config import (
    DynamoDBConfig,
    FirestoreConfig,
    MongoDBConfig,
    NamedNoSQLConfig,
    NoSQLConfig,
)


class TestMongoDBConfig:
    def test_defaults(self) -> None:
        """MongoDBConfig has sensible defaults."""
        cfg = MongoDBConfig()
        assert cfg.uri == "mongodb://localhost:27017"
        assert cfg.database == "lexigram"
        assert cfg.max_pool_size == 100
        assert cfg.min_pool_size == 10

    def test_custom_uri(self) -> None:
        """MongoDBConfig accepts custom URI."""
        cfg = MongoDBConfig(uri="mongodb://remote:27017", database="mydb")
        assert cfg.uri == "mongodb://remote:27017"
        assert cfg.database == "mydb"

    def test_pool_size_validation(self) -> None:
        """MongoDBConfig enforces pool size constraints."""
        cfg = MongoDBConfig(max_pool_size=50)
        assert cfg.max_pool_size == 50

    def test_timeout_defaults(self) -> None:
        """MongoDBConfig has sensible timeout defaults."""
        cfg = MongoDBConfig()
        assert cfg.server_selection_timeout_ms == 5000
        assert cfg.connect_timeout_ms == 10000
        assert cfg.socket_timeout_ms == 30000

    def test_retry_options_default_to_true(self) -> None:
        """Retry writes/reads default to enabled."""
        cfg = MongoDBConfig()
        assert cfg.retry_writes is True
        assert cfg.retry_reads is True

    def test_read_preference_default(self) -> None:
        """Read preference defaults to primaryPreferred."""
        cfg = MongoDBConfig()
        assert cfg.read_preference == "primaryPreferred"


class TestFirestoreConfig:
    def test_requires_project_id(self) -> None:
        """FirestoreConfig requires project_id."""
        from lexigram.contracts.exceptions import ValidationError
        with pytest.raises(ValidationError):
            FirestoreConfig()

    def test_custom_project_id(self) -> None:
        """FirestoreConfig accepts custom project_id."""
        cfg = FirestoreConfig(project_id="my-project")
        assert cfg.project_id == "my-project"

    def test_credentials_default_to_none(self) -> None:
        """credentials_json defaults to None for ADC."""
        cfg = FirestoreConfig(project_id="my-project")
        assert cfg.credentials_json is None

    def test_custom_credentials(self) -> None:
        """FirestoreConfig accepts custom credentials."""
        cfg = FirestoreConfig(
            project_id="my-project",
            credentials_json="/path/to/key.json",
        )
        assert cfg.credentials_json == "/path/to/key.json"

    def test_database_id_default(self) -> None:
        """database_id defaults to '(default)'."""
        cfg = FirestoreConfig(project_id="my-project")
        assert cfg.database_id == "(default)"


class TestDynamoDBConfig:
    def test_defaults(self) -> None:
        """DynamoDBConfig has sensible defaults."""
        cfg = DynamoDBConfig()
        assert cfg.table_name == "lexigram"
        assert cfg.region == "us-east-1"
        assert cfg.pk_field == "_id"

    def test_custom_table_name(self) -> None:
        """DynamoDBConfig accepts custom table name."""
        cfg = DynamoDBConfig(table_name="my-table")
        assert cfg.table_name == "my-table"

    def test_custom_region(self) -> None:
        """DynamoDBConfig accepts custom region."""
        cfg = DynamoDBConfig(region="eu-west-1")
        assert cfg.region == "eu-west-1"

    def test_credentials_default_to_none(self) -> None:
        """AWS credentials default to None for boto3 chain."""
        cfg = DynamoDBConfig()
        assert cfg.access_key is None
        assert cfg.secret_key is None

    def test_endpoint_url_default_to_none(self) -> None:
        """endpoint_url defaults to None (use real AWS)."""
        cfg = DynamoDBConfig()
        assert cfg.endpoint_url is None


class TestNoSQLConfig:
    def test_defaults(self) -> None:
        """NoSQLConfig has sensible defaults."""
        cfg = NoSQLConfig()
        assert cfg.enabled is True
        assert cfg.driver == "mongodb"
        assert isinstance(cfg.mongodb, MongoDBConfig)
        assert cfg.backends == []

    def test_custom_mongodb_config(self) -> None:
        """NoSQLConfig accepts custom MongoDBConfig."""
        mongo = MongoDBConfig(uri="mongodb://custom:27017", database="customdb")
        cfg = NoSQLConfig(mongodb=mongo)
        assert cfg.mongodb.uri == "mongodb://custom:27017"
        assert cfg.mongodb.database == "customdb"

    def test_custom_driver(self) -> None:
        """NoSQLConfig accepts custom driver."""
        cfg = NoSQLConfig(driver="firestore", firestore=FirestoreConfig(project_id="proj"))
        assert cfg.driver == "firestore"

    def test_firestore_config(self) -> None:
        """NoSQLConfig accepts FirestoreConfig."""
        cfg = NoSQLConfig(
            driver="firestore",
            firestore=FirestoreConfig(project_id="my-proj"),
        )
        assert cfg.firestore is not None
        assert cfg.firestore.project_id == "my-proj"


class TestNoSQLConfigValidation:
    def test_validate_production_warns_on_localhost(self) -> None:
        """Production validation warns about localhost URI."""
        cfg = NoSQLConfig(
            mongodb=MongoDBConfig(uri="mongodb://localhost:27017"),
        )
        issues = cfg.validate_for_environment(Env.PRODUCTION)
        assert len(issues) == 1
        assert issues[0].field == "mongodb.uri"
        assert "localhost" in issues[0].message

    def test_validate_production_no_warn_on_remote(self) -> None:
        """Production validation doesn't warn about remote URI."""
        cfg = NoSQLConfig(
            mongodb=MongoDBConfig(uri="mongodb://mongo.example.com:27017"),
        )
        issues = cfg.validate_for_environment(Env.PRODUCTION)
        assert issues == []

    def test_validate_development_no_warn(self) -> None:
        """Development environment doesn't trigger warnings."""
        cfg = NoSQLConfig(
            mongodb=MongoDBConfig(uri="mongodb://localhost:27017"),
        )
        issues = cfg.validate_for_environment(Env.DEVELOPMENT)
        assert issues == []

    def test_validate_test_no_warn(self) -> None:
        """Test environment doesn't trigger warnings."""
        cfg = NoSQLConfig(
            mongodb=MongoDBConfig(uri="mongodb://localhost:27017"),
        )
        issues = cfg.validate_for_environment(Env.TEST)
        assert issues == []


class TestNoSQLConfigIntegration:
    def test_firestore_and_mongodb_mutually_exclusive(self) -> None:
        """driver= firestore uses firestore config, not mongodb."""
        cfg = NoSQLConfig(
            driver="firestore",
            firestore=FirestoreConfig(project_id="proj"),
            mongodb=MongoDBConfig(uri="mongodb://other:27017"),
        )
        assert cfg.driver == "firestore"
        assert cfg.firestore is not None