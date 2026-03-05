"""HTTP-specific security configuration for lexigram-web.

Contains all transport-coupled security configs: CORS, CSRF, CSP, HSTS,
cross-origin isolation, security response headers, and the aggregate
SecurityConfig that the WebProvider exposes via ``config_key="security"``.

Transport-agnostic config (``InputSanitizerConfig``) lives in
``lexigram.security.config`` (core).
"""

from __future__ import annotations

from typing import Any, ClassVar

from lexigram.config.base import BaseConfig
from lexigram.contracts.core.config import ConfigIssue, Environment
from lexigram.security.constants import ENV_NESTED_DELIMITER, ENV_PREFIX
from lexigram.validation import ConfigDict, Field, model_validator

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------


class CORSConfig(BaseConfig):
    """CORS configuration.

    Accepts ``allow_origins`` as a convenience alias for ``allowed_origins``
    at construction time (e.g. ``CORSConfig(allow_origins=["https://..."])``).
    Comma-separated strings are also accepted so that values can be supplied
    via a single environment variable.

    Attributes:
        enabled: Enable CORS headers.  When ``False`` the middleware should
            skip CORS processing entirely.
        allowed_origins: Origins that are permitted.
            Use ``['*']`` to allow all; combine with ``allow_credentials=False``
            only.
        allow_methods: HTTP methods permitted in CORS requests.
        allow_headers: Request headers permitted in CORS requests.
        expose_headers: Response headers the browser may expose to JS.
        allow_credentials: Allow cookies / auth headers in CORS requests.
        max_age: Pre-flight cache duration in seconds.
        allow_origin_regex: Regex pattern matched against the ``Origin`` header
            as a fallback when the origin is not in ``allowed_origins``.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    enabled: bool = Field(default=True, description="Enable CORS")
    allowed_origins: list[str] = Field(
        default_factory=lambda: ["*"],
        description="Allowed origins (use ['*'] to allow all)",
    )
    allow_methods: list[str] = Field(
        default_factory=lambda: ["GET", "POST", "PUT", "DELETE", "PATCH"]
    )
    allow_headers: list[str] = Field(default_factory=lambda: ["*"])
    expose_headers: list[str] = Field(default_factory=list)
    allow_credentials: bool = Field(default=False)
    max_age: int = Field(default=600)
    allow_origin_regex: str | None = Field(
        default=None,
        description="Regex pattern for allowed origins (matched when not in allowed_origins)",
    )

    @model_validator(mode="before")
    @classmethod
    def _normalize_origins(cls, data: Any) -> Any:
        """Accept ``allow_origins`` as alias for ``allowed_origins``.

        Also parses comma-separated strings into lists so that
        ``CORS_ORIGINS="https://a.com,https://b.com"`` works via env vars.
        """
        if not isinstance(data, dict):
            return data
        data = dict(data)

        # Alias allow_origins → allowed_origins (web-compat)
        if "allow_origins" in data and "allowed_origins" not in data:
            data["allowed_origins"] = data.pop("allow_origins")

        # Parse comma-separated strings
        origins = data.get("allowed_origins")
        if isinstance(origins, str):
            data["allowed_origins"] = [
                o.strip() for o in origins.split(",") if o.strip()
            ]

        return data

    @model_validator(mode="after")
    def _validate_credentials_with_wildcard(self) -> CORSConfig:
        """Reject wildcard origins combined with allow_credentials.

        This is a CORS misconfiguration — browsers will reject such responses.
        """
        if self.allow_credentials and "*" in self.allowed_origins:
            raise ValueError(
                "SECURITY ERROR: allow_credentials=True combined with allowed_origins=['*'] "
                "is a CORS misconfiguration. Specify explicit origins when credentials are enabled."
            )
        return self

    @property
    def allow_origins(self) -> list[str]:
        """Alias for ``allowed_origins`` for backward compatibility."""
        return self.allowed_origins

    def to_middleware_kwargs(self) -> dict[str, Any]:
        """Return kwargs suitable for passing directly to a CORS middleware."""
        return {
            "allow_origins": self.allowed_origins,
            "allow_credentials": self.allow_credentials,
            "allow_methods": self.allow_methods,
            "allow_headers": self.allow_headers,
            "max_age": self.max_age,
            "allow_origin_regex": self.allow_origin_regex,
            "expose_headers": self.expose_headers,
        }

    def validate_for_environment(
        self, env: Environment | None = None
    ) -> list[ConfigIssue]:
        """Validate CORS for production environments."""
        resolved = env or self.environment
        issues: list[ConfigIssue] = []

        if resolved == Environment.PRODUCTION:
            if "*" in self.allowed_origins and self.allow_credentials:
                issues.append(
                    ConfigIssue(
                        field="cors.allowed_origins",
                        message="Wildcard origins ('*') cannot be used with allow_credentials=True in production",
                        severity="error",
                        suggestion="Explicitly list allowed origins or disable credentials",
                    )
                )

        return issues


# ---------------------------------------------------------------------------
# CSP
# ---------------------------------------------------------------------------

_DEFAULT_DIRECTIVES: dict[str, str] = {
    "default-src": "'self'",
    # Safe CDN hosts used by the framework's own templates (Swagger UI,
    # ReDoc, lexigram-admin, lexigram-ui): see UI_CSP_REQUIREMENTS and
    # APIDocsConfig.SWAGGER_DOMAINS / REDOC_DOMAINS.
    "script-src": (
        "'self' 'unsafe-inline' 'unsafe-eval' "
        "https://unpkg.com https://cdn.jsdelivr.net https://cdn.tailwindcss.com "
        "https://cdn.redoc.ly https://cdn.plot.ly"
    ),
    "script-src-elem": (
        "'self' 'unsafe-inline' 'unsafe-eval' "
        "https://unpkg.com https://cdn.jsdelivr.net https://cdn.tailwindcss.com "
        "https://cdn.redoc.ly https://cdn.plot.ly"
    ),
    "style-src": (
        "'self' 'unsafe-inline' "
        "https://unpkg.com https://cdn.jsdelivr.net https://cdn.tailwindcss.com "
        "https://fonts.googleapis.com"
    ),
    "style-src-elem": (
        "'self' 'unsafe-inline' "
        "https://unpkg.com https://cdn.jsdelivr.net https://cdn.tailwindcss.com "
        "https://fonts.googleapis.com"
    ),
    "img-src": "'self' data: https: blob:",
    "font-src": "'self' data: https://fonts.googleapis.com https://fonts.gstatic.com",
    "connect-src": "'self' https: wss: ws: https://unpkg.com",
    "frame-ancestors": "'none'",
    "base-uri": "'self'",
    "form-action": "'self'",
}


class CSPConfig(BaseConfig):
    """Content Security Policy configuration.

    Manages CSP directives as a ``dict[str, str | set[str]]`` and
    serialises them to the ``Content-Security-Policy`` header value
    via :meth:`build_header`.

    Attributes:
        enabled: Emit the ``Content-Security-Policy`` header.
        directives: Mapping of CSP directive name to source expression(s).
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    enabled: bool = Field(
        default=True, description="Emit the Content-Security-Policy header"
    )
    directives: dict[str, Any] = Field(
        default_factory=lambda: dict(_DEFAULT_DIRECTIVES),
        description="CSP directives mapping directive name to source expression(s)",
    )

    @model_validator(mode="after")
    def _merge_default_directives(self) -> CSPConfig:
        """Merge the framework default directives into the configured ones.

        User-supplied directives always win per-key; any directive the user
        omitted falls back to the safe framework default. This prevents a
        partial ``directives`` dict from silently dropping defaults — e.g. a
        user configuring only ``style-src`` previously lost the default
        ``style-src-elem`` with ``'unsafe-inline'``, which then blocked all
        inline styles (the CSP fallback chain does not apply when the
        ``-elem`` variant is present).

        Returns:
            Self with merged directives.
        """
        merged = dict(_DEFAULT_DIRECTIVES)
        merged.update(self.directives)
        self.directives = merged
        return self

    def build_header(self) -> str:
        """Build the ``Content-Security-Policy`` header value.

        Returns:
            Semicolon-delimited CSP policy string ready for the response header.
        """
        parts: list[str] = []
        for directive, value in self.directives.items():
            if isinstance(value, set):
                csp_value = " ".join(str(v) for v in value) if value else "'none'"
                parts.append(f"{directive} {csp_value}")
            else:
                str_value = str(value)
                if str_value:
                    parts.append(f"{directive} {str_value}")
                else:
                    parts.append(directive)
        return "; ".join(parts)


