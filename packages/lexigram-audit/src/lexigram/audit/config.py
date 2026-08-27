"""Configuration for the Lexigram audit subsystem."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, cast

from lexigram.audit import constants as const
from lexigram.config.base import BaseConfig
from lexigram.contracts.audit import RetentionPolicy
from lexigram.contracts.core.config import Environment
from lexigram.validation import ConfigDict, Field

__all__ = ["AuditConfig"]


@dataclass(init=False)
class AuditConfig(BaseConfig):
    """Configuration for the audit subsystem.

    Attributes:
        store_backend: Backend type — ``"sql"`` or ``"memory"``.
        table_name: SQL table name for the unified audit store.
        hmac_key: HMAC key for checksum computation (bytes).
        retention_policy: Retention rules; defaults to 365 days.
        verification_schedule: Cron expression for scheduled verification.
        verification_batch_size: Entries to verify per verification run.
        enable_admin: Whether to register the AuditAdminContributor.
    """

    model_config: ClassVar[ConfigDict] = cast(
        "ConfigDict",
        {
            "env_prefix": const.ENV_PREFIX,
            "env_nested_delimiter": const.ENV_NESTED_DELIMITER,
            "extra": "ignore",
        },
    )

    config_section: ClassVar[str] = "audit"

    name: str = "audit"
    enabled: bool = True
    env: Environment | None = Field(None, description="Deployment environment")

    store_backend: str = Field(
        const.DEFAULT_STORE_BACKEND,
        description="Backend type — 'sql' or 'memory'",
    )
    table_name: str = Field(
        const.DEFAULT_TABLE_NAME,
        description="SQL table name for the unified audit store",
    )
    hmac_key: bytes | None = Field(
        None,
        description="HMAC key for checksum computation",
    )
    retention_policy: RetentionPolicy = Field(
        default_factory=lambda: RetentionPolicy(
            name="default",
            default_retention_days=365,
            severity_overrides={
                "critical": 2555,
                "high": 1095,
            },
        ),
        description="Retention rules",
    )
    verification_schedule: str = Field(
        const.DEFAULT_VERIFICATION_SCHEDULE,
        description="Cron expression for scheduled verification",
    )
    verification_batch_size: int = Field(
        const.DEFAULT_VERIFICATION_BATCH_SIZE,
        description="Entries to verify per verification run",
    )
    enable_admin: bool = Field(
        True,
        description="Whether to register the AuditAdminContributor",
    )
