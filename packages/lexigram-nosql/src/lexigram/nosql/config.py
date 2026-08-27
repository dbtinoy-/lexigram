"""NoSQL configuration following the config-system standard."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from lexigram.config.base import BaseConfig
from lexigram.contracts.core.config import ConfigIssue, Environment
from lexigram.domain import DomainModel
from lexigram.nosql.constants import ENV_NESTED_DELIMITER, ENV_PREFIX
from lexigram.validation import ConfigDict, Field


@dataclass(init=False)
class MongoDBConfig(DomainModel):
    """MongoDB-specific configuration."""

    uri: str = Field(
        default="mongodb://localhost:27017",
        description="MongoDB connection URI",
    )
    database: str = Field(default="lexigram", description="Database name")
    max_pool_size: int = Field(
        default=100,
        ge=1,
        description="Maximum connection pool size",
    )
    min_pool_size: int = Field(
        default=10,
        ge=0,
        description="Minimum connection pool size",
    )
    server_selection_timeout_ms: int = Field(
        default=5000,
        ge=1000,
        description="Server selection timeout (ms)",
    )
    connect_timeout_ms: int = Field(
        default=10000,
        ge=1000,
        description="Connection timeout (ms)",
    )
    socket_timeout_ms: int = Field(
        default=30000,
        ge=1000,
        description="Socket timeout (ms)",
    )
    retry_writes: bool = Field(default=True, description="Enable write retries")
    retry_reads: bool = Field(default=True, description="Enable read retries")
    read_preference: str = Field(
        default="primaryPreferred",
        description="Read preference mode",
    )
    write_concern_w: str | int = Field(
        default="majority",
        description="Write concern level",
    )
    auth_source: str = Field(default="admin", description="Authentication database")


@dataclass(init=False)
class FirestoreConfig(DomainModel):
    """Google Cloud Firestore configuration."""

    project_id: str = Field(
        ...,
        description="Google Cloud project ID",
    )
    credentials_json: str | None = Field(
        default=None,
        description=(
            "Path to a service account JSON key file, or the raw JSON string. "
            "When ``None``, Application Default Credentials (ADC) are used."
        ),
    )
    database_id: str = Field(
        default="(default)",
        description="Firestore database ID (use '(default)' for the default database)",
    )


@dataclass(init=False)
class DynamoDBConfig(DomainModel):
    """AWS DynamoDB configuration."""

    table_name: str = Field(
        default="lexigram",
        description="Default DynamoDB table name (used as the database_name / health-check target)",
    )
    region: str = Field(
        default="us-east-1",
        description="AWS region",
    )
    access_key: str | None = Field(
        default=None,
        description="AWS access key ID.  When None, boto3 credential chain is used.",
    )
    secret_key: str | None = Field(
        default=None,
        description="AWS secret access key.  When None, boto3 credential chain is used.",
    )
    endpoint_url: str | None = Field(
        default=None,
        description=(
            "Custom DynamoDB endpoint URL.  Set to 'http://localhost:8000' "
            "for LocalStack or DynamoDB Local."
        ),
    )
    pk_field: str = Field(
        default="_id",
        description="Partition key attribute name used by DynamoDBCollection.",
    )


@dataclass(init=False)
class NamedNoSQLConfig(DomainModel):
    """Configuration for a single named NoSQL backend.

    Used in NoSQLConfig.backends to declare multiple document stores
    that the framework registers as named DI bindings.

    Example:
        backends:
          - name: primary
            driver: mongodb
            mongodb:
              uri: mongodb://localhost:27017
              database: app
          - name: analytics
            driver: mongodb
            mongodb:
              uri: mongodb://analytics-host:27017
              database: analytics

    Args:
        name: Unique backend identifier. Used as the Named() DI key.
        primary: Whether this is the primary backend. Primary backends
            also receive the unnamed DocumentStoreProtocol binding.
        driver: NoSQL driver. One of 'mongodb' or 'firestore'.
        mongodb: MongoDB-specific connection config.
        firestore: Firestore-specific connection config.
    """

    name: str = Field(..., description="Unique backend name used as the Named() DI key")
    primary: bool = Field(
        default=False,
        description="Also register under unnamed DocumentStoreProtocol binding",
    )
    driver: str = Field(default="mongodb", description="NoSQL driver name")
    mongodb: MongoDBConfig = Field(
        default_factory=MongoDBConfig, description="MongoDB connection configuration"
    )
    firestore: FirestoreConfig | None = Field(
        default=None, description="Firestore connection configuration"
    )


@dataclass(init=False)
class NoSQLConfig(BaseConfig):
    """Top-level NoSQL configuration.

    Loaded from the ``nosql:`` key in application.yaml, with environment
    variable overrides via ``LEX_NOSQL__*`` prefix.
    """

    config_section: ClassVar[str] = "nosql"

    model_config: ClassVar[ConfigDict] = ConfigDict(  # type: ignore[typeddict-unknown-key]
        env_prefix=ENV_PREFIX,
        env_nested_delimiter=ENV_NESTED_DELIMITER,
        extra="ignore",
    )

    name: str = "nosql"
    enabled: bool = Field(default=True, description="Enable NoSQL support")
    env: Environment | None = Field(None, description="Deployment environment")
    driver: str = Field(default="mongodb", description="NoSQL driver name")
    mongodb: MongoDBConfig = Field(
        default_factory=MongoDBConfig,
        description="MongoDB configuration",
    )
    firestore: FirestoreConfig | None = Field(
        default=None,
        description="Firestore configuration (used when driver='firestore')",
    )
    backends: list[NamedNoSQLConfig] = Field(
        default_factory=list,
        description=(
            "Named NoSQL backends for multi-store support. "
            "When non-empty, the provider registers each backend under "
            "Annotated[DocumentStoreProtocol, Named(entry.name)]. "
            "The first entry (or the one with primary=True) also receives "
            "the unnamed DocumentStoreProtocol binding for backward compatibility."
        ),
    )

    def validate_for_environment(
        self,
        env: Environment | None = None,
    ) -> list[ConfigIssue]:
        """Check config is safe for the target environment."""
        resolved = env or Environment.from_env()
        issues: list[ConfigIssue] = []

        if resolved == Environment.PRODUCTION:
            if self.mongodb.uri == "mongodb://localhost:27017":
                issues.append(
                    ConfigIssue(
                        severity="warning",
                        field="mongodb.uri",
                        message="Using default localhost MongoDB URI in production",
                        suggestion=(
                            f"Set {ENV_PREFIX}MONGODB__URI to a production "
                            "MongoDB connection string."
                        ),
                    )
                )

        return issues

    @classmethod
    def from_named(
        cls, entry: NamedNoSQLConfig, base: NoSQLConfig | None = None
    ) -> NoSQLConfig:
        """Build a single-backend NoSQLConfig from a NamedNoSQLConfig entry.

        Used internally by NoSQLProvider to create per-backend configs
        from a multi-backend declaration.

        Args:
            entry: The named backend entry to materialise.
            base: Optional base config to inherit top-level settings from.

        Returns:
            A NoSQLConfig configured for the single named backend.
        """
        source = base or cls()
        return cls(
            enabled=source.enabled,
            driver=entry.driver,
            mongodb=entry.mongodb,
            firestore=entry.firestore,
            backends=[],  # prevent recursion
        )


__all__ = ["FirestoreConfig", "MongoDBConfig", "NamedNoSQLConfig", "NoSQLConfig"]
