"""Admin auth sub-provider — authentication, guards, sessions, CSRF, sanitization.

Registration bodies live in :mod:`.auth_registrations` (core services and
the new auth service layer); this provider invokes them at their original
positions and owns the boot/shutdown lifecycle.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.admin.di.sub_providers.auth_registrations import (
    register_core_services,
    register_new_auth_services,
)
from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.admin.config import AdminConfig
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )

logger = get_logger(__name__)


class AdminAuthSubProvider:
    """Manages admin authentication infrastructure: guards, sessions, CSRF, security.

    Registers auth-related services: guard chain, session manager, CSRF protection,
    input sanitization, and security headers. Auth primitives are expected to be
    provided through contract bindings by the host application's auth provider.
    """

    def __init__(
        self,
        config: AdminConfig,
        auth_provider: Any | None = None,
        **kwargs: object,
    ) -> None:
        self._config = config
        self._auth_provider = auth_provider
        self._kwargs = kwargs
        self._initialized = False

    @property
    def config(self) -> AdminConfig:
        """Return current admin config."""
        return self._config

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Register auth services: guard chain, session manager, CSRF, sanitizer."""
        # Core bindings: user store, guard chain, session manager, guard
        # config, middleware sanitization, RBAC permission service, and
        # the authorizer PDP bindings.
        register_core_services(container, self._config)

        # ------------------------------------------------------------------
        # New admin auth services
        # ------------------------------------------------------------------
        register_new_auth_services(container, self._config)

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Boot auth services: initialize guard chain, session management.

        Attempts to initialize the schema for every new SQL store. Failures
        are logged at WARNING level and never re-raised so that a missing
        table does not prevent the admin panel from starting.

        Also wires the optional ``CacheBackendProtocol`` into
        ``AdminLoginAttemptService`` when the cache provider is available.

        Args:
            container: The container resolver (container is frozen at this point).
        """
        self._initialized = True

        # ── Schema initialization for new auth stores ─────────────────────
        from lexigram.admin.auth.protocols import (
            AdminAccountLockoutStoreProtocol,
            AdminAuditLogStoreProtocol,
            AdminEmailOtpStoreProtocol,
            AdminEmailVerificationServiceProtocol,
            AdminEmailVerificationStoreProtocol,
            AdminLoginAttemptServiceProtocol,
            AdminLoginAttemptStoreProtocol,
            AdminMfaStoreProtocol,
            AdminPasswordResetServiceProtocol,
            AdminPasswordResetTokenStoreProtocol,
        )
        from lexigram.admin.rbac.protocols import AdminRoleStoreProtocol

        # ── Schema-version marker (R15) ────────────────────────────────────
        # When the stored fingerprint matches this build, the ensure pass
        # below is skipped (16 DDL statements → 1 SELECT) and each store is
        # marked ready. Every marker failure falls back to the full ensure
        # pass — the marker can never make boot worse.
        marker = None
        schema_current = False
        try:
            from lexigram.admin.auth.store.schema_marker import (
                ADMIN_AUTH_SCHEMA_FINGERPRINT,
                AUTH_STORES_COMPONENT,
                AdminSchemaMarker,
            )
            from lexigram.contracts.data import DatabaseProviderProtocol

            _db = await container.resolve(
                DatabaseProviderProtocol, bypass_visibility=True
            )
            marker = AdminSchemaMarker(_db)
            schema_current = await marker.is_current(
                AUTH_STORES_COMPONENT, ADMIN_AUTH_SCHEMA_FINGERPRINT
            )
        except Exception:  # noqa: BLE001 — marker is best-effort; fall back to ensures
            logger.debug("admin_auth.schema_marker_unavailable")

        all_schemas_ok = True
        for _store_protocol in (
            AdminLoginAttemptStoreProtocol,
            AdminAccountLockoutStoreProtocol,
            AdminAuditLogStoreProtocol,
            AdminPasswordResetTokenStoreProtocol,
            AdminMfaStoreProtocol,
            AdminRoleStoreProtocol,
            AdminEmailVerificationStoreProtocol,
            AdminEmailOtpStoreProtocol,
        ):
            try:
                _store = await container.resolve(
                    _store_protocol, bypass_visibility=True
                )
                if schema_current:
                    # Skip the probe entirely; stores keep their lazy
                    # per-call ensure as a fallback when the attribute is
                    # missing (custom store implementations).
                    if hasattr(_store, "_initialized"):
                        _store._initialized = True
                    continue
                await _store.ensure_schema()  # type: ignore[attr-defined]
            except Exception as e:
                all_schemas_ok = False
                logger.exception(f"admin_auth.schema_init_failed: {e}")  # noqa: BLE001
                logger.warning(
                    "admin_auth.schema_init_failed",
                    protocol=str(_store_protocol),
                )

        if schema_current:
            logger.info(
                "admin_auth.schema_current",
                component="admin.auth_stores",
                note=(
                    "ensure pass skipped; if the schema was mutated by hand, "
                    "delete the admin_schema_markers row and restart"
                ),
            )
        elif all_schemas_ok and marker is not None:
            try:
                await marker.mark_current(
                    AUTH_STORES_COMPONENT, ADMIN_AUTH_SCHEMA_FINGERPRINT
                )
                logger.info(
                    "admin_auth.schema_marker_written",
                    component="admin.auth_stores",
                )
            except Exception:  # noqa: BLE001 — marker write is best-effort
                logger.debug("admin_auth.schema_marker_write_failed")

        # ── Wire cache into AdminLoginAttemptService (optional) ───────────
        try:
            from lexigram.contracts.infra.cache import CacheBackendProtocol

            _cache = await container.resolve(CacheBackendProtocol)
            _attempt_svc = await container.resolve(
                AdminLoginAttemptServiceProtocol, bypass_visibility=True
            )
            if hasattr(_attempt_svc, "_cache"):
                _attempt_svc._cache = _cache
            logger.debug("admin_auth.cache_wired")
        except Exception:
            logger.debug("admin_auth.cache_not_available")

        # ── Wire cache into AdminEmailVerificationService (optional) ─────
        try:
            from lexigram.contracts.infra.cache import CacheBackendProtocol

            _cache = await container.resolve(CacheBackendProtocol)
            _verif_svc = await container.resolve(
                AdminEmailVerificationServiceProtocol, bypass_visibility=True
            )
            if hasattr(_verif_svc, "_cache"):
                _verif_svc._cache = _cache
            logger.debug("admin_auth.verification_cache_wired")
        except Exception:
            logger.debug("admin_auth.verification_cache_not_available")

        # ── Wire cache into AdminPasswordResetService (optional) ──────────
        try:
            from lexigram.contracts.infra.cache import CacheBackendProtocol

            _cache = await container.resolve(CacheBackendProtocol)
            _reset_svc = await container.resolve(
                AdminPasswordResetServiceProtocol, bypass_visibility=True
            )
            if hasattr(_reset_svc, "_cache"):
                _reset_svc._cache = _cache
            logger.debug("admin_auth.reset_cache_wired")
        except Exception:
            logger.debug("admin_auth.reset_cache_not_available")

    async def shutdown(self) -> None:
        """Shut down auth services."""
        self._initialized = False

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Return auth infrastructure health status."""
        return HealthCheckResult(
            component="admin_auth",
            status=HealthStatus.HEALTHY if self._initialized else HealthStatus.UNKNOWN,
            message="Admin auth operational"
            if self._initialized
            else "Not yet initialized",
        )


__all__ = ["AdminAuthSubProvider"]
