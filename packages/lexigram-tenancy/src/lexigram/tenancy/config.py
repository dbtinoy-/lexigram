"""Tenancy configuration dataclasses."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar, cast

from lexigram.config import BaseConfig
from lexigram.contracts.core.config import Environment
from lexigram.tenancy.constants import (
    DEFAULT_CONFIG_CACHE_TTL,
    DEFAULT_HEADER_NAME,
    DEFAULT_JWT_CLAIM_KEY,
    DEFAULT_PATH_PATTERN,
    DEFAULT_VALIDATOR_CACHE_TTL,
    ENV_NESTED_DELIMITER,
    ENV_PREFIX,
)
from lexigram.validation import ConfigDict, Field


@dataclass
class ResolutionConfig:
    """Configuration for the tenant resolution chain.

    Attributes:
        resolvers: Ordered list of resolver names to activate.
            Available names: ``"jwt_claim"``, ``"header"``, ``"subdomain"``,
            ``"path"``.
        header_name: HTTP header name read by :class:`HeaderTenantResolver`.
        subdomain_pattern: Optional base domain for subdomain extraction
            (e.g. ``"app.com"`` → ``acme`` from ``acme.app.com``).
            ``None`` disables subdomain resolver even if listed.
        path_pattern: Path pattern for :class:`PathTenantResolver`.
            Use ``{tenant_id}`` as the placeholder.
        jwt_claim_key: JWT claim key read by :class:`JWTClaimTenantResolver`.
        validator_cache_ttl: Seconds a validated :class:`TenantInfo` is cached
            by :class:`TenantValidator`.
        trusted_resolvers: Resolver names exempt from the membership
            cross-check because their source is server-verified.
            Defaults to ``["jwt_claim"]``.
        strict_membership: Default-deny gate.  When ``True`` (default), a
            tenant resolved by a non-trusted resolver is bound only after
            the membership cross-check passes.  Setting ``False`` reproduces
            the pre-fix behavior for migration only and is **unsafe**.
    """

    resolvers: list[str] = field(
        default_factory=lambda: ["jwt_claim", "header", "subdomain", "path"]
    )
    header_name: str = DEFAULT_HEADER_NAME
    subdomain_pattern: str | None = None
    path_pattern: str | None = DEFAULT_PATH_PATTERN
    jwt_claim_key: str = DEFAULT_JWT_CLAIM_KEY
    validator_cache_ttl: int = DEFAULT_VALIDATOR_CACHE_TTL
    trusted_resolvers: list[str] = field(default_factory=lambda: ["jwt_claim"])
    strict_membership: bool = True


@dataclass
class LifecycleConfig:
    """Configuration for tenant lifecycle and provisioning.

    Attributes:
        isolation_strategy: Name of the isolation strategy to use.
            Defaults to ``"row_level"``.
        auto_provision_isolation: When ``True``, the provisioner runs the
            isolation strategy automatically on tenant creation.
    """

    isolation_strategy: str = "row_level"
    auto_provision_isolation: bool = True


@dataclass
class ConfigOverridesConfig:
    """Configuration for the per-tenant config override layer.

    Attributes:
        cache_ttl: Seconds a tenant's config dict is cached in memory.
    """

    cache_ttl: int = DEFAULT_CONFIG_CACHE_TTL


@dataclass
class IntegrationConfig:
    """Configuration for cross-package integration features.

    Attributes:
        cache_key_prefix: When ``True``, tenant-prefix cache keys via
            :class:`~lexigram.tenancy.integration.cache_decorator.TenantCacheKeyDecorator`.
        sql_context_bridge: When ``True``, sync the core ``TENANT_ID`` context
            key into lexigram-sql's DB context via
            :class:`~lexigram.tenancy.integration.sql_bridge.TenantSQLContextBridge`.
    """

    cache_key_prefix: bool = True
    sql_context_bridge: bool = True


@dataclass(init=False)
class TenancyConfig(BaseConfig):
    """Top-level tenancy configuration.

    Loaded from the ``tenancy:`` key in ``application.yaml``, with
    environment variable overrides via ``LEX_TENANCY__*`` prefix.

    Composed of four focused sub-configs.

    Attributes:
        resolution: Resolver chain configuration.
        lifecycle: Lifecycle and isolation strategy configuration.
        overrides: Per-tenant config override layer configuration.
        integration: Cross-package integration feature toggles.
    """

    config_section: ClassVar[str] = "tenancy"

    name: str = "tenancy"
    enabled: bool = True
    env: Environment | None = Field(None, description="Deployment environment")

    model_config: ClassVar[ConfigDict] = cast(
        "ConfigDict",
        {
            "env_prefix": ENV_PREFIX,
            "env_nested_delimiter": ENV_NESTED_DELIMITER,
            "extra": "ignore",
        },
    )

    resolution: ResolutionConfig = Field(default_factory=ResolutionConfig)
    lifecycle: LifecycleConfig = Field(default_factory=LifecycleConfig)
    overrides: ConfigOverridesConfig = Field(default_factory=ConfigOverridesConfig)
    integration: IntegrationConfig = Field(default_factory=IntegrationConfig)


__all__ = [
    "ConfigOverridesConfig",
    "IntegrationConfig",
    "LifecycleConfig",
    "ResolutionConfig",
    "TenancyConfig",
]
