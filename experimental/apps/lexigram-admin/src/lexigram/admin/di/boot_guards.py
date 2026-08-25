"""Mandatory boot-time service resolution guards for the admin provider."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.contracts.core.di import ContainerResolverProtocol

_log = get_logger(__name__)


class AdminBootGuardsMixin:
    """Fail-loud boot guards for mandatory admin middleware services.

    Host attributes are provided by ``AdminProvider``.
    """

    # Host attributes populated by _resolve_mandatory_boot_services().
    _config: Any
    _csrf_service: Any
    _user_store: Any
    _session_service: Any
    _authorizer: Any
    _authorizer_service: Any

    async def _resolve_mandatory_boot_services(
        self,
        container: ContainerResolverProtocol,
    ) -> None:
        """Resolve every service the admin middleware stack cannot run without.

        Resolution order is part of the boot contract and must not change:
        CSRF → setup-token guard → auth-middleware dependencies → request
        authorizer → per-resource authorizer service. Each failure is fatal
        (RuntimeError) so a misconfigured admin fails application startup
        instead of silently degrading security.

        Args:
            container: The DI resolver for mandatory service resolution.

        Raises:
            RuntimeError: If any mandatory service cannot be resolved or the
                setup token guard is not satisfied.
        """
        # CSRF is mandatory. Resolve here, not in mount_to_app(): boot
        # failures propagate through the orchestrator and fail application
        # startup, whereas mount_to_app() exceptions are caught by the web
        # provider's RouteSetup and logged, silently skipping the admin mount.
        from lexigram.admin.auth.protocols import AdminCsrfServiceProtocol

        try:
            self._csrf_service = await container.resolve(
                AdminCsrfServiceProtocol,
                bypass_visibility=True,
            )
        except Exception as exc:  # noqa: BLE001 — re-raised as fatal below
            _log.error(
                "admin.csrf_service_resolution_failed",
                error=str(exc),
                error_type=type(exc).__name__,
            )
            raise RuntimeError(
                "CSRF service could not be resolved; refusing to boot admin "
                "without CSRF enforcement"
            ) from exc

        # The first-run wizard must be gated: boot refuses to start without
        # a setup token (admin.auth.security.setup_token, legacy env var
        # ADMIN_SETUP_TOKEN, or nested LEX_ADMIN_AUTH__SECURITY__SETUP_TOKEN)
        # unless the operator explicitly opts out with
        # admin.auth.security.setup_token_optin_unsafe=true for local/
        # ephemeral environments only.
        if (
            not self._config.auth.security.setup_token
            and not self._config.auth.security.setup_token_optin_unsafe
        ):
            raise RuntimeError(
                "Refusing to boot admin without a setup token: set "
                "ADMIN_SETUP_TOKEN (or config admin.auth.security.setup_token, "
                "env LEX_ADMIN_AUTH__SECURITY__SETUP_TOKEN), or explicitly opt "
                "out for local/ephemeral environments with "
                "admin.auth.security.setup_token_optin_unsafe=true"
            )

        # AdminAuthMiddleware's dependencies are mandatory — the middleware
        # that actually enforces identity must not be silently dropped by a
        # mount-time resolution failure (RouteSetup swallows mount exception
        # and skips the admin mount entirely). Resolve at boot with the same
        # fail-loud shape as the CSRF block above.
        from lexigram.admin.auth.protocols import AdminSessionServiceProtocol
        from lexigram.admin.auth.store.protocols import AdminUserStoreProtocol

        try:
            self._user_store = await container.resolve(
                AdminUserStoreProtocol,
                bypass_visibility=True,
            )
            self._session_service = await container.resolve(
                AdminSessionServiceProtocol,
                bypass_visibility=True,
            )
        except Exception as exc:  # noqa: BLE001 — re-raised as fatal below
            _log.error(
                "admin.auth_middleware_dependencies_resolution_failed",
                error=str(exc),
                error_type=type(exc).__name__,
            )
            raise RuntimeError(
                "AdminAuthMiddleware dependencies could not be resolved; "
                "refusing to boot admin without session validation"
            ) from exc

        # AdminAuthorizationMiddleware's authorizer is mandatory — RBAC
        # enforcement must never silently degrade at startup.
        from lexigram.admin.middleware.authorization import (
            RequestAuthorizerProtocol,
        )

        try:
            self._authorizer = await container.resolve(
                RequestAuthorizerProtocol,
                bypass_visibility=True,
            )
        except Exception as exc:  # noqa: BLE001 — re-raised as fatal below
            _log.error(
                "admin.authorization_middleware_dependency_resolution_failed",
                error=str(exc),
                error_type=type(exc).__name__,
            )
            raise RuntimeError(
                "AdminAuthorizationMiddleware's authorizer could not be "
                "resolved; refusing to boot admin without RBAC enforcement"
            ) from exc

        from lexigram.contracts.auth import AuthorizerProtocol

        try:
            self._authorizer_service = await container.resolve(
                AuthorizerProtocol,
                bypass_visibility=True,
            )
        except Exception as exc:  # noqa: BLE001 — re-raised as fatal below
            _log.error(
                "admin.authorizer_service_resolution_failed",
                error=str(exc),
                error_type=type(exc).__name__,
            )
            raise RuntimeError(
                "AuthorizerProtocol could not be resolved; refusing to boot "
                "admin without a per-resource permission source for search"
            ) from exc


__all__ = ["AdminBootGuardsMixin"]