# ---------------------------------------------------------------------------
# CSRF
# ---------------------------------------------------------------------------


class CSRFConfig(BaseConfig):
    """Configuration for CSRF protection middleware.

    Attributes:
        enabled: Whether CSRF protection is active.
        cookie_name: Name of the cookie storing the CSRF token.
        header_name: Name of the header containing the client CSRF token.
        cookie_secure: Whether the cookie should be marked as secure (HTTPS only).
        cookie_httponly: Whether the cookie should be marked as HttpOnly.
        cookie_samesite: Value for the SameSite attribute ('Lax', 'Strict', or 'None').
        cookie_domain: Optional domain attribute for the CSRF cookie.
        cookie_path: Path attribute for the CSRF cookie.
        token_length: Length of the generated CSRF token in bytes.
        token_ttl: Lifetime in seconds for synchronizer-mode tokens stored in cache.
        excluded_paths: URL path prefixes that are exempt from CSRF validation.
        exclude_content_types: ``Content-Type`` values that bypass CSRF validation.
        exclude_auth_schemes: Authorization header schemes that bypass CSRF validation.
        secret_key: HMAC secret used to sign and verify CSRF tokens.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    enabled: bool = Field(default=False)
    cookie_name: str = Field(default="csrf_token")
    header_name: str = Field(default="X-CSRF-Token")
    cookie_secure: bool = Field(default=True)
    cookie_httponly: bool = Field(default=True)
    cookie_samesite: str = Field(default="Lax")
    cookie_domain: str | None = Field(default=None)
    cookie_path: str = Field(default="/")
    token_length: int = Field(default=32)
    token_ttl: int = Field(
        default=3600,
        description="TTL in seconds for synchronizer-mode tokens stored in cache.",
    )
    excluded_paths: list[str] = Field(
        default_factory=list,
        description="URL path prefixes that are exempt from CSRF validation.",
    )
    exclude_content_types: list[str] = Field(
        default_factory=lambda: ["application/json"],
        description="Content-Type values that bypass CSRF validation.",
    )
    exclude_auth_schemes: list[str] = Field(
        default_factory=lambda: ["bearer", "apikey", "api-key"],
        description="Authorization header schemes that bypass CSRF validation.",
    )
    _secret_key: str | None = Field(default=None)

    @property
    def secret_key(self) -> str | None:
        """Return the HMAC secret key, or ``None`` when not configured."""
        return self._secret_key

    def validate_for_environment(
        self, env: Environment | None = None
    ) -> list[ConfigIssue]:
        """CSRF production validation."""
        resolved = env or self.environment
        issues: list[ConfigIssue] = []

        if resolved == Environment.PRODUCTION and self.enabled:
            if not self._secret_key or self._secret_key.strip() == "":
                issues.append(
                    ConfigIssue(
                        field="csrf.secret_key",
                        message="CSRF is enabled but no secret_key is set in production",
                        severity="warning",
                        suggestion="Set a strong, random secret_key if using HMAC-based CSRF protection",
                    )
                )

        return issues


# ---------------------------------------------------------------------------
# Security Headers
# ---------------------------------------------------------------------------


class SecurityHeadersConfig(BaseConfig):
    """Configuration for security response headers.

    Attributes:
        hsts_max_age: Strict-Transport-Security max age in seconds.
        hsts_include_subdomains: Whether HSTS applies to subdomains.
        content_type_nosniff: Sets X-Content-Type-Options to 'nosniff'.
        frame_options: X-Frame-Options value ('DENY', 'SAMEORIGIN').
        xss_protection: X-XSS-Protection value.
        referrer_policy: Referrer-Policy value.
        csp: Content-Security-Policy header string.
        permissions_policy: Permissions-Policy header string.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    hsts_max_age: int = Field(default=31536000)
    hsts_include_subdomains: bool = Field(default=True)
    content_type_nosniff: bool = Field(default=True)
    frame_options: str = Field(default="DENY")
    xss_protection: str = Field(default="1; mode=block")
    referrer_policy: str = Field(default="strict-origin-when-cross-origin")
    csp: str | None = Field(default=None)
    permissions_policy: str | None = Field(default=None)

    def validate_for_environment(
        self, env: Environment | None = None
    ) -> list[ConfigIssue]:
        """Validate security headers for production."""
        resolved = env or self.environment
        issues: list[ConfigIssue] = []

        if resolved == Environment.PRODUCTION:
            if self.hsts_max_age < 31536000:
                issues.append(
                    ConfigIssue(
                        field="headers.hsts_max_age",
                        message="HSTS max_age should be at least 1 year (31536000 seconds) in production",
                        severity="warning",
                        suggestion="Increase hsts_max_age to 31536000 or higher",
                    )
                )

        return issues


