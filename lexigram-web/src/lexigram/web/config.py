"""Configuration models for Lexigram Web/HTTP.

This module provides comprehensive configuration models for web server,
security headers, CORS, and rate limiting.

Example:
    from lexigram.web.config import WebConfig

    # From YAML
    config = WebConfig.from_yaml("application.yaml")

    # From environment
    config = WebConfig()  # reads LEX_WEB__* env vars
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any, ClassVar, cast

from lexigram.config import BaseConfig
from lexigram.validation import (
    ConfigDict,
    Field,
    SecretStr,
    model_validator,
)
from lexigram.web import constants as const
from lexigram.web.security.config import (
    CORSConfig,
    CrossOriginConfig,
    CSPConfig,
    CSRFConfig,
    HSTSConfig,
    SecurityConfig,
)


def __getattr__(name: str) -> Any:
    if name == "VersioningStrategy":
        from lexigram.web.routing.versioning import VersioningStrategy

        return VersioningStrategy
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


@dataclass(init=False)
class ServerConfig(BaseConfig):
    """Server configuration."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    host: str = Field(default=const.DEFAULT_HOST, description="Bind host")
    port: int = Field(default=const.DEFAULT_PORT, description="Bind port")
    workers: int = Field(default=const.DEFAULT_WORKERS, description="Number of workers")
    reload: bool = Field(default=const.DEFAULT_RELOAD, description="Enable auto-reload")
    debug: bool = Field(default=False, description="Enable debug mode")

    @model_validator(mode="after")
    def validate_server(self) -> ServerConfig:
        """Validate server host and port."""
        if not (1 <= self.port <= 65535):
            raise ValueError(f"Invalid port: {self.port}. Must be between 1 and 65535.")
        if not self.host:
            raise ValueError("Server host cannot be empty.")
        return self


# =============================================================================
# API Documentation Configuration
# =============================================================================


@dataclass(init=False)
class APIDocsConfig(BaseConfig):
    """API documentation configuration.

    Automatically configures CSP directives for API documentation endpoints
    (/docs for Swagger UI, /redoc for ReDoc) when enabled.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    enabled: bool = Field(
        default=True,
        description=(
            "Enable API documentation endpoints (/docs, /redoc) and auto-configure "
            "CSP for their CDN assets"
        ),
    )
    provider: str = Field(
        default="both",
        description="Documentation provider: 'swagger', 'redoc', or 'both'",
    )

    # Domains needed for API docs
    SWAGGER_DOMAINS: ClassVar[dict[str, set[str]]] = {
        "script-src": {"https://unpkg.com"},
        "script-src-elem": {"https://unpkg.com"},  # For <script src> elements
        "style-src": {"https://unpkg.com"},
        "style-src-elem": {"https://unpkg.com"},  # For <link rel=stylesheet> elements
    }

    REDOC_DOMAINS: ClassVar[dict[str, set[str]]] = {
        "script-src": {"https://cdn.redoc.ly"},
        "script-src-elem": {"https://cdn.redoc.ly"},  # For <script src> elements
        "style-src": {"https://fonts.googleapis.com"},
        "style-src-elem": {
            "https://fonts.googleapis.com"
        },  # For <link rel=stylesheet> elements
        "font-src": {"https://fonts.gstatic.com"},
        "worker-src": {"blob:"},
    }

    def get_required_domains(self) -> dict[str, set[str]]:
        """Get required CSP domains based on provider setting."""
        result: dict[str, set[str]] = {}

        # Determine which providers to include
        providers = {"swagger", "redoc"} if self.provider == "both" else {self.provider}

        if "swagger" in providers:
            for key, values in self.SWAGGER_DOMAINS.items():
                result.setdefault(key, set()).update(values)

        if "redoc" in providers:
            for key, values in self.REDOC_DOMAINS.items():
                result.setdefault(key, set()).update(values)

        return result


@dataclass(init=False)
class StaticFileConfig(BaseConfig):
    """Static file serving configuration."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    enabled: bool = Field(default=False, description="Enable static file serving")
    directory: str = Field(default="static", description="Directory to serve")
    prefix: str = Field(default="/static", description="URL prefix for static files")
    html: bool = Field(default=False, description="Serve HTML files (SPA mode)")


# =============================================================================
# Rate Limiting Configuration
# =============================================================================


