"""Tests for Security Config Collapse — post-refactoring verification.

Verifies that all web security config classes use canonical types from
``lexigram.web.security.config``:
- HSTSConfig, CSPConfig, CrossOriginConfig, CSRFConfig, CORSConfig, SecurityConfig
  are all defined in the web security package and imported directly.
"""

from __future__ import annotations

import pytest

from lexigram.web.config import WebConfig
from lexigram.web.security.config import (
    CORSConfig,
    CrossOriginConfig,
    CSPConfig,
    CSRFConfig,
    HSTSConfig,
    SecurityConfig,
)


class TestSecurityConfigCollapseDecisions:
    """Verify security config types are canonical and behave correctly."""

    # ── HSTSConfig ────────────────────────────────────────────────────────────

    def test_hsts_config_is_from_web_security_package(self) -> None:
        """HSTSConfig is the canonical class from lexigram.web.security."""
        from lexigram.web.security.config import HSTSConfig as WebSecurityHSTSConfig

        assert HSTSConfig is WebSecurityHSTSConfig

    def test_hsts_config_has_enabled_and_preload_fields(self) -> None:
        """HSTSConfig from security has 'enabled' and 'preload' fields."""
        config = HSTSConfig()
        assert hasattr(config, "enabled")
        assert hasattr(config, "preload")
        assert hasattr(config, "max_age")
        assert hasattr(config, "include_subdomains")
        assert config.max_age == 31536000

    # ── CSPConfig ─────────────────────────────────────────────────────────────

    def test_csp_config_is_from_web_security_package(self) -> None:
        """CSPConfig is the canonical class from lexigram.web.security."""
        from lexigram.web.security.config import CSPConfig as WebSecurityCSPConfig

        assert CSPConfig is WebSecurityCSPConfig

    def test_csp_config_has_build_header_method(self) -> None:
        """CSPConfig has build_header() method and directive support."""
        config = CSPConfig()
        assert callable(config.build_header)
        assert isinstance(config.directives, dict)
        header = config.build_header()
        assert isinstance(header, str)
        assert "default-src" in header

    def test_csp_config_has_sensible_defaults(self) -> None:
        """CSPConfig provides secure-by-default CSP directives."""
        config = CSPConfig()
        assert config.directives is not None
        assert "default-src" in config.directives
        assert config.directives["default-src"] == "'self'"

    # ── CrossOriginConfig ─────────────────────────────────────────────────────

    def test_cross_origin_config_is_from_web_security_package(self) -> None:
        """CrossOriginConfig is canonical from lexigram.web.security."""
        from lexigram.web.security.config import (
            CrossOriginConfig as WebSecurityCrossOriginConfig,
        )

        assert CrossOriginConfig is WebSecurityCrossOriginConfig

    def test_cross_origin_config_fields(self) -> None:
        """CrossOriginConfig has the cross-origin isolation policy fields."""
        config = CrossOriginConfig()
        assert hasattr(config, "enabled")
        assert hasattr(config, "embedder_policy")
        assert hasattr(config, "opener_policy")
        assert hasattr(config, "resource_policy")
        assert config.embedder_policy == "require-corp"
        assert config.opener_policy == "same-origin"
        assert config.resource_policy == "same-origin"

    # ── CSRFConfig ────────────────────────────────────────────────────────────

    def test_csrf_config_is_from_web_security_package(self) -> None:
        """CSRFConfig is the canonical class from lexigram.web.security."""
        from lexigram.web.security.config import CSRFConfig as WebSecurityCSRFConfig

        assert CSRFConfig is WebSecurityCSRFConfig

    def test_csrf_config_has_excluded_paths(self) -> None:
        """CSRFConfig has the 'excluded_paths' field."""
        config = CSRFConfig()
        assert hasattr(config, "excluded_paths")
        assert isinstance(config.excluded_paths, list)

    def test_csrf_config_all_fields_documented(self) -> None:
        """CSRFConfig fields are properly typed."""
        config = CSRFConfig(
            enabled=True,
            cookie_samesite="strict",
            cookie_secure=True,
            cookie_name="my_csrf",
            header_name="X-Custom-CSRF",
            excluded_paths=["/public/"],
        )
        assert config.enabled is True
        assert config.cookie_samesite == "strict"
        assert config.cookie_secure is True
        assert config.cookie_name == "my_csrf"
        assert config.header_name == "X-Custom-CSRF"
        assert config.excluded_paths == ["/public/"]

    def test_webconfigcors_security_csrf_enabled_by_default(self) -> None:
        """WebConfig().security.csrf is enabled=True for web's secure-by-default UX."""
        config = WebConfig()
        assert config.security.csrf.enabled is True
        assert len(config.security.csrf.excluded_paths) > 0

    # ── CORSConfig ────────────────────────────────────────────────────────────

    def test_cors_config_is_from_web_security_package(self) -> None:
        """CORSConfig is the canonical class from lexigram.web.security."""
        from lexigram.web.security.config import CORSConfig as WebSecurityCORSConfig

        assert CORSConfig is WebSecurityCORSConfig

    def test_cors_config_has_utility_methods(self) -> None:
        """CORSConfig has to_middleware_kwargs() and allow_origins alias."""
        config = CORSConfig()
        assert callable(config.to_middleware_kwargs)
        assert hasattr(config, "allow_origins")

    def test_cors_config_accepts_allow_origins_kwarg(self) -> None:
        """CORSConfig accepts allow_origins= keyword (alias for allowed_origins)."""
        config = CORSConfig(allow_origins=["http://localhost:3000"])
        assert "http://localhost:3000" in config.allowed_origins
        assert "http://localhost:3000" in config.allow_origins

    def test_cors_config_parses_comma_separated_origins(self) -> None:
        """CORSConfig parses comma-separated origin strings from env vars."""
        config = CORSConfig(allowed_origins="http://a.com,http://b.com")
        assert config.allowed_origins == ["http://a.com", "http://b.com"]

    def test_cors_config_validate_credentials_with_origins(self) -> None:
        """CORSConfig rejects credentials + wildcard origins."""
        with pytest.raises(ValueError, match="CORS misconfiguration"):
            CORSConfig(
                allow_credentials=True,
                allow_origins=["*"],
            )

    def test_middleware_adapter_pattern_cors_config(self) -> None:
        """CORSConfig supports middleware adapter pattern."""
        config = CORSConfig(
            allow_origins=["https://a.com"],
            allow_methods=["GET", "POST"],
            allow_headers=["Content-Type"],
            max_age=3600,
        )
        kwargs = config.to_middleware_kwargs()
        assert kwargs["allow_origins"] == ["https://a.com"]
        assert kwargs["allow_methods"] == ["GET", "POST"]
        assert kwargs["max_age"] == 3600

    # ── SecurityConfig ────────────────────────────────────────────────────────

    def test_security_config_is_from_web_security_package(self) -> None:
        """SecurityConfig is canonical from lexigram.web.security."""
        from lexigram.web.security.config import SecurityConfig as WebSecurityConfig

        assert SecurityConfig is WebSecurityConfig

    def test_web_config_security_field_is_security_config(self) -> None:
        """WebConfig().security is an instance of web security SecurityConfig."""
        config = WebConfig()
        assert isinstance(config.security, SecurityConfig)

    def test_security_config_has_all_sub_configs(self) -> None:
        """SecurityConfig has all required sub-configs."""
        config = SecurityConfig()
        assert isinstance(config.hsts, HSTSConfig)
        assert isinstance(config.csp, CSPConfig)
        assert isinstance(config.cross_origin, CrossOriginConfig)
        assert isinstance(config.csrf, CSRFConfig)
        assert hasattr(config, "referrer_policy")
        assert hasattr(config, "permissions_policy")
        assert hasattr(config, "custom_headers")

    def test_no_local_class_definitions_for_collapsed_classes(self) -> None:
        """Confirm no local class definitions remain in web/config.py for security classes."""
        import inspect

        from lexigram.web import config as web_config_module

        # Each collapsed class must NOT be defined in web.config
        for cls_name in ["HSTSConfig", "CSPConfig", "CrossOriginConfig"]:
            cls = getattr(web_config_module, cls_name)
            assert inspect.getmodule(cls) is not web_config_module, (
                f"{cls_name} should be defined in lexigram.web.security.config, not lexigram-web/config.py"
            )

    # ── Integration ───────────────────────────────────────────────────────────

    def test_full_web_config_with_all_security_settings(self) -> None:
        """WebConfig supports comprehensive security configuration."""
        config = WebConfig(
            security=SecurityConfig(
                hsts=HSTSConfig(enabled=True, max_age=31536000),
                csp=CSPConfig(enabled=True),
                cross_origin=CrossOriginConfig(enabled=True),
                csrf=CSRFConfig(enabled=True),
            ),
            cors=CORSConfig(
                allowed_origins=["https://example.com"],
                allow_credentials=False,
            ),
        )
        assert config.security.hsts.enabled is True
        assert config.security.csp.enabled is True
        assert config.security.cross_origin.enabled is True
        assert config.security.csrf.enabled is True
        assert config.cors.allowed_origins == ["https://example.com"]

    def test_no_circular_imports(self) -> None:
        """Config classes don't create circular imports with security package."""
        from lexigram.web.config import SecurityConfig as WebSecurityConfig
        from lexigram.web.security.config import SecurityConfig as DirectSecurityConfig

        assert WebSecurityConfig is DirectSecurityConfig
        sec = SecurityConfig()
        assert sec is not None