# ---------------------------------------------------------------------------
# HSTS
# ---------------------------------------------------------------------------


class HSTSConfig(BaseConfig):
    """HTTP Strict Transport Security configuration.

    Attributes:
        enabled: Emit the ``Strict-Transport-Security`` header.
        max_age: ``max-age`` directive in seconds.
        include_subdomains: Append the ``includeSubDomains`` directive.
        preload: Append the ``preload`` directive.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    enabled: bool = Field(
        default=False, description="Emit the Strict-Transport-Security header"
    )
    max_age: int = Field(
        default=31536000, description="HSTS max-age in seconds (default 1 year)"
    )
    include_subdomains: bool = Field(
        default=True, description="Apply HSTS to all subdomains"
    )
    preload: bool = Field(
        default=False, description="Include site in HSTS preload list"
    )


# ---------------------------------------------------------------------------
# Cross-Origin
# ---------------------------------------------------------------------------


class CrossOriginConfig(BaseConfig):
    """Cross-Origin policy configuration.

    Controls whether and with what values the three cross-origin
    isolation headers are sent:

    * ``Cross-Origin-Embedder-Policy``
    * ``Cross-Origin-Opener-Policy``
    * ``Cross-Origin-Resource-Policy``

    Attributes:
        enabled: Emit the cross-origin isolation headers.
        embedder_policy: ``COEP`` value (e.g. ``'require-corp'``).
        opener_policy: ``COOP`` value (e.g. ``'same-origin'``).
        resource_policy: ``CORP`` value (e.g. ``'same-origin'``).
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    enabled: bool = Field(
        default=False,
        description="Emit cross-origin isolation headers",
    )
    embedder_policy: str = Field(
        default="require-corp",
        description="Cross-Origin-Embedder-Policy header value",
    )
    opener_policy: str = Field(
        default="same-origin",
        description="Cross-Origin-Opener-Policy header value",
    )
    resource_policy: str = Field(
        default="same-origin",
        description="Cross-Origin-Resource-Policy header value",
    )