@dataclass(init=False)
class RateLimitRuleConfig(BaseConfig):
    """Rate limit rule for a specific path pattern."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    requests: int = Field(default=100, ge=1, description="Max requests per window")
    window: int = Field(default=60, ge=1, description="Window size in seconds")
    burst: int | None = Field(
        default=None,
        description="Burst capacity (defaults to requests)",
    )

    @property
    def effective_burst(self) -> int:
        """Get burst capacity, defaulting to requests if not set."""
        return self.burst if self.burst is not None else self.requests


@dataclass(init=False)
class RateLimitConfig(BaseConfig):
    """Rate limiting configuration with per-path rules."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    enabled: bool = Field(default=True, description="Enable rate limiting")
    default_limit: int = Field(
        default=const.DEFAULT_RATE_LIMIT_REQUESTS, description="Max requests per window"
    )
    default_window: int = Field(
        default=const.DEFAULT_RATE_LIMIT_WINDOW, description="Window size in seconds"
    )
    whitelist_ips: list[str] = Field(
        default_factory=list,
        description="Exempt IP addresses",
    )
    storage_backend: str = Field(
        default="memory",
        description="Storage backend (memory/redis)",
    )

    # Per-path rules (new)
    rules: dict[str, RateLimitRuleConfig] = Field(
        default_factory=dict,
        description="Per-path rate limit rules",
    )

    @model_validator(mode="after")
    def validate_rate_limit(self) -> RateLimitConfig:
        """Validate rate limit settings."""
        if self.enabled:
            if self.default_limit <= 0:
                raise ValueError("Rate limit 'default_limit' must be greater than 0.")
            if self.default_window <= 0:
                raise ValueError("Rate limit 'default_window' must be greater than 0.")
        return self

    def get_rule(self, path: str) -> RateLimitRuleConfig | None:
        """Get rate limit rule for a path (longest prefix match)."""
        # Exact match first
        if path in self.rules:
            return self.rules[path]

        # Longest prefix match
        best_match = None
        best_length = 0
        for pattern, rule in self.rules.items():
            if path.startswith(pattern) and len(pattern) > best_length:
                best_match = rule
                best_length = len(pattern)

        return best_match


@dataclass(init=False)
class WebConfig(BaseConfig):
    """Hierarchical root configuration for Lexigram Web.

    This is the single source of truth for web configuration,
    loaded from application.yaml's `web` section.

    Attributes:
        name: Configuration name (default: "web")
        enabled: Whether the web module is enabled
        server: Server binding and worker settings
        app: Application-level settings (OpenAPI, CORS origins, etc.)
        security: Security headers and policies
        cors: CORS configuration
        rate_limit: Rate limiting rules
        debug_routes: Enable /debug/* endpoints
        enable_identity_resolution: Resolve OAuth external IDs to internal UUIDs
        enable_auth: Enable built-in authentication middleware
        auth_exclude_paths: Paths excluded from authentication
    """

    config_section: ClassVar[str] = "web"

    model_config = cast(
        "ConfigDict",
        {
            "env_prefix": "LEX_WEB__",
            "env_nested_delimiter": "__",
            "extra": "ignore",
        },
    )

    name: str = "web"
    enabled: bool = True
    env: str | None = Field(
        default=None,
        description="Environment (development/staging/production)",
    )
    server: ServerConfig = Field(default_factory=ServerConfig)
    security: SecurityConfig = Field(
        default_factory=lambda: SecurityConfig(
            csrf=CSRFConfig(
                enabled=True,
                excluded_paths=["/api/", "/health", "/metrics"],
            ),
        ),
        description="Security configuration (HSTS, CSP, cross-origin, CSRF, headers)",
    )
    cors: CORSConfig = Field(
        default_factory=lambda: CORSConfig(
            allowed_origins=["http://localhost:3000", "http://localhost:8001"],
            allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        ),
    )
    static: StaticFileConfig = Field(default_factory=StaticFileConfig)
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)

    # OpenAPI settings (formerly in WebAppConfig)
    openapi_title: str = Field(default="API", description="OpenAPI Title")
    openapi_version: str = Field(default="1.0.0", description="OpenAPI Version")
    openapi_url: str | None = Field(default=const.DEFAULT_OPENAPI_PATH)
    swagger_ui_url: str | None = Field(default=const.DEFAULT_DOCS_PATH)
    redoc_url: str | None = Field(default="/redoc")
    swagger_js_url: str | None = Field(default=None)
    swagger_css_url: str | None = Field(default=None)
    redoc_js_url: str | None = Field(default=None)
    compression_enabled: bool = Field(default=True)
    template_directory: str = Field(
        default="templates", description="Directory for Jinja2 templates"
    )

    # API Documentation - auto-configures CSP for /docs and /redoc
    api_docs: APIDocsConfig = Field(
        default_factory=APIDocsConfig,
        description="API documentation configuration (auto-configures CSP)",
    )

    # Debug routes - enable /debug/* endpoints
    debug_routes: bool = Field(default=False, description="Enable debug routes")
    enable_debug_routes_env_gate: bool = Field(
        default=False,
        description="Require explicit opt-in for debug route registration.",
    )
    debug_routes_token: SecretStr | None = Field(
        default=None,
        description="Token required to access debug routes (sent as X-Debug-Token header).",
    )

    # OAuth Identity Resolution - resolve external OAuth IDs to internal UUIDs
    enable_identity_resolution: bool = Field(
        default=False,
        description="Automatically resolve OAuth external IDs to internal UUIDs in authenticated requests",
    )

    # Authentication - enable built-in authentication middleware
    enable_auth: bool = Field(
        default=False,
        description="Enable built-in authentication middleware. Requires authenticators to be registered in the container.",
    )

    # Request body size limit — protects against OOM DoS via oversized payloads.
    # Set to None to disable the middleware entirely.
    max_body_size: int | None = Field(
        default=10 * 1024 * 1024,  # 10 MiB
        ge=1,
        description=(
            "Maximum allowed request body size in bytes. "
            "Requests with a Content-Length header exceeding this limit receive "
            "a 413 response before the body is read. "
            "Set to None to disable the body size limit (not recommended in production)."
        ),
    )

    # Paths to exclude from authentication (e.g., health checks, docs)
    auth_exclude_paths: list[str] = Field(
        default_factory=lambda: [
            const.DEFAULT_HEALTH_PATH,
            const.DEFAULT_HEALTH_PATH + "/",
            const.DEFAULT_DOCS_PATH,
            "/redoc",
            const.DEFAULT_OPENAPI_PATH,
        ],
        description="Paths to exclude from authentication",
    )

    @model_validator(mode="after")
    def validate_production_security(self) -> WebConfig:
        """Block insecure configurations in production."""
        # Use explicit env field if set, otherwise fall back to os.getenv
        env_raw = self.env or os.getenv("LEX_ENV", "development") or "development"
        env = str(env_raw).lower()
        if env == "production":
            if self.cors.allowed_origins and "*" in self.cors.allowed_origins:
                raise ValueError(
                    "CRITICAL SECURITY ERROR: Wildcard CORS origin '*' not allowed in PRODUCTION.\n"
                    "You MUST set specific origins via LEX_WEB__CORS__ALLOWED_ORIGINS.",
                )
        return self


