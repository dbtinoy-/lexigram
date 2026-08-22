"""JSON API for the auth web demo — no HTML lives here."""

from __future__ import annotations

from auth_web.repository import InMemorySessionRepository
from auth_web.services.password_change import PasswordChangeService
from starlette.requests import Request
from starlette.responses import JSONResponse

from lexigram.auth.authn.schemas.requests import RegisterRequest
from lexigram.auth.authn.services import AuthenticationService
from lexigram.auth.authz.service import AuthorizationService
from lexigram.auth.session.cookie_backend import SessionCookieBackend
from lexigram.logging import get_logger
from lexigram.primitives import clock
from lexigram.serialization import loads as json_loads
from lexigram.web import Controller, get, post

logger = get_logger(__name__)


def _error(message: str, status: int) -> JSONResponse:
    return JSONResponse({"error": message}, status_code=status)


class AuthApiController(Controller):
    """Account lifecycle API consumed by the UI's vanilla-JS client."""

    def __init__(
        self,
        authentication: AuthenticationService,
        cookies: SessionCookieBackend,
        sessions: InMemorySessionRepository,
        authz: AuthorizationService,
        password_changes: PasswordChangeService,
    ) -> None:
        self._authentication = authentication
        self._cookies = cookies
        self._sessions = sessions
        self._authz = authz
        self._password_changes = password_changes

    @post("/api/register")
    async def register(self, request: Request) -> JSONResponse:
        """Create an account and start a session for it."""
        data = json_loads(await request.body())
        result = await self._authentication.register_user(
            RegisterRequest(
                name=str(data.get("name", "")),
                email=str(data.get("email", "")),
                password=str(data.get("password", "")),
                confirm_password=str(data.get("confirm_password", "")),
            )
        )
        if result.is_err():
            return _error(str(result.unwrap_err()), 400)

        user = result.unwrap()
        response = JSONResponse(
            {"ok": True, "user": {"email": user.email}}, status_code=201
        )
        await self._cookies.login(response, user.user_id)
        return response

    @post("/api/login")
    async def login(self, request: Request) -> JSONResponse:
        """Verify credentials and set the session cookie."""
        data = json_loads(await request.body())
        email = str(data.get("email", ""))
        password = str(data.get("password", ""))

        user = await self._authentication.authenticate_user(email, password)
        if user.is_err():
            logger.warning("login_failed", email=email)
            return _error(str(user.unwrap_err()), 401)

        authenticated = user.unwrap()
        response = JSONResponse(
            {
                "ok": True,
                "user": {
                    "user_id": authenticated.user_id,
                    "email": authenticated.email,
                    "name": authenticated.name,
                },
            }
        )
        await self._cookies.login(response, authenticated.user_id)
        return response

    @post("/api/logout")
    async def logout(self, request: Request) -> JSONResponse:
        """Invalidate the session cookie."""
        response = JSONResponse({"ok": True})
        await self._cookies.logout(request, response)
        return response

    @get("/api/me")
    async def me(self, request: Request) -> JSONResponse:
        """Return the session's identity, or 401 when anonymous."""
        user = await self._cookies.authenticate(request)
        if user is None:
            return _error("not authenticated", 401)
        return JSONResponse(
            {"user_id": user.user_id, "email": user.email, "name": user.name}
        )

    @get("/api/profile")
    async def profile(self, request: Request) -> JSONResponse:
        """Identity + fresh JWT claims + active sessions for this user."""
        user = await self._cookies.authenticate(request)
        if user is None:
            return _error("not authenticated", 401)

        token = self._authentication.create_token(user)
        verified = await self._authentication.verify_token(token.token)
        if verified.is_err():
            return _error(str(verified.unwrap_err()), 500)
        claims = verified.unwrap()

        sessions = await self._sessions.find_active_by_user(
            user.user_id, cutoff=clock.now()
        )

        # Effective permissions = explicit claims UNION role-derived patterns
        # (AuthorizationService expands inheritance for us).
        effective: set[str] = set(claims.permissions)
        for role in claims.roles:
            effective |= self._authz.get_role_permissions(role)

        return JSONResponse(
            {
                "user": {
                    "user_id": user.user_id,
                    "email": user.email,
                    "name": user.name,
                },
                "token_preview": token.token[:24] + "…",
                "claims": {
                    "roles": claims.roles,
                    "permissions": sorted(effective),
                    "key_id": claims.key_id,
                    "expires_at": claims.expires_at.isoformat(),
                    "token_type": claims.token_type,
                },
                "sessions": [
                    {
                        "session_id": row["session_id"],
                        "expires_at": row["expires_at"].isoformat()
                        if row.get("expires_at")
                        else None,
                    }
                    for row in sessions
                ],
            }
        )

    @post("/api/profile/password")
    async def change_password(self, request: Request) -> JSONResponse:
        """Change the session user's password (requires current password)."""
        user = await self._cookies.authenticate(request)
        if user is None:
            return _error("not authenticated", 401)

        data = json_loads(await request.body())
        result = await self._password_changes.change(
            user_id=user.user_id,
            current_password=str(data.get("current_password", "")),
            new_password=str(data.get("new_password", "")),
        )
        if result.is_err():
            return _error(str(result.unwrap_err()), 400)
        return JSONResponse({"ok": True})

    @post("/api/sessions/{session_id}/revoke")
    async def revoke_session(self, request: Request, session_id: str) -> JSONResponse:
        """Revoke one of the session user's active sessions."""
        user = await self._cookies.authenticate(request)
        if user is None:
            return _error("not authenticated", 401)

        rows = await self._sessions.find_active_by_user(
            user.user_id, cutoff=clock.now()
        )
        if session_id not in {row["session_id"] for row in rows}:
            return _error("unknown session", 404)

        await self._sessions.revoke(session_id)
        return JSONResponse({"ok": True})


__all__ = ["AuthApiController"]
