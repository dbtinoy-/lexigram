"""Admin auth sub-provider — authentication, guards, sessions, CSRF, sanitization."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

# Runtime imports (not TYPE_CHECKING): the @inject local subclasses below
# annotate their constructors with these protocol names. Under
# ``from __future__ import annotations`` those annotations are strings that
# get_type_hints resolves against the module globals — function-local imports
# are invisible to it, which would silently drop the injectable parameters.
from lexigram.admin.auth.protocols import (
    AdminAuditLogServiceProtocol,
    AdminEmailOtpServiceProtocol,
    AdminEmailOtpStoreProtocol,
    AdminEmailVerificationServiceProtocol,
    AdminEmailVerificationStoreProtocol,
    AdminLoginAttemptServiceProtocol,
    AdminMfaServiceProtocol,
    AdminMfaStoreProtocol,
    AdminSessionServiceProtocol,
)
from lexigram.admin.auth.store.protocols import AdminUserStoreProtocol
from lexigram.admin.services.notifications import AdminNotificationService
from lexigram.contracts.auth.repositories import SessionRepositoryProtocol
from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.logging import get_logger
from lexigram.validation import SecretStr

if TYPE_CHECKING:
    from lexigram.admin.config import AdminConfig
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )


async def _resolve_admin_authorizer(container: Any) -> Any:
    """Return the lexigram-auth AuthorizationService, constructing on demand."""
    from lexigram.auth.authz.service import AuthorizationService

    try:
        return await container.resolve(AuthorizationService, bypass_visibility=True)
    except Exception:  # noqa: BLE001 — auth provider not bound: default engine
        return AuthorizationService()


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
        from lexigram.admin.auth.guard_chain import AdminGuardChain
        from lexigram.admin.auth.guards import GuardConfig
        from lexigram.admin.auth.session_manager import AdminSessionManager
        from lexigram.admin.auth.store.direct_sql import DirectSQLAdminUserStore
        from lexigram.admin.auth.store.session_sql import AdminSessionSqlRepository
        from lexigram.admin.middleware.input_sanitizer import AdminInputSanitizer
        from lexigram.admin.middleware.security_headers import AdminSecurityHeaders
        from lexigram.admin.rbac.service import PermissionService
        from lexigram.contracts.auth.repositories import SessionRepositoryProtocol

        # Bind the admin user store protocol to the SQL implementation, or to
        # the app-principal adapter when configured (spec D3). SetupMiddleware
        # and any other service that needs to manage admin-panel accounts
        # depend on AdminUserStoreProtocol — never on the concrete class.
        if getattr(self._config.auth, "principal_source", "internal") == "app":
            from lexigram.admin.auth.store.app_principal import (
                AppPrincipalUserStoreAdapter,
            )

            container.singleton(AdminUserStoreProtocol, AppPrincipalUserStoreAdapter)
        else:
            container.singleton(AdminUserStoreProtocol, DirectSQLAdminUserStore)

        # Register guard chain (container will instantiate via DI)
        container.singleton(AdminGuardChain, AdminGuardChain)

        # Register the SQL repository as SessionRepositoryProtocol so the
        # container can inject it into AdminSessionManager.
        container.singleton(SessionRepositoryProtocol, AdminSessionSqlRepository)
        container.singleton(AdminSessionManager, AdminSessionManager)

        # Guard config — pre-constructed with defaults
        container.singleton(GuardConfig, GuardConfig())

        container.singleton(AdminInputSanitizer, AdminInputSanitizer)
        container.singleton(AdminSecurityHeaders, AdminSecurityHeaders)
        container.singleton(PermissionService, PermissionService)

        # ── AuthorizerProtocol — single PDP instance (spec §2.2) ────────────
        # The one authorization engine: lexigram-auth's AuthorizationService.
        # Every consumer (ResourceManager, ActionExecutor, PermissionService,
        # AdminRoleService) resolves the SAME object from the container.
        # ── RequestAuthorizerProtocol — request-entry RBAC (AUTH-09, AUTH-18) ─
        # Default: authenticated users pass (fail-closed on identity).
        # App authors override either binding in their on_admin_boot hook.
        from lexigram.admin.middleware.authorization import (
            DefaultRequestAuthorizer,
            RequestAuthorizerProtocol,
        )
        from lexigram.contracts.auth import AuthorizerProtocol

        container.singleton(AuthorizerProtocol, factory=_resolve_admin_authorizer)
        container.singleton(RequestAuthorizerProtocol, DefaultRequestAuthorizer)

        # ------------------------------------------------------------------
        # New admin auth services
        # ------------------------------------------------------------------
        self._register_new_auth_services(container)

        # ------------------------------------------------------------------
        # Contract-first auth integration.
        # Concrete implementations for auth primitives are expected to be
        # registered by the application's auth provider.
        # ------------------------------------------------------------------

    def _register_new_auth_services(
        self, container: ContainerRegistrarProtocol
    ) -> None:
        """Register SQL stores and auth services introduced in the new auth layer.

        Registration order:
        1. SQL stores (protocol → concrete SQL class, DI-wired via ``@inject``).
        2. ``AdminAuditLogService`` (DI-wired via ``@inject``).
        3. ``AdminPasswordPolicyService`` — pre-built from config; no DI deps.
        4. ``AdminCsrfService`` — pre-built from config; no DI deps.
        5. ``AdminSessionService`` — thin ``@inject`` subclass to pass config
           values alongside the DI-resolved ``SessionRepositoryProtocol``.
        6. ``AdminLoginAttemptService`` — DI-wired; cache is optional and wired
           in ``boot()`` if ``CacheBackendProtocol`` is available.
        7. ``AdminAuthService`` — DI-wired orchestrator.

        Args:
            container: The container registrar for the current boot phase.
        """
        from lexigram.admin.auth.protocols import (
            AdminAccountLockoutStoreProtocol,
            AdminAuditLogServiceProtocol,
            AdminAuditLogStoreProtocol,
            AdminAuthServiceProtocol,
            AdminCsrfServiceProtocol,
            AdminLoginAttemptServiceProtocol,
            AdminLoginAttemptStoreProtocol,
            AdminPasswordPolicyServiceProtocol,
            AdminPasswordResetServiceProtocol,
            AdminPasswordResetTokenStoreProtocol,
            AdminSessionServiceProtocol,
        )
        from lexigram.admin.auth.services.audit_log_service import AdminAuditLogService
        from lexigram.admin.auth.services.auth_service import AdminAuthService
        from lexigram.admin.auth.services.csrf_service import AdminCsrfService
        from lexigram.admin.auth.services.login_attempt_service import (
            AdminLoginAttemptService,
        )
        from lexigram.admin.auth.services.password_policy_service import (
            AdminPasswordPolicyService,
        )
        from lexigram.admin.auth.services.password_reset_service import (
            AdminPasswordResetService,
        )
        from lexigram.admin.auth.services.session_service import AdminSessionService
        from lexigram.admin.auth.store.audit_log_sql import AdminAuditLogSqlStore
        from lexigram.admin.auth.store.lockout_sql import AdminAccountLockoutSqlStore
        from lexigram.admin.auth.store.login_attempt_sql import (
            AdminLoginAttemptSqlStore,
        )
        from lexigram.admin.auth.store.password_reset_token_sql import (
            AdminPasswordResetTokenSqlStore,
        )
        from lexigram.di.decorators import inject

        # ── SQL stores ────────────────────────────────────────────────────
        container.singleton(AdminLoginAttemptStoreProtocol, AdminLoginAttemptSqlStore)
        container.singleton(
            AdminAccountLockoutStoreProtocol, AdminAccountLockoutSqlStore
        )
        container.singleton(AdminAuditLogStoreProtocol, AdminAuditLogSqlStore)
        container.singleton(
            AdminPasswordResetTokenStoreProtocol, AdminPasswordResetTokenSqlStore
        )

        # ── Config extraction (safe getattr — works even when config is None) ──
        _auth_cfg = getattr(self._config, "auth", None)
        _pp_cfg = getattr(_auth_cfg, "password_policy", None)
        _sec_cfg = getattr(_auth_cfg, "security", None)
        _mfa_cfg = getattr(_auth_cfg, "mfa", None)
        _email_verif_cfg = getattr(_auth_cfg, "email_verification", None)
        _email_otp_cfg = getattr(_auth_cfg, "email_otp", None)

        # ── AdminAuditLogService — DI-wired via @inject ───────────────────
        container.singleton(AdminAuditLogServiceProtocol, AdminAuditLogService)

        # ── AdminPasswordPolicyService — pre-built from config ────────────
        # Rule evaluation delegates to lexigram-auth's PasswordPolicy;
        # the admin service keeps only the email-containment rule + the
        # admin violation/message contract.
        from lexigram.auth import PasswordPolicy

        container.singleton(
            AdminPasswordPolicyServiceProtocol,
            AdminPasswordPolicyService(
                policy=PasswordPolicy(
                    min_length=getattr(_pp_cfg, "min_length", 12),
                    max_length=getattr(_pp_cfg, "max_length", 128),
                    require_uppercase=getattr(_pp_cfg, "require_uppercase", True),
                    require_lowercase=getattr(_pp_cfg, "require_lowercase", True),
                    require_digits=getattr(_pp_cfg, "require_digit", True),
                    require_special=getattr(_pp_cfg, "require_special", True),
                    prevent_common=getattr(_pp_cfg, "reject_common_passwords", True),
                ),
                reject_containing_email=getattr(
                    _pp_cfg, "reject_containing_email", True
                ),
            ),
        )

        # ── AdminCsrfService — pre-built from config ──────────────────────
        _session_secret: str = getattr(
            _auth_cfg, "session_secret", "change-me-in-production"
        )
        if isinstance(_session_secret, SecretStr):
            _session_secret = _session_secret.get_secret_value()
        # Token lifetime aligns with session idle TTL (AUTH-08)
        _csrf_lifetime: int = getattr(_auth_cfg, "idle_timeout", 3600)
        container.singleton(
            AdminCsrfServiceProtocol,
            AdminCsrfService(secret=_session_secret, token_lifetime=_csrf_lifetime),
        )

        # ── AdminSessionService — @inject subclass to pass config lifetimes ──
        # Follows the same pattern as _AdminSessionCookieBackend: a thin
        # @inject-decorated inner class captures config values from the
        # closure while letting the container inject SessionRepositoryProtocol.
        _session_lifetime: int = getattr(_auth_cfg, "session_lifetime", 86400)
        _idle_timeout: int = getattr(_auth_cfg, "idle_timeout", 3600)
        _fingerprint_secret: str = getattr(
            _auth_cfg, "session_secret", "change-me-in-production"
        )
        if isinstance(_fingerprint_secret, SecretStr):
            _fingerprint_secret = _fingerprint_secret.get_secret_value()

        @inject
        class _AdminSessionServiceConfigured(AdminSessionService):
            """Admin-scoped SessionService with config-driven lifetimes."""

            def __init__(
                self,
                session_repo: SessionRepositoryProtocol,
            ) -> None:
                super().__init__(
                    session_repo=session_repo,
                    session_lifetime=_session_lifetime,
                    idle_timeout=_idle_timeout,
                    fingerprint_secret=_fingerprint_secret,
                )

        container.singleton(AdminSessionServiceProtocol, _AdminSessionServiceConfigured)

        # ── AdminLoginAttemptService — DI-wired; cache wired in boot() ────
        # The @inject decorator resolves attempt_store and lockout_store from
        # the container. CacheBackendProtocol is optional (defaults to None);
        # it is wired post-registration in boot() when cache is available.
        container.singleton(AdminLoginAttemptServiceProtocol, AdminLoginAttemptService)

        # ── AdminAuthService — DI-wired orchestrator ──────────────────────
        # The @inject decorator resolves all store/service deps from the
        # container; mfa_factor comes from config via the closure.

        @inject
        class _AdminAuthServiceConfigured(AdminAuthService):
            """Admin-scoped auth service with config-driven factor selection."""

            def __init__(
                self,
                user_store: AdminUserStoreProtocol,
                attempt_service: AdminLoginAttemptServiceProtocol,
                audit_service: AdminAuditLogServiceProtocol,
                session_service: AdminSessionServiceProtocol,
                mfa_service: AdminMfaServiceProtocol | None = None,
                email_verification_service: AdminEmailVerificationServiceProtocol
                | None = None,
                email_otp_service: AdminEmailOtpServiceProtocol | None = None,
            ) -> None:
                super().__init__(
                    user_store=user_store,
                    attempt_service=attempt_service,
                    audit_service=audit_service,
                    session_service=session_service,
                    mfa_service=mfa_service,
                    email_verification_service=email_verification_service,
                    email_otp_service=email_otp_service,
                    mfa_factor=getattr(_mfa_cfg, "factor", "totp"),
                )

        container.singleton(AdminAuthServiceProtocol, _AdminAuthServiceConfigured)

        # ── AdminPasswordResetService — DI-wired orchestrator ─────────────
        # Resolves user_store, token_store, audit, auth, and policy services
        # from the container. hasher and notification_service stay optional:
        # the hasher falls back to lexigram-auth's PasswordHasher at runtime,
        # and notifications are skipped when no service is bound.
        container.singleton(
            AdminPasswordResetServiceProtocol, AdminPasswordResetService
        )

        # ── AdminMfaService — @inject subclass captures config values ────
        # Follows the _AdminSessionServiceConfigured pattern: the inner class
        # passes MFA config from the closure while the container injects the
        # store and audit service.
        from lexigram.admin.auth.services.mfa_service import AdminMfaService
        from lexigram.admin.auth.store.mfa_sql import AdminMfaSqlStore
        from lexigram.admin.config import AdminMfaConfig

        container.singleton(AdminMfaStoreProtocol, AdminMfaSqlStore)

        @inject
        class _AdminMfaServiceConfigured(AdminMfaService):
            """Admin-scoped MFA service with config-driven settings."""

            def __init__(
                self,
                store: AdminMfaStoreProtocol,
                audit_service: AdminAuditLogServiceProtocol,
            ) -> None:
                super().__init__(
                    config=_mfa_cfg or AdminMfaConfig(),
                    store=store,
                    audit_service=audit_service,
                )

        container.singleton(AdminMfaServiceProtocol, _AdminMfaServiceConfigured)

        # ── Email verification + email OTP — configured subclasses ────────
        # Notification service is registered as a concrete singleton so the
        # email services can inject it; it no-ops when no mailer is bound
        # (fail-open for verification, Err for OTP delivery).
        from lexigram.admin.auth.services.email_otp_service import AdminEmailOtpService
        from lexigram.admin.auth.services.email_verification_service import (
            AdminEmailVerificationService,
        )
        from lexigram.admin.auth.store.email_otp_sql import AdminEmailOtpSqlStore
        from lexigram.admin.auth.store.email_verification_sql import (
            AdminEmailVerificationSqlStore,
        )
        from lexigram.admin.config import (
            AdminEmailOtpConfig,
            AdminEmailVerificationConfig,
        )

        container.singleton(AdminNotificationService, AdminNotificationService)

        container.singleton(
            AdminEmailVerificationStoreProtocol, AdminEmailVerificationSqlStore
        )
        container.singleton(AdminEmailOtpStoreProtocol, AdminEmailOtpSqlStore)

        @inject
        class _AdminEmailVerificationServiceConfigured(AdminEmailVerificationService):
            """Admin-scoped email verification service with config-driven settings."""

            def __init__(
                self,
                store: AdminEmailVerificationStoreProtocol,
                notification_service: AdminNotificationService | None = None,
                audit_service: AdminAuditLogServiceProtocol | None = None,
            ) -> None:
                super().__init__(
                    config=_email_verif_cfg or AdminEmailVerificationConfig(),
                    store=store,
                    notification_service=notification_service,
                    audit_service=audit_service,
                )

        container.singleton(
            AdminEmailVerificationServiceProtocol,
            _AdminEmailVerificationServiceConfigured,
        )

        @inject
        class _AdminEmailOtpServiceConfigured(AdminEmailOtpService):
            """Admin-scoped email OTP service with config-driven settings."""

            def __init__(
                self,
                store: AdminEmailOtpStoreProtocol,
                notification_service: AdminNotificationService | None = None,
                audit_service: AdminAuditLogServiceProtocol | None = None,
            ) -> None:
                super().__init__(
                    config=_email_otp_cfg or AdminEmailOtpConfig(),
                    store=store,
                    notification_service=notification_service,
                    audit_service=audit_service,
                )

        container.singleton(
            AdminEmailOtpServiceProtocol, _AdminEmailOtpServiceConfigured
        )

        # ── AdminRoleService — DI-wired RBAC orchestrator ────────────────
        # The @inject decorator resolves role_store from the container.
        # authorization_service and audit_service are optional (None when
        # unbound — the service skips mirror/audit, fail open).
        from lexigram.admin.rbac.protocols import (
            AdminRoleServiceProtocol,
            AdminRoleStoreProtocol,
        )
        from lexigram.admin.rbac.role_service import AdminRoleService
        from lexigram.admin.rbac.roles_sql import AdminRoleSqlStore

        container.singleton(AdminRoleStoreProtocol, AdminRoleSqlStore)
        container.singleton(AdminRoleServiceProtocol, AdminRoleService)

        logger.debug("admin_auth.new_services_registered")

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
                await _store.ensure_schema()  # type: ignore[attr-defined]
            except Exception as e:
                logger.exception(f"admin_auth.schema_init_failed: {e}")  # noqa: BLE001
                logger.warning(
                    "admin_auth.schema_init_failed",
                    protocol=str(_store_protocol),
                )

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
