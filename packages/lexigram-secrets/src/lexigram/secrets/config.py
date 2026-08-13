"""Configuration models for the secrets rotation subsystem."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, cast

from lexigram.config import BaseConfig
from lexigram.contracts.core.config import Environment
from lexigram.secrets import constants as const
from lexigram.validation import ConfigDict, Field, model_validator

__all__ = ["SecretsConfig"]


@dataclass(init=False)
class SecretsConfig(BaseConfig):
    """Top-level configuration for the secrets rotation subsystem.

    Attributes:
        name: Configuration name.
        enabled: Whether the secrets subsystem is enabled.
        backend_type: Backend store type (``"memory"`` or ``"vault"``).
        backend_options: Keyword arguments forwarded to the backend constructor.
        max_age_seconds: Maximum age before automatic rotation.
        warning_before_seconds: Seconds before expiry to emit rotation warnings.
        tenant_id: Optional tenant namespace for multi-tenancy.
        audit_actor_id: Actor identifier for audit log entries.
    """

    model_config = cast(
        "ConfigDict",
        {
            "env_prefix": const.ENV_PREFIX,
            "env_nested_delimiter": const.ENV_NESTED_DELIMITER,
            "extra": "ignore",
        },
    )

    config_section: ClassVar[str] = "secrets"

    name: str = Field("secrets", description="Configuration name")
    enabled: bool = Field(True, description="Whether secrets subsystem is enabled")
    backend_type: str = Field(
        const.DEFAULT_BACKEND_TYPE,
        description="Backend store type (memory, vault, ...)",
    )
    backend_options: dict = Field(
        default_factory=dict,
        description="Keyword arguments for backend constructor",
    )
    max_age_seconds: float = Field(
        const.DEFAULT_MAX_AGE_SECONDS,
        description="Seconds before automatic rotation",
    )
    warning_before_seconds: float = Field(
        const.DEFAULT_WARNING_BEFORE_SECONDS,
        description="Seconds before expiry to warn",
    )
    tenant_id: str | None = Field(None, description="Optional tenant namespace")
    audit_actor_id: str = Field(
        const.DEFAULT_AUDIT_ACTOR_ID,
        description="Actor identifier for audit log entries",
    )

    @property
    def is_production(self) -> bool:
        """Whether the active environment is production."""
        return self.environment == Environment.PRODUCTION

    @property
    def is_development(self) -> bool:
        """Whether the active environment is development."""
        return self.environment == Environment.DEVELOPMENT

    @property
    def is_test(self) -> bool:
        """Whether the active environment is test."""
        return self.environment == Environment.TEST

    @model_validator(mode="after")
    def validate_backend_environment(self) -> SecretsConfig:
        """Reject the in-memory backend in production-like environments.

        The in-memory store is plaintext and process-local; it must not
        silently become the default in production or staging.

        Raises:
            ValueError: If ``backend_type`` is ``"memory"`` while the
                environment is production or staging.
        """
        if self.backend_type == "memory" and self.environment in (
            Environment.PRODUCTION,
            Environment.STAGING,
        ):
            raise ValueError(
                "SecretsConfig: backend_type='memory' (in-memory plaintext "
                "store) is not permitted in "
                f"{self.environment.value}; set LEX_SECRETS__BACKEND_TYPE to "
                "a persistent backend (vault, aws, gcp, azure) before "
                "deploying to production/staging."
            )
        return self
