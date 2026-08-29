"""Top-level cache configuration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar, cast

from lexigram.cache import constants as const
from lexigram.cache.config.backends import CacheBackendConfig
from lexigram.cache.config.service import CacheServiceConfig
from lexigram.cache.types import BackendType
from lexigram.config import BaseConfig
from lexigram.contracts.core.config import Environment
from lexigram.validation import (
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


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
    env: Environment | None = Field(default=None, description="Deployment environment")
    debug: bool = Field(const.DEFAULT_CACHE_DEBUG, description="Debug mode")

    @model_validator(mode="after")
    def validate_production_security(self) -> CacheConfig:
        """Block insecure cache configurations in production."""
        if self.environment == Environment.PRODUCTION:
            for backend in self.backends:
                if backend.type != BackendType.REDIS:
                    continue
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


def make_cache_config(**kwargs: Any) -> CacheConfig:
    """Helper to create cache config from kwargs.

    Args:
        **kwargs: Configuration keyword arguments.

    Returns:
        Created :class:`CacheConfig` instance.
    """
    return CacheConfig(**kwargs)


__all__ = [
    "CacheConfig",
    "make_cache_config",
]
