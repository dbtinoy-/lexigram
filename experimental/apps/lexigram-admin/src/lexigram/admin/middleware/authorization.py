"""Request-entry RBAC middleware (AUTH-09, AUTH-18).

Checks every non-public request against an authorizer before dispatching
to the handler.  Returns 401 for anonymous users, 403 for authorization
denials, and is HTMX-aware.
"""

from __future__ import annotations

from collections.abc import Collection
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse, Response

from lexigram.admin.observability.admin_metrics import AdminMetrics
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from starlette.types import ASGIApp

logger = get_logger(__name__)


def _public_paths(admin_prefix: str) -> tuple[str, ...]:
    """Public paths relative to the configured admin mount prefix."""
    prefix = admin_prefix.rstrip("/")
    return (
        f"{prefix}/login",
        f"{prefix}/setup",
        f"{prefix}/static",
        f"{prefix}/health",
        # Standalone pre-session flows (own CSRF + guest handling):
        f"{prefix}/login/2fa",
        f"{prefix}/verify-email",
        f"{prefix}/password-reset",
        f"{prefix}/register",
        # CSP violation report sink — browsers post pre-auth, no session
        # (doc 30). Exact/boundary matching cannot leak the /csp-reports
        # viewer, which stays authorized.
        f"{prefix}/security/csp-report",
    )


class DefaultRequestAuthorizer:
    """Default request-entry authorizer — authenticated users pass (fail-closed on identity)."""

    async def authorize_request(self, user: object, request: Request) -> bool:
        del request  # unused
        return getattr(user, "user_id", None) is not None


@runtime_checkable
class RequestAuthorizerProtocol(Protocol):
    """Protocol for request-level authorization.

    Concrete implementations (e.g. PiccolinaAdminAuthPolicy) implement
    ``authorize_request`` alongside the union ``AuthorizerProtocol`` methods.
    """

    async def authorize_request(self, user: object, request: Request) -> bool:
        """Return True if the user is authorized to access the request."""
        ...


