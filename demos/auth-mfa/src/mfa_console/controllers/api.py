"""JSON API for the MFA console — no HTML lives here."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from mfa_console.repository.session_repository import InMemorySessionRepository
from starlette.requests import Request

from lexigram.auth.authn.services import AuthenticationService
from lexigram.auth.authn.user_service import UserService
from lexigram.auth.mfa.manager import MFAManager
from lexigram.auth.session.cookie_backend import SessionCookieBackend
from lexigram.logging import get_logger
from lexigram.primitives import clock
from lexigram.serialization import loads as json_loads
from lexigram.web import Controller, JSONResponse, get, post

logger = get_logger(__name__)

PENDING_COOKIE = "mfa_pending"
PENDING_TTL_SECONDS = 300
MAX_CHALLENGE_ATTEMPTS = 3


def _error(message: str, status: int) -> JSONResponse:
    return JSONResponse({"error": message}, status_code=status)


def _mfa_enabled(user: Any) -> bool:
    profile_mfa = (getattr(user, "profile", {}) or {}).get("mfa") or {}
    return bool(profile_mfa.get("enabled"))


class MfaApiController(Controller):
    """Login + TOTP challenge/enroll/disable API for the demo UI."""

    def __init__(
        self,
        authentication: AuthenticationService,
        users: UserService,
        mfa: MFAManager,
        cookies: SessionCookieBackend,
        sessions: InMemorySessionRepository,
    ) -> None:
        self._authentication = authentication
        self._users = users
        self._mfa = mfa
        self._cookies = cookies
        self._sessions = sessions
        self._attempts: dict[str, int] = {}

    async def _user_from_pending(self, request: Request) -> Any | None:
        pending_id = request.cookies.get(PENDING_COOKIE)
        if not pending_id:
            return None
        row = await self._sessions.find_active(pending_id)
        if row is None:
            return None
        user = await self._users.get_user(row["user_id"])
        if user is None or not _mfa_enabled(user):
            return None
        return user, pending_id, row

    @post("/api/login")
    async def login(self, request: Request) -> JSONResponse:
        """Password step; MFA-enabled users get a pending challenge cookie."""
        data = json_loads(await request.body())
        email = str(data.get("email", ""))
        password = str(data.get("password", ""))

        result = await self._authentication.authenticate_user(email, password)
        if result.is_err():
            logger.warning("login_failed", email=email)
            return _error(str(result.unwrap_err()), 401)

        user = result.unwrap()
        if not _mfa_enabled(user):
            response = JSONResponse({"ok": True, "mfa_required": False})
            await self._cookies.login(response, user.user_id)
            return response

        pending_id = f"pending-{user.user_id}-{clock.now().timestamp()}"
        await self._sessions.insert(
            {
                "session_id": pending_id,
                "user_id": user.user_id,
                "device_id": "pre-auth",
                "expires_at": clock.now() + timedelta(seconds=PENDING_TTL_SECONDS),
            }
        )
        response = JSONResponse({"ok": True, "mfa_required": True})
        response.set_cookie(
            key=PENDING_COOKIE,
            value=pending_id,
            max_age=PENDING_TTL_SECONDS,
            httponly=True,
            samesite="lax",
        )
        logger.info("mfa_challenge_issued", user_id=user.user_id)
        return response

    @post("/api/mfa/challenge")
    async def challenge(self, request: Request) -> JSONResponse:
        """Verify a TOTP/backup code and upgrade to a full session."""
        resolved = await self._user_from_pending(request)
        if resolved is None:
            return _error("no pending challenge", 401)
        user, pending_id, _row = resolved

        data = json_loads(await request.body())
        code = str(data.get("code", ""))

        if not await self._mfa.verify_totp(user.user_id, code):
            attempts = self._attempts.get(pending_id, 0) + 1
            self._attempts[pending_id] = attempts
            if attempts >= MAX_CHALLENGE_ATTEMPTS:
                await self._sessions.revoke(pending_id)
                response = JSONResponse(
                    {"error": "too many attempts; log in again"}, status_code=401
                )
                response.delete_cookie(PENDING_COOKIE)
                return response
            return _error("invalid code", 401)

        self._attempts.pop(pending_id, None)
        await self._sessions.revoke(pending_id)
        response = JSONResponse({"ok": True})
        await self._cookies.login(response, user.user_id)
        logger.info("mfa_challenge_passed", user_id=user.user_id)
        return response

    @get("/api/me")
    async def me(self, request: Request) -> JSONResponse:
        user = await self._cookies.authenticate(request)
        if user is None:
            return _error("not authenticated", 401)
        return JSONResponse(
            {"email": user.email, "name": user.name, "mfa_enabled": _mfa_enabled(user)}
        )

    @get("/api/mfa/status")
    async def mfa_status(self, request: Request) -> JSONResponse:
        user = await self._cookies.authenticate(request)
        if user is None:
            return _error("not authenticated", 401)
        profile_mfa = (user.profile or {}).get("mfa") or {}
        remaining = len(profile_mfa.get("backup_codes") or [])
        return JSONResponse(
            {"enabled": _mfa_enabled(user), "backup_codes_left": remaining}
        )

    @post("/api/mfa/enroll")
    async def enroll(self, request: Request) -> JSONResponse:
        """Enable TOTP; returns secret + provisioning URI + backup codes once."""
        user = await self._cookies.authenticate(request)
        if user is None:
            return _error("not authenticated", 401)
        if _mfa_enabled(user):
            return _error("MFA already enabled", 400)

        secret, provisioning_uri, backup_codes = await self._mfa.enable_totp(
            user.user_id, issuer="auth-mfa-demo"
        )
        logger.info("mfa_enrolled", user_id=user.user_id)
        return JSONResponse(
            {
                "secret": secret,
                "provisioning_uri": provisioning_uri,
                "backup_codes": backup_codes,
            }
        )

    @post("/api/mfa/disable")
    async def disable(self, request: Request) -> JSONResponse:
        """Disable TOTP after re-verifying the password."""
        user = await self._cookies.authenticate(request)
        if user is None:
            return _error("not authenticated", 401)

        data = json_loads(await request.body())
        recheck = await self._authentication.authenticate_user(
            user.email, str(data.get("password", ""))
        )
        if recheck.is_err():
            return _error(str(recheck.unwrap_err()), 401)

        disabled = await self._mfa.disable_totp(user.user_id)
        return JSONResponse({"ok": True, "disabled": disabled})


__all__ = ["MfaApiController"]
