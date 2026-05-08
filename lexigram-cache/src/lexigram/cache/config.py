"""Consolidated cache configuration.

Replaces the former ``config/`` sub-package by merging all four modules
(``operation``, ``backends``, ``service``, ``loaders``) into a single flat
file so that ``from lexigram.cache.config import X`` continues to work
unchanged for all existing callers.

Public API
----------
- :class:`CacheOperationConfig`
- :class:`MemoryBackendConfig`
- :class:`RedisBackendConfig`
- :class:`MemcachedBackendConfig`
- :class:`CacheBackendConfig`
- :class:`CacheServiceConfig`
- :class:`CacheConfig`
- :data:`BACKEND_TYPE_MAP`
- :func:`default_cache_config`
- :func:`get_backend_type_from_string`
- :func:`make_cache_config`
- :func:`make_cache_service_config`
- :class:`EnvironmentConfigLoader`
"""

from __future__ import annotations

from dataclasses import dataclass
import os
import re
from typing import Any, ClassVar, cast

from lexigram.cache import constants as const
from lexigram.cache.types import BackendType
from lexigram.config import BaseConfig
from lexigram.domain import DomainModel
from lexigram.serialization import loads as json_loads
from lexigram.validation import (
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

# ---------------------------------------------------------------------------
# Operation configuration
# ---------------------------------------------------------------------------


@dataclass(init=False)
class CacheOperationConfig(DomainModel):
    """Internal configuration for cache operations. Shared across backends.

    Attributes:
        default_ttl: Default time-to-live in seconds.
        max_memory: Maximum memory usage in bytes.
        key_prefix: Prefix for all cache keys.
        enable_metrics: Whether to enable metrics collection.
        serializer_type: Type of serializer to use (json, pickle, msgpack).
    """

    default_ttl: int | None = Field(None, description="Default TTL in seconds")
    max_memory: int | None = Field(None, description="Maximum memory in bytes")
    key_prefix: str = Field("", description="Prefix for all cache keys")
    enable_metrics: bool = Field(True, description="Enable metrics collection")
    serializer_type: str = Field(
        const.DEFAULT_SERVICE_SERIALIZER,
        description="AsyncStringSerializerProtocol type",
    )

    def make_key(self, key: str) -> str:
        """Create a prefixed cache key.

        Args:
            key: The raw cache key.

        Returns:
            Key with the configured prefix applied, or the original key if no
            prefix is set.
        """
        if self.key_prefix:
            return f"{self.key_prefix}:{key}"
        return key

    def strip_prefix(self, prefixed_key: str) -> str:
        """Remove prefix from a cache key.

        Args:
            prefixed_key: A key that may carry the configured prefix.

        Returns:
            The key with the prefix removed, or the original key unchanged.
        """
        if self.key_prefix and prefixed_key.startswith(f"{self.key_prefix}:"):
            return prefixed_key[len(self.key_prefix) + 1 :]
        return prefixed_key


# ---------------------------------------------------------------------------
# Per-backend configuration models
# ---------------------------------------------------------------------------


@dataclass(init=False)
class MemoryBackendConfig(DomainModel):
    """Configuration for in-memory cache backend.

    Attributes:
        name: Backend name.
        default: Whether this is the default backend.
        enabled: Whether this backend is enabled.
        default_ttl: Default TTL in seconds.
        max_size: Maximum number of entries.
        cleanup_interval: Cleanup interval in seconds.
        key_prefix: Key prefix for namespace isolation.
    """

    name: str = Field(const.DEFAULT_MEMORY_NAME, description="Backend name")
    default: bool = Field(
        const.DEFAULT_MEMORY_DEFAULT, description="Is default backend"
    )
    enabled: bool = Field(const.DEFAULT_MEMORY_ENABLED, description="Is enabled")
    default_ttl: int | None = Field(None, description="Default TTL")
    max_size: int | None = Field(None, description="Max entries")
    cleanup_interval: int = Field(
        const.DEFAULT_MEMORY_CLEANUP_INTERVAL,
        description="Cleanup interval seconds",
    )
    key_prefix: str = Field("", description="Key prefix")

    @property
    def backend_type(self) -> BackendType:
        """Get the backend type."""
        return BackendType.MEMORY


@dataclass(init=False)
class RedisBackendConfig(DomainModel):
    """Configuration for Redis cache backend.

    Attributes:
        name: Backend name.
        default: Whether this is the default backend.
        enabled: Whether this backend is enabled.
        host: Redis host.
        port: Redis port.
        db: Redis database number.
        password: Redis password (optional).
        url: Full Redis URL (overrides host/port/db).
        default_ttl: Default TTL in seconds.
        key_prefix: Key prefix for namespace isolation.
        ssl: Whether to use SSL/TLS.
        connection_pool_size: Connection pool size.
        socket_timeout: Socket timeout in seconds.
        retry_on_timeout: Whether to retry on timeout.
    """

    name: str = Field(const.DEFAULT_REDIS_NAME, description="Backend name")
    default: bool = Field(const.DEFAULT_REDIS_DEFAULT, description="Is default backend")
    enabled: bool = Field(const.DEFAULT_REDIS_ENABLED, description="Is enabled")
    host: str = Field(const.DEFAULT_REDIS_HOST, description="Redis host")
    port: int = Field(const.DEFAULT_REDIS_PORT, description="Redis port")
    db: int = Field(const.DEFAULT_REDIS_DB, description="Redis database")
    password: str | None = Field(None, description="Redis password")
    url: str | None = Field(None, description="Redis URL")
    default_ttl: int | None = Field(None, description="Default TTL")
    key_prefix: str = Field("", description="Key prefix")
    ssl: bool = Field(const.DEFAULT_REDIS_SSL, description="Use SSL/TLS")
    connection_pool_size: int = Field(
        const.DEFAULT_REDIS_CONNECTION_POOL_SIZE,
        description="Connection pool size",
    )
    socket_timeout: float = Field(
        const.DEFAULT_REDIS_SOCKET_TIMEOUT,
        description="Socket timeout seconds",
    )
    retry_on_timeout: bool = Field(
        const.DEFAULT_REDIS_RETRY_ON_TIMEOUT,
        description="Retry on timeout",
    )

    @property
    def backend_type(self) -> BackendType:
        """Get the backend type."""
        return BackendType.REDIS

    @property
    def redis_url(self) -> str:
        """Get the full Redis URL."""
        if self.url:
            return self.url

        url = "rediss://" if self.ssl else "redis://"
        if self.password:
            url += f":{self.password}@"
        url += f"{self.host}:{self.port}/{self.db}"
        return url


@dataclass(init=False)
class MemcachedBackendConfig(DomainModel):
    """Configuration for Memcached cache backend.

    Attributes:
        name: Backend name.
        default: Whether this is the default backend.
        enabled: Whether this backend is enabled.
        host: Memcached host.
        port: Memcached port.
        servers: List of server addresses (host:port).
        default_ttl: Default TTL in seconds.
        key_prefix: Key prefix for namespace isolation.
        connect_timeout: Connection timeout in seconds.
        timeout: Operation timeout in seconds.
        max_pool_size: Maximum connection pool size.
    """

    name: str = Field(const.DEFAULT_MEMCACHED_NAME, description="Backend name")
    default: bool = Field(
        const.DEFAULT_MEMCACHED_DEFAULT, description="Is default backend"
    )
    enabled: bool = Field(const.DEFAULT_MEMCACHED_ENABLED, description="Is enabled")
    host: str = Field(const.DEFAULT_MEMCACHED_HOST, description="Memcached host")
    port: int = Field(const.DEFAULT_MEMCACHED_PORT, description="Memcached port")
    servers: list[str] | None = Field(None, description="Server list")
    default_ttl: int | None = Field(None, description="Default TTL")
    key_prefix: str = Field("", description="Key prefix")
    connect_timeout: float = Field(
        const.DEFAULT_REDIS_SOCKET_TIMEOUT,
        description="Connect timeout",
    )
    timeout: float = Field(
        const.DEFAULT_REDIS_SOCKET_TIMEOUT,
        description="Operation timeout",
    )
    max_pool_size: int = Field(
        const.DEFAULT_REDIS_CONNECTION_POOL_SIZE,
        description="Max pool size",
    )

    @property
    def backend_type(self) -> BackendType:
        """Get the backend type."""
        return BackendType.MEMCACHED

    @property
    def server_list(self) -> list[str]:
        """Get the server list."""
        if self.servers:
            return self.servers
        return [f"{self.host}:{self.port}"]


@dataclass(init=False)
class CacheBackendConfig(DomainModel):
    """Unified (flattened-union) configuration for any single cache backend.

    This class uses the **flattened-union pattern**: all backend-specific
    fields live in one dataclass and are partitioned by the ``type`` field.
    Fields that do not belong to the active backend type are silently
    ignored by the respective backend implementation.

    When to use
    -----------
    Prefer this class when loading backend configuration from environment
    variables or a flat config file (e.g. TOML/YAML with no nested sections),
    where per-backend types cannot be selected at parse time.

    For strongly-typed, up-front configuration prefer the dedicated classes:
    :class:`MemoryBackendConfig`, :class:`RedisBackendConfig`, or
    :class:`MemcachedBackendConfig`.

    Field partitioning
    ------------------
    +-------------------------+----------+----------+-----------+
    | Field                   | memory   | redis    | memcached |
    +=========================+==========+==========+===========+
    | name, type, default,    | ✓        | ✓        | ✓         |
    | enabled, default_ttl,   |          |          |           |
    | key_prefix,             |          |          |           |
    | enable_metrics,         |          |          |           |
    | health_check_interval   |          |          |           |
    +-------------------------+----------+----------+-----------+
    | max_size,               | ✓        |          |           |
    | cleanup_interval        |          |          |           |
    +-------------------------+----------+----------+-----------+
    | redis_host/port/db/     |          | ✓        |           |
    | password/url/ssl/       |          |          |           |
    | pool_size               |          |          |           |
    +-------------------------+----------+----------+-----------+
    | memcached_host/port/    |          |          | ✓         |
    | servers                 |          |          |           |
    +-------------------------+----------+----------+-----------+

    Attributes:
        name: Unique name for this backend.
        type: Backend type (memory, redis, memcached).
        default: Whether this is the default backend.
        enabled: Whether this backend is enabled.
        default_ttl: Default TTL in seconds.
        key_prefix: Key prefix for namespace isolation.
        enable_metrics: Enable metrics collection.
        health_check_interval: Health check interval in seconds.
    """

    # Common configuration
    name: str = Field(..., description="Unique backend name")
    type: BackendType = Field(..., description="Backend type")
    default: bool = Field(
        const.DEFAULT_MEMORY_DEFAULT, description="Is default backend"
    )
    enabled: bool = Field(const.DEFAULT_MEMORY_ENABLED, description="Is enabled")
    default_ttl: int | None = Field(None, description="Default TTL")
    key_prefix: str = Field("", description="Key prefix")
    enable_metrics: bool = Field(True, description="Enable metrics")
    health_check_interval: int = Field(
        const.DEFAULT_PROTECTION_LOCK_TTL,
        description="Health check interval",
    )

    # Memory-specific
    max_size: int | None = Field(None, description="Max entries (memory)")
    cleanup_interval: int = Field(
        const.DEFAULT_MEMORY_CLEANUP_INTERVAL,
        description="Cleanup interval (memory)",
    )

    # Redis-specific
    redis_host: str = Field(const.DEFAULT_REDIS_HOST, description="Redis host")
    redis_port: int = Field(const.DEFAULT_REDIS_PORT, description="Redis port")
    redis_db: int = Field(const.DEFAULT_REDIS_DB, description="Redis database")
    redis_password: str | None = Field(None, description="Redis password")
    redis_url: str | None = Field(None, description="Redis URL")
    redis_ssl: bool = Field(const.DEFAULT_REDIS_SSL, description="Redis SSL")
    redis_pool_size: int = Field(
        const.DEFAULT_REDIS_CONNECTION_POOL_SIZE,
        description="Redis pool size",
    )

    # Memcached-specific
    memcached_host: str = Field(
        const.DEFAULT_MEMCACHED_HOST, description="Memcached host"
    )
    memcached_port: int = Field(
        const.DEFAULT_MEMCACHED_PORT, description="Memcached port"
    )
    memcached_servers: list[str] | None = Field(None, description="Memcached servers")

    @model_validator(mode="after")
    def build_redis_url(self) -> CacheBackendConfig:
        """Build Redis URL from components if not provided."""
        if self.type == BackendType.REDIS and not self.redis_url:
            url = "rediss://" if self.redis_ssl else "redis://"
            if self.redis_password:
                url += f":{self.redis_password}@"
            url += f"{self.redis_host}:{self.redis_port}/{self.redis_db}"
            self.redis_url = url
        return self

    @model_validator(mode="after")
    def build_memcached_servers(self) -> CacheBackendConfig:
        """Build Memcached server list if not provided."""
        if self.type == BackendType.MEMCACHED and not self.memcached_servers:
            self.memcached_servers = [f"{self.memcached_host}:{self.memcached_port}"]
        return self


# ---------------------------------------------------------------------------
# Service-level configuration
# ---------------------------------------------------------------------------


@dataclass(init=False)
class CacheServiceConfig(DomainModel):
    """Configuration for the cache service layer.

    Controls service-level behavior and features like stampede
    protection, metrics, and circuit breaker.

    Attributes:
        enable_protection: Enable cache stampede protection.
        enable_metrics: Enable service-level metrics.
        enable_health_checks: Enable health checks.
        protection_lock_ttl: Lock TTL for stampede protection.
        protection_max_wait: Max wait time for locks.
        protection_retry_interval: Retry interval for locks.
        default_backend: Name of the default backend.
        circuit_breaker_enabled: Enable circuit breaker pattern.
        circuit_breaker_threshold: Failure threshold for circuit breaker.
        default_serializer: Default serializer type.
    """

    enable_protection: bool = Field(
        const.DEFAULT_SERVICE_PROTECTION_ENABLED,
        description="Enable stampede protection",
    )
    enable_metrics: bool = Field(
        const.DEFAULT_SERVICE_METRICS_ENABLED,
        description="Enable metrics",
    )
    enable_health_checks: bool = Field(
        const.DEFAULT_SERVICE_HEALTH_CHECKS_ENABLED,
        description="Enable health checks",
    )
    protection_lock_ttl: int = Field(
        const.DEFAULT_PROTECTION_LOCK_TTL,
        description="Protection lock TTL",
    )
    protection_max_wait: float = Field(
        const.DEFAULT_PROTECTION_MAX_WAIT,
        description="Max wait for locks",
    )
    protection_retry_interval: float = Field(
        const.DEFAULT_PROTECTION_RETRY_INTERVAL,
        description="Lock retry interval",
    )
    default_backend: str | None = Field(None, description="Default backend name")
    circuit_breaker_enabled: bool = Field(
        const.DEFAULT_SERVICE_CIRCUIT_BREAKER_ENABLED,
        description="Enable circuit breaker",
    )
    circuit_breaker_threshold: int = Field(
        const.DEFAULT_SERVICE_CIRCUIT_BREAKER_THRESHOLD,
        description="Circuit breaker threshold",
    )
    default_serializer: str = Field(
        const.DEFAULT_SERVICE_SERIALIZER,
        description="Default serializer",
    )


# ---------------------------------------------------------------------------
# Top-level configuration
# ---------------------------------------------------------------------------


@dataclass(init=False)
class CacheConfig(BaseConfig):
    """Top-level configuration for Lexigram Cache.

    Attributes:
        name: Configuration name (default: "cache")
        version: Config version
        enabled: Whether cache is enabled
        backends: List of cache backend configurations
        service: Cache service settings
        environment: Environment name
        debug: Debug mode
    """

    model_config = cast(
        "ConfigDict",
        {
            "env_prefix": const.ENV_PREFIX,
            "env_nested_delimiter": const.ENV_NESTED_DELIMITER,
            "extra": "ignore",
        },
    )

    config_section: ClassVar[str] = "cache"

    name: str = Field(const.DEFAULT_CACHE_NAME, description="Provider name")
    version: str = Field(const.DEFAULT_CACHE_VERSION, description="Config version")
    enabled: bool = Field(
        const.DEFAULT_CACHE_ENABLED, description="Whether cache is enabled"
    )
    backends: list[CacheBackendConfig] = Field(
        default_factory=list,
        description="Backend configs",
    )
    service: CacheServiceConfig = Field(
        default_factory=CacheServiceConfig,
        description="Service config",
    )
    environment: str = Field(const.DEFAULT_CACHE_ENVIRONMENT, description="Environment")  # type: ignore[assignment]
    env: str | None = Field(
        None, description="Environment (development/staging/production)"
    )
    debug: bool = Field(const.DEFAULT_CACHE_DEBUG, description="Debug mode")

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return (self.env or self.environment) == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        env_val = self.env or self.environment
        return env_val in ("development", "dev")

    @property
    def is_test(self) -> bool:
        """Check if running in test environment."""
        env_val = self.env or self.environment
        return env_val in ("test", "testing")

    @model_validator(mode="after")
    def validate_production_security(self) -> CacheConfig:
        """Block insecure cache configurations in production."""
        env = os.getenv(const.ENV_VAR_LEX_ENV, const.DEFAULT_CACHE_ENVIRONMENT).lower()
        if env == "production":
            for backend in self.backends:
                if backend.type == BackendType.REDIS:
                    if (
                        backend.redis_password
                        and backend.redis_password.lower() in const.INSECURE_PASSWORDS
                    ):
                        raise ValueError(
                            const.ERROR_MSG_INSECURE_PASSWORD.format(
                                backend="Redis",
                                name=backend.name,
                                env_var=f"{const.ENV_PREFIX}BACKENDS__<idx>__REDIS_PASSWORD",
                            ),
                        )
                    if backend.redis_url and any(
                        f":{d}@" in backend.redis_url.lower()
                        for d in const.INSECURE_PASSWORDS
                    ):
                        raise ValueError(
                            const.ERROR_MSG_INSECURE_URL.format(
                                backend="Redis",
                                name=backend.name,
                                env_var=f"{const.ENV_PREFIX}BACKENDS__<idx>__REDIS_URL",
                            ),
                        )
        return self

    @field_validator("backends")
    @classmethod
    def validate_default_backend(
        cls,
        v: list[CacheBackendConfig],
    ) -> list[CacheBackendConfig]:
        """Ensure exactly one default backend is specified."""
        if not v:
            return v
        default_count = sum(
            1
            for backend in v
            if (
                backend.get("default", False)
                if isinstance(backend, dict)
                else backend.default
            )
        )
        if default_count != 1:
            raise ValueError("Exactly one backend must be marked as default")
        return v

    @field_validator("backends")
    @classmethod
    def validate_unique_names(
        cls,
        v: list[CacheBackendConfig],
    ) -> list[CacheBackendConfig]:
        """Ensure backend names are unique."""
        names = [
            (backend.get("name") if isinstance(backend, dict) else backend.name)
            for backend in v
        ]
        if len(names) != len(set(names)):
            raise ValueError("Backend names must be unique")
        return v

    def get_default_backend(self) -> CacheBackendConfig | None:
        """Get the default backend configuration.

        Returns:
            The first backend marked as default, or ``None`` if none exists.
        """
        for backend in self.backends:
            if backend.default:
                return backend
        return None

    def get_backend(self, name: str) -> CacheBackendConfig | None:
        """Get a backend configuration by name.

        Args:
            name: The backend name to look up.

        Returns:
            Matching :class:`CacheBackendConfig`, or ``None`` if not found.
        """
        for backend in self.backends:
            if backend.name == name:
                return backend
        return None

    @classmethod
    def get_provider_class(cls) -> type:
        """Return the provider class for this config.

        Returns:
            The :class:`~lexigram.cache.CacheProvider` class.
        """
        from lexigram.cache import CacheProvider

        return CacheProvider


# ---------------------------------------------------------------------------
# Backend type registry and helpers
# ---------------------------------------------------------------------------

BACKEND_TYPE_MAP: dict[str, BackendType] = {
    "memory": BackendType.MEMORY,
    "redis": BackendType.REDIS,
    "memcached": BackendType.MEMCACHED,
}


def get_backend_type_from_string(type_str: str) -> BackendType:
    """Convert string to BackendType using registry lookup.

    Args:
        type_str: Backend type string (e.g., "memory", "redis").

    Returns:
        BackendType enum value, defaults to MEMORY if unknown.
    """
    return BACKEND_TYPE_MAP.get(type_str.lower(), BackendType.MEMORY)


def default_cache_config() -> CacheOperationConfig:
    """Factory for default cache operation configuration.

    Returns:
        Default :class:`CacheOperationConfig` instance.
    """
    return CacheOperationConfig(
        default_ttl=None,
        max_memory=None,
        key_prefix="",
        enable_metrics=True,
        serializer_type="json",
    )


def resolve_backend_type(config: CacheBackendConfig) -> BackendType:
    """Return the backend type from a backend configuration.

    The flattened :class:`CacheBackendConfig` stores the type in the
    ``type`` field while the strongly-typed classes
    (:class:`MemoryBackendConfig`, :class:`RedisBackendConfig`,
    :class:`MemcachedBackendConfig`) expose it via the ``backend_type``
    property. This helper normalizes both shapes.

    Args:
        config: Backend configuration, either shape.

    Returns:
        The resolved :class:`BackendType`.
    """
    backend_type = getattr(config, "backend_type", None)
    if backend_type is not None:
        return cast("BackendType", backend_type)
    return config.type


def make_cache_config(**kwargs: Any) -> CacheConfig:
    """Helper to create cache config from kwargs.

    Args:
        **kwargs: Configuration keyword arguments.

    Returns:
        Created :class:`CacheConfig` instance.
    """
    return CacheConfig(**kwargs)


def make_cache_service_config(**kwargs: Any) -> CacheServiceConfig:
    """Helper to create service config from kwargs.

    Args:
        **kwargs: Service configuration keyword arguments.

    Returns:
        Created :class:`CacheServiceConfig` instance.
    """
    return CacheServiceConfig(**kwargs)


# ---------------------------------------------------------------------------
# Environment / file config loaders
# ---------------------------------------------------------------------------


class EnvironmentConfigLoader:
    """Loader for cache configuration from various sources."""

    @staticmethod
    def from_env(prefix: str = const.ENV_PREFIX) -> CacheConfig:
        """Load CacheConfig from environment variables.

        Args:
            prefix: Environment variable prefix.

        Returns:
            Populated :class:`CacheConfig` instance.
        """
        upper_prefix = prefix.upper()
        flat: dict[str, Any] = {}
        for key, value in os.environ.items():
            if not key.startswith(upper_prefix):
                continue
            config_key = key[len(upper_prefix) :].lower()
            try:
                parsed: Any = int(value)
            except ValueError:
                try:
                    parsed = float(value)
                except ValueError:
                    parsed = value
            flat[config_key] = parsed
        result: dict[str, Any] = {}
        indexed: dict[str, dict[int, dict[str, Any]]] = {}
        for key, value in flat.items():
            m = re.match(r"^(.+?)_(\d+)_(.+)$", key)
            if m:
                base, idx_str, suffix = m.group(1), m.group(2), m.group(3)
                list_key = f"{base}s"
                indexed.setdefault(list_key, {}).setdefault(int(idx_str), {})[
                    suffix
                ] = value
            else:
                result[key] = value
        for list_key, by_index in indexed.items():
            max_idx = max(by_index.keys())
            result[list_key] = [by_index.get(i, {}) for i in range(max_idx + 1)]
        return CacheConfig(**result)

    @staticmethod
    def from_dict(config_dict: dict[str, Any]) -> CacheConfig:
        """Load CacheConfig from a dictionary.

        Args:
            config_dict: Configuration dictionary.

        Returns:
            Populated :class:`CacheConfig` instance.
        """
        return CacheConfig(**config_dict)

    @staticmethod
    def from_yaml(file_path: str) -> CacheConfig:
        """Load CacheConfig from a YAML file.

        Args:
            file_path: Path to the YAML configuration file.

        Returns:
            Populated :class:`CacheConfig` instance.
        """
        try:
            import yaml
        except ImportError as e:
            raise ImportError(const.ERROR_MSG_PYYAML_INSTALL) from e
        with open(file_path, encoding=const.DEFAULT_ENCODING) as f:
            config_dict = yaml.safe_load(f)
        return CacheConfig(**config_dict)

    @staticmethod
    def from_json(file_path: str) -> CacheConfig:
        """Load CacheConfig from a JSON file.

        Args:
            file_path: Path to the JSON configuration file.

        Returns:
            Populated :class:`CacheConfig` instance.
        """
        with open(file_path, encoding=const.DEFAULT_ENCODING) as f:
            content = f.read()
        config_dict = json_loads(content)
        return CacheConfig(**config_dict)


# ---------------------------------------------------------------------------
# __all__
# ---------------------------------------------------------------------------

__all__ = [
    "BACKEND_TYPE_MAP",
    "CacheBackendConfig",
    "CacheConfig",
    "CacheOperationConfig",
    "CacheServiceConfig",
    "EnvironmentConfigLoader",
    "MemcachedBackendConfig",
    "MemoryBackendConfig",
    "RedisBackendConfig",
    "default_cache_config",
    "get_backend_type_from_string",
    "make_cache_config",
    "make_cache_service_config",
    "resolve_backend_type",
]