class AdminAuthorizationMiddleware(BaseHTTPMiddleware):
    """Middleware that enforces request-entry authorization."""

    def __init__(
        self,
        app: ASGIApp,
        authorizer: RequestAuthorizerProtocol,
        metrics: AdminMetrics | None = None,
        admin_prefix: str | None = None,
        permission_authorizer: Any | None = None,
        resource_names: Collection[str] | None = None,
        super_admin_role: str | None = None,
    ) -> None:
        super().__init__(app)
        self._authorizer = authorizer
        self._permission_authorizer = permission_authorizer
        self._resource_names = resource_names
        self._metrics = metrics or AdminMetrics(None)
        self._admin_prefix = (admin_prefix or "/admin").rstrip("/")
        self._public_paths = _public_paths(self._admin_prefix)
        self._super_admin_role = super_admin_role

    def _is_super_admin(self, user: object) -> bool:
        """Return True for superusers and holders of the super-admin role.

        The permission engine only recognizes ``is_superuser`` and the
        hardcoded ``admin``/``superuser`` roles; the configured
        ``AdminRbacConfig.super_admin_role`` (default ``"superadmin"`` — the
        role the setup wizard grants the first account) must also bypass
        per-resource capability checks, otherwise a fresh install's only
        account is denied every resource route.
        """
        if getattr(user, "is_superuser", False) is True:
            return True
        if not self._super_admin_role:
            return False
        from lexigram.admin.rbac.super_admin import is_super_admin

        return is_super_admin(user, self._super_admin_role)

    @staticmethod
    def _resource_action(path: str, admin_prefix: str) -> tuple[str, str] | None:
        """Extract a canonical resource/action pair from an admin route."""
        relative = path.removeprefix(admin_prefix).strip("/")
        parts = relative.split("/") if relative else []
        if not parts or not parts[0]:
            return None

        resource = parts[0]
        if len(parts) == 1:
            return resource, "view"

        operation = parts[1]
        if operation == "create":
            return resource, "create"
        if operation == "bulk":
            # The generic POST endpoint also serves non-destructive actions
            # such as export. The handler applies the action-specific delete
            # or update check after parsing the submitted action.
            return resource, "view"
        if operation in {
            "bulk-delete-confirm",
            "bulk-purge-confirm",
            "bulk-restore-confirm",
        }:
            return (
                resource,
                "delete" if operation != "bulk-restore-confirm" else "update",
            )
        if operation in {"import-example", "import-report"}:
            return resource, "create"
        if operation == "relation-options":
            return resource, "view"
        if len(parts) >= 3:
            operation = parts[2]
        if operation in {"edit", "restore"}:
            return resource, "update"
        if operation in {"delete", "delete-confirm", "purge"}:
            return resource, "delete"
        if operation == "clone":
            return resource, "create"
        if operation == "permissions":
            return resource, "update"
        return resource, "view"

    async def _resource_capabilities(
        self,
        user: object,
        request: Request,
    ) -> dict[str, bool] | None:
        """Resolve CRUD capabilities and enforce the current route action."""
        service = self._permission_authorizer
        if service is None:
            return None

        route = self._resource_action(request.url.path, self._admin_prefix)
        if route is None:
            return None
        resource, action = route

        # Super admins hold every capability — never consult the permission
        # engine (which has no knowledge of the configured super-admin role).
        if self._is_super_admin(user):
            return {
                "can_view": True,
                "can_create": True,
                "can_update": True,
                "can_delete": True,
            }

        async def check(name: str, fallback: str | None = None) -> bool:
            method = getattr(service, name, None)
            if method is None and fallback:
                method = getattr(service, fallback, None)
            if method is None:
                return False
            try:
                if await method(user, resource):
                    return True
            except Exception:  # noqa: BLE001 — authorization must fail closed
                logger.exception(
                    "admin_authz.permission_check_failed",
                    resource=resource,
                    action=name,
                )
                return False
            # Canonical permission denied — honour deprecated aliases
            # (e.g. ``{resource}.read`` for view) during the migration
            # window, with a one-line deprecation warning (roadmap R6).
            return await self._legacy_alias_grant(
                service, user, resource, name.removeprefix("can_")
            )

        capabilities = {
            "can_view": await check("can_view"),
            "can_create": await check("can_create"),
            "can_update": await check("can_update", "can_edit"),
            "can_delete": await check("can_delete"),
        }
        if not capabilities.get(
            {
                "view": "can_view",
                "create": "can_create",
                "update": "can_update",
                "delete": "can_delete",
            }.get(action, "can_view"),
            False,
        ):
            return None
        return capabilities

    @staticmethod
    async def _legacy_alias_grant(
        service: object,
        user: object,
        resource: str,
        action: str,
    ) -> bool:
        """Return True when a deprecated permission alias grants *action*.

        Consults ``lexigram.admin.auth.permission_scheme`` for the aliases
        (``read``/``list`` → view, ``edit`` → update) and checks each via the
        service's generic ``can_execute_action`` when available. A grant via
        an alias logs a one-line ``admin_authz.legacy_permission_grant``
        deprecation warning (deduplicated per process). Fails closed.
        """
        from lexigram.admin.auth.permission_scheme import (
            legacy_aliases_for,
            warn_legacy_grant,
        )

        aliases = legacy_aliases_for(action)
        if not aliases:
            return False
        check_action = getattr(service, "can_execute_action", None)
        if check_action is None:
            return False
        for alias in aliases:
            try:
                granted = bool(await check_action(user, resource, alias))
            except Exception:  # noqa: BLE001 — authorization must fail closed
                logger.exception(
                    "admin_authz.legacy_alias_check_failed",
                    resource=resource,
                    alias=alias,
                )
                continue
            if granted:
                warn_legacy_grant(resource, alias)
                return True
        return False

    def _is_public_path(self, path: str) -> bool:
        """Match public endpoints exactly or beneath their path boundary."""
        return any(
            path == public or path.startswith(f"{public}/")
            for public in self._public_paths
        )

    async def dispatch(self, request: Request, call_next: Any) -> Any:
        """Check authorization before dispatching to the next handler."""
        path = request.url.path
        if self._is_public_path(path):
            return await call_next(request)

        user = getattr(request.state, "user", None)
        if user is None:
            logger.info(
                "admin_authz.unauthenticated",
                path=path,
            )
            return self._unauthenticated(request)

        if not await self._authorizer.authorize_request(user, request):
            logger.info(
                "admin_authz.denied",
                user_id=getattr(user, "user_id", "unknown"),
                path=path,
            )
            resource = path.split("/")[2] if len(path.split("/")) > 2 else "unknown"
            self._metrics.record_authz_denied(resource=resource)
            return self._forbidden(request)

        # Enforce resource CRUD capability at the request boundary as well as
        # the broad request policy. This keeps direct ResourceHandler routes
        # from relying only on hidden UI actions for authorization.
        route = self._resource_action(path, self._admin_prefix)
        is_known_resource = route is not None and (
            self._resource_names is None or route[0] in self._resource_names
        )
        if self._permission_authorizer is not None and is_known_resource:
            capabilities = await self._resource_capabilities(user, request)
            if capabilities is None:
                # Reuse `route` rather than recomputing: is_known_resource
                # already proved it is not None, whereas a fresh call is
                # typed Optional and indexing it is unguarded.
                assert route is not None
                resource = route[0]
                logger.info(
                    "admin_authz.resource_denied",
                    user_id=getattr(user, "user_id", "unknown"),
                    resource=resource,
                    path=path,
                )
                self._metrics.record_authz_denied(resource=resource)
                return self._forbidden(request)
            request.state.permissions = capabilities

        return await call_next(request)

    def _unauthenticated(
        self,
        request: Request,
    ) -> JSONResponse | RedirectResponse | Response:
        """Redirect to login, with HX-Redirect for HTMX requests.

        HTMX swaps responses into the current page, so a plain redirect
        would render the login page inside the target component. The
        HX-Redirect header forces a full browser navigation instead.
        """
        login_url = f"{self._public_paths[0]}?next={request.url.path}"
        if request.headers.get("HX-Request") == "true":
            response = Response(status_code=200)
            response.headers["HX-Redirect"] = login_url
            return response
        return RedirectResponse(url=login_url, status_code=302)

    def _forbidden(self, request: Request) -> Response:
        """Return 403, content-negotiated for the caller (roadmap R7).

        - Browser navigations get the styled "Access Denied" page.
        - HTMX requests get an empty 403 with an ``HX-Trigger`` toast so the
          denial is visible without swapping raw JSON into the page.
        - API callers keep the machine-readable JSON body.
        """
        from lexigram.admin.middleware._negotiation import (
            error_page_meta,
            prefers_html,
            styled_error_response,
        )

        if request.headers.get("HX-Request") == "true":
            from lexigram.serialization import dumps_str

            title, message, _icon = error_page_meta(403)
            response = Response(status_code=403)
            response.headers["HX-Trigger"] = dumps_str(
                {"showMessage": {"message": f"{title}: {message}", "type": "error"}},
            )
            return response
        if prefers_html(request):
            return styled_error_response(403, self._admin_prefix)
        return JSONResponse(
            {"error": "forbidden", "path": request.url.path},
            status_code=403,
        )


__all__ = [
    "AdminAuthorizationMiddleware",
    "DefaultRequestAuthorizer",
    "RequestAuthorizerProtocol",
]