# ---------------------------------------------------------------------------
# SecurityConfig (aggregate)
# ---------------------------------------------------------------------------


class SecurityConfig(BaseConfig):
    """Root HTTP security configuration for lexigram-web.

    Aggregates CORS, CSRF, security-headers, and HTTP security-policy
    sub-configs into a single object.

    Attributes:
        cors: CORS policy configuration.
        csrf: CSRF protection configuration.
        headers: Low-level security response headers.
        hsts: Structured HSTS configuration.
        csp: Content Security Policy configuration.
        cross_origin: Cross-origin isolation policy headers.
        referrer_policy: Referrer-Policy header value.
        custom_headers: Additional response headers emitted verbatim.
        permissions_policy: Permissions-Policy directive map.
        enable_csrf: Convenience flag — enable/disable CSRF.
        enable_cors: Convenience flag — enable/disable CORS.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(
        env_prefix=ENV_PREFIX,  # type: ignore[typeddict-unknown-key]
        env_nested_delimiter=ENV_NESTED_DELIMITER,
        extra="ignore",
    )

    enabled: bool = Field(default=True, description="Enable the security subsystem")

    cors: CORSConfig = Field(default_factory=CORSConfig)
    csrf: CSRFConfig = Field(default_factory=CSRFConfig)
    headers: SecurityHeadersConfig = Field(default_factory=SecurityHeadersConfig)

    # Convenience flags
    enable_csrf: bool = Field(default=True)
    enable_cors: bool = Field(default=True)

    # HTTP security-policy sub-configs
    hsts: HSTSConfig = Field(
        default_factory=HSTSConfig,
        description="HSTS configuration (enabled, max_age, subdomains, preload)",
    )
    csp: CSPConfig = Field(
        default_factory=CSPConfig,
        description="Content Security Policy configuration",
    )
    cross_origin: CrossOriginConfig = Field(
        default_factory=CrossOriginConfig,
        description="Cross-origin isolation policy headers",
    )
    referrer_policy: str = Field(
        default="strict-origin-when-cross-origin",
        description="Referrer-Policy header value",
    )
    custom_headers: dict[str, str] = Field(
        default_factory=lambda: {
            "x-content-type-options": "nosniff",
            "x-frame-options": "DENY",
            "x-xss-protection": "1; mode=block",
        },
        description="Additional HTTP response headers emitted verbatim",
    )
    permissions_policy: dict[str, str] = Field(
        default_factory=lambda: {
            "geolocation": "()",
            "microphone": "()",
            "camera": "()",
            "payment": "()",
            "usb": "()",
        },
        description="Permissions-Policy directive map",
    )

    def validate_for_environment(
        self, env: Environment | None = None
    ) -> list[ConfigIssue]:
        """Aggregate validation from all sub-configs."""
        issues: list[ConfigIssue] = []
        issues.extend(self.cors.validate_for_environment(env))
        issues.extend(self.csrf.validate_for_environment(env))
        issues.extend(self.headers.validate_for_environment(env))
        return issues


__all__ = [
    "CORSConfig",
    "CSPConfig",
    "CSRFConfig",
    "CrossOriginConfig",
    "HSTSConfig",
    "SecurityConfig",
    "SecurityHeadersConfig",
]
