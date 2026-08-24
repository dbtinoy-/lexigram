"""Integration configurations for cache, tasks, search, resilience, storage, features, and monitoring."""

from __future__ import annotations

from dataclasses import dataclass

from lexigram.domain import DomainModel
from lexigram.validation import Field


@dataclass(init=False)
class CacheIntegrationConfig(DomainModel):
    """Configuration for the optional cache integration.

    Controls ``lexigram-cache`` usage from admin resources.
    """

    enabled: bool = Field(default=True)
    default_ttl_seconds: int = Field(default=60, ge=1)
    key_prefix: str = Field(default="admin")


@dataclass(init=False)
class TasksIntegrationConfig(DomainModel):
    """Configuration for the optional tasks integration.

    Controls ``lexigram-tasks`` usage from admin bulk actions.
    """

    enabled: bool = Field(default=True)
    bulk_threshold: int = Field(default=25, ge=1)


@dataclass(init=False)
class SearchIntegrationConfig(DomainModel):
    """Configuration for the optional search integration."""

    enabled: bool = Field(default=True)
    fallback_to_like: bool = Field(default=True)


@dataclass(init=False)
class ResilienceIntegrationConfig(DomainModel):
    """Configuration for the optional resilience integration."""

    enabled: bool = Field(default=True)
    retry_max_attempts: int = Field(default=3, ge=1)
    circuit_failure_threshold: int = Field(default=5, ge=1)


@dataclass(init=False)
class StorageIntegrationConfig(DomainModel):
    """Configuration for the optional storage integration."""

    enabled: bool = Field(default=True)
    presigned_url_expiry: int = Field(default=3600, ge=60)


@dataclass(init=False)
class FeaturesIntegrationConfig(DomainModel):
    """Configuration for the optional feature-flags integration."""

    enabled: bool = Field(default=True)


@dataclass(init=False)
class MonitorIntegrationConfig(DomainModel):
    """Configuration for the optional monitoring integration."""

    enabled: bool = Field(default=True)


@dataclass(init=False)
class AdminIntegrationsConfig(DomainModel):
    """Aggregate configuration for all optional integrations."""

    cache: CacheIntegrationConfig = Field(default_factory=CacheIntegrationConfig)
    tasks: TasksIntegrationConfig = Field(default_factory=TasksIntegrationConfig)
    search: SearchIntegrationConfig = Field(default_factory=SearchIntegrationConfig)
    resilience: ResilienceIntegrationConfig = Field(
        default_factory=ResilienceIntegrationConfig,
    )
    storage: StorageIntegrationConfig = Field(
        default_factory=StorageIntegrationConfig,
    )
    features: FeaturesIntegrationConfig = Field(
        default_factory=FeaturesIntegrationConfig,
    )
    monitor: MonitorIntegrationConfig = Field(default_factory=MonitorIntegrationConfig)
    enabled: bool = Field(default=True)

    model_config = {"extra": "forbid"}
