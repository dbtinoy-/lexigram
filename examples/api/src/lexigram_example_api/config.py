"""Application configuration via Pydantic Settings.

All settings can be overridden via environment variables prefixed with
``APP_``.  For example, ``APP_JWT_SECRET=my-secret`` sets ``jwt_secret``.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings


class AppConfig(BaseSettings):
    """Top-level application configuration.

    Attributes:
        database_url: Async PostgreSQL connection string (SQLAlchemy format).
        redis_url: Redis connection URL used by the cache provider.
        jwt_secret: HMAC secret used to sign/verify JWTs.  Change in production.
        jwt_algorithm: JWT signing algorithm.  Defaults to HS256.
        jwt_expiry_seconds: Lifetime of access tokens in seconds.
        debug: Enable debug logging and development-only routes.
        host: HTTP server bind address.
        port: HTTP server listen port.
        app_name: Human-readable application name emitted in log records.
    """

    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:25432/example_api",
        description="Async PostgreSQL connection URL",
    )
    redis_url: str = Field(
        default="redis://localhost:26379",
        description="Redis connection URL for cache backend",
    )
    jwt_secret: str = Field(
        default="dev-secret-change-in-production-at-least-32-chars",
        description="HMAC secret for JWT signing — must be changed in production",
    )
    jwt_algorithm: str = Field(
        default="HS256",
        description="JWT signing algorithm",
    )
    jwt_expiry_seconds: int = Field(
        default=3600,
        description="JWT access-token lifetime in seconds",
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode",
    )
    host: str = Field(
        default="0.0.0.0",
        description="HTTP server bind address",
    )
    port: int = Field(
        default=8000,
        description="HTTP server listen port",
    )
    app_name: str = Field(
        default="lexigram-example-api",
        description="Application name used in log records",
    )

    model_config = {"env_prefix": "APP_", "env_file": ".env", "extra": "ignore"}
