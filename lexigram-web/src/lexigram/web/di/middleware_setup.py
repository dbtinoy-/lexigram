"""Middleware registration helper for the Lexigram web layer."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from lexigram.contracts.core import HookRegistryProtocol
from lexigram.contracts.exceptions.container import UnresolvableDependencyError
from lexigram.contracts.exceptions.provider import ModuleVisibilityError
from lexigram.contracts.infra.cache import CacheBackendProtocol
from lexigram.logging import get_logger
from lexigram.primitives.context import Context
from lexigram.web.middleware.security import SecurityHeadersMiddleware

if TYPE_CHECKING:
    from starlette.applications import Starlette

    from lexigram.contracts.core.di import ContainerResolverProtocol
    from lexigram.web.config import WebConfig

logger = get_logger(__name__)

__all__ = ["MiddlewareSetup"]


class MiddlewareSetup:
    """Encapsulates Starlette middleware registration for the Lexigram web layer.

    Extracted from ``WebProvider`` to keep the provider focused on DI lifecycle
    (register/boot/shutdown) rather than application configuration details.

    Args:
        config: The web configuration driving middleware selection and ordering.
    """

    def __init__(
        self,
        config: WebConfig,
        hooks: HookRegistryProtocol | None = None,
    ) -> None:
        self._config = config
        self._hooks = hooks

    async def configure(
        self,
        app: Starlette,
        container: ContainerResolverProtocol,
    ) -> None:
        """Apply all configured middleware to the application.

        Middleware is applied in security-first order:

        1. Auto-configure CSP for API documentation (mutates ``self._config``).
        2. Security headers.
        3. CORS.
        4. CSRF (opt-in).
        5. Request context propagation.
        6. DI scope (request-scoped container).
        7. Request body size limit.
        8. Web hook emission middleware (outermost for broad coverage).

        Args:
            app: The Starlette application to configure.
            container: The resolved DI container; used for optional CSRF cache
                resolution.
        """
        await self._configure_csp()
        self._add_security_headers(app)
        self._add_cors(app)
        await self._add_csrf(app, container)
        self._add_request_context(app, container)
        self._add_di_scope(app, container)
        self._add_body_limit(app)
        self._add_hooks(app)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _configure_csp(self) -> None:
        """Auto-configure CSP directives for API documentation if enabled."""
        api_docs = getattr(self._config, "api_docs", None)
        if not api_docs or not api_docs.enabled:
            return

        required_domains = api_docs.get_required_domains()
        if not required_domains:
            return

        if not hasattr(self._config, "security") or not self._config.security:
            from lexigram.web.security.config import SecurityConfig

            self._config.security = SecurityConfig()

        csp = self._config.security.csp
        directives = csp.directives if hasattr(csp, "directives") else {}
        for directive, domains in required_domains.items():
            if directive not in directives:
                directives[directive] = set()
            current = directives[directive]
            if isinstance(current, str):
                current_set = {current}
            elif not isinstance(current, set):
                current_set = set(current) if current else set()
            else:
                current_set = current

            current_set.update(domains)
            directives[directive] = current_set

        logger.info(
            "auto_configured_csp_for_api_docs",
            directives={
                k: list(v) if isinstance(v, set) else v for k, v in directives.items()
            },
        )

    def _add_security_headers(self, app: Starlette) -> None:
        """Add security headers middleware when a security config is present."""
        if hasattr(self._config, "security") and self._config.security:
            app.add_middleware(
                SecurityHeadersMiddleware,
                config=self._config.security,
                enabled=True,
            )

    def _add_cors(self, app: Starlette) -> None:
        """Add CORS middleware when CORS is enabled in config."""
        if not self._config.cors.enabled:
            return

        from lexigram.logging.debug import is_debug_mode
        from lexigram.web.security.config import CORSConfig
        from lexigram.web.security.cors.middleware import (
            CORSMiddleware as WebCORSMiddleware,
        )

        cors_cfg = self._config.cors
        _debug_active = is_debug_mode() or self._config.server.debug
        _default_origins = {"http://localhost:3000", "http://localhost:8001"}
        _configured_origins = set(cors_cfg.allow_origins)

        allowed_origins = cors_cfg.allow_origins
        if _debug_active and _configured_origins == _default_origins:
            allowed_origins = ["*"]
            logger.debug(
                "cors.debug_permissive",
                reason="debug mode active, no explicit CORS config — using wildcard",
            )

        web_cors_config = CORSConfig(
            allowed_origins=allowed_origins,
            allow_credentials=cors_cfg.allow_credentials,
            allow_methods=cors_cfg.allow_methods,
            allow_headers=cors_cfg.allow_headers,
            expose_headers=cors_cfg.expose_headers,
            max_age=cors_cfg.max_age,
        )
        app.add_middleware(WebCORSMiddleware, config=web_cors_config)

    async def _add_csrf(
        self,
        app: Starlette,
        container: ContainerResolverProtocol,
    ) -> None:
        """Add CSRF protection middleware when opt-in config is present."""
        csrf_cfg = getattr(getattr(self._config, "security", None), "csrf", None)
        if csrf_cfg is None or not csrf_cfg.enabled:
            return

        from lexigram.web.security.csrf.middleware import CSRFProtectionMiddleware

        csrf_cache = None
        try:
            csrf_cache = cast("Any", container).resolve_sync(CacheBackendProtocol)
        except (UnresolvableDependencyError, AttributeError, RuntimeError, ModuleVisibilityError):
            pass

        app.add_middleware(
            CSRFProtectionMiddleware,
            config=csrf_cfg,
            cache=csrf_cache,
        )

    def _add_request_context(
        self,
        app: Starlette,
        container: ContainerResolverProtocol,
    ) -> None:
        """Add request context middleware wired to the shared core context."""
        from lexigram.web.middleware.request_context import RequestContextMiddleware

        context = cast("Any", container).resolve_sync(Context)
        app.add_middleware(RequestContextMiddleware, context=context)

    def _add_di_scope(
        self,
        app: Starlette,
        container: ContainerResolverProtocol,
    ) -> None:
        """Add DI scope middleware for request-scoped container resolution."""
        from lexigram.web.middleware.di_scope import DIScopeMiddleware

        app.add_middleware(
            DIScopeMiddleware,
            container=cast("Any", container),
        )

    def _add_hooks(self, app: Starlette) -> None:
        """Add outermost web hook middleware for request/response events."""
        from lexigram.web.middleware.hooks import WebHooksMiddleware

        app.add_middleware(WebHooksMiddleware, hooks=self._hooks)

    def _add_body_limit(self, app: Starlette) -> None:
        """Add request body size limit middleware when configured.

        Added before the hook middleware so oversized requests are still
        rejected near the edge while hooks can observe the prepared response.
        """
        max_body_size = getattr(self._config, "max_body_size", None)
        if max_body_size is None:
            return

        from lexigram.web.middleware.body_limit import RequestBodySizeLimitMiddleware

        app.add_middleware(
            RequestBodySizeLimitMiddleware,
            max_body_size=max_body_size,
        )