@dataclass(init=False)
class WebProviderConfig(BaseConfig):
    """Configuration for the WebProvider itself.

    This provides provider-specific settings that complement the main WebConfig.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    # OpenAPI settings
    openapi_title: str = Field(default="API", description="OpenAPI title")
    openapi_version: str = Field(default="1.0.0", description="OpenAPI version")

    # CORS settings (provider-level)
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])
    cors_methods: list[str] = Field(
        default_factory=lambda: ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    )
    cors_headers: list[str] = Field(default_factory=lambda: ["*"])
    cors_credentials: bool = Field(default=True)

    # Middleware and filters
    middleware: list[str] = Field(
        default_factory=list,
        description="Middleware class names",
    )
    exception_filters: list[str] = Field(
        default_factory=list,
        description="Exception filter class names",
    )

    # Compression
    compression_enabled: bool = Field(
        default=True,
        description="Enable response compression",
    )

    # Whether to raise on duplicate route registrations
    fail_on_route_conflict: bool = Field(
        default=False,
        description="If true, duplicate route registrations will raise during startup; otherwise a warning is emitted",
    )

    # Debug routes settings
    debug_routes: bool = Field(default=False, description="Enable debug routes")
    debug_routes_token: SecretStr | None = Field(
        default=None,
        description="Token for debug routes access",
    )
    debug_routes_require_middleware: str | None = Field(
        default=None,
        description="Required middleware for debug routes",
    )
    debug_routes_rate_limit: int = Field(
        default=0,
        description="Rate limit for debug routes",
    )
    debug_routes_rate_window_seconds: int = Field(
        default=60,
        description="Rate limit window for debug routes",
    )

    @property
    def is_production(self) -> bool:
        """Returns True if running in production environment."""
        return self.environment.value == "production"

    @property
    def is_development(self) -> bool:
        """Returns True if running in development environment."""
        return self.environment.value == "development"

    @property
    def is_test(self) -> bool:
        """Returns True if running in test environment."""
        return self.environment.value == "test"


__all__ = [
    # CORS — canonical class from lexigram.web.security
    "CORSConfig",
    # Security configs — canonical in lexigram.web.security
    "CrossOriginConfig",
    "CSPConfig",
    "CSRFConfig",
    "HSTSConfig",
    "SecurityConfig",
    # Rate limiting
    "RateLimitConfig",
    "RateLimitRuleConfig",
    # Server
    "ServerConfig",
    # Static files
    "StaticFileConfig",
    "VersioningStrategy",
    # Main config
    "WebConfig",
    "WebProviderConfig",
]
