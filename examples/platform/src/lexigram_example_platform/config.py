"""Platform application configuration.

All fields can be overridden via environment variables.  The
:class:`~lexigram.config.base.BaseConfig` base class resolves values from
YAML files and ``LEX_*`` / ``PLATFORM_*`` environment variables.
"""

from __future__ import annotations

from dataclasses import dataclass

from lexigram.config import BaseConfig
from lexigram.validation import Field


@dataclass(init=False)
class PlatformConfig(BaseConfig):
    """Top-level configuration for the multi-tenant SaaS platform.

    Attributes:
        db_url: Async SQLAlchemy database URL.
        redis_url: Redis connection URL (used for cache and feature-flag storage).
        event_driver: Event bus backend (``memory``, ``kafka``, ``rabbitmq``).
        feature_flags_enabled: Whether the feature-flag subsystem is active.
        max_tenants_per_instance: Soft cap on tenants (advisory; not enforced
            by the domain layer).
        default_member_role: Role assigned to new invitations when no role is
            explicitly specified.
    """

    db_url: str = Field(
        default="sqlite+aiosqlite:///./platform.db",
        description="Async SQLAlchemy database URL.",
    )
    redis_url: str = Field(
        default="redis://localhost:26379/0",
        description="Redis connection URL.",
    )
    event_driver: str = Field(
        default="memory",
        description="Event bus backend driver (memory | kafka | rabbitmq).",
    )
    feature_flags_enabled: bool = Field(
        default=True,
        description="Enable the feature-flag subsystem.",
    )
    max_tenants_per_instance: int = Field(
        default=1000,
        description="Soft cap on tenants (advisory).",
    )
    default_member_role: str = Field(
        default="member",
        description="Default role assigned to invited users.",
    )


__all__ = ["PlatformConfig"]
