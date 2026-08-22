"""JSON API for the API-keys console — management + machine endpoint."""

from __future__ import annotations

from starlette.requests import Request

from lexigram.auth.authn.apikeys import APIKeyManager
from lexigram.auth.authn.services import AuthenticationService
from lexigram.auth.session.cookie_backend import SessionCookieBackend
from lexigram.logging import get_logger
from lexigram.serialization import loads as json_loads
from lexigram.web import Controller, JSONResponse, get, post

logger = get_logger(__name__)


def _error(message: str, status: int) -> JSONResponse:
    return JSONResponse({"error": message}, status_code=status)


class KeysApiController(Controller):
    """Session-guarded key management + X-API-Key machine endpoint."""

    def __init__(
        self,
        authentication: AuthenticationService,
        cookies: SessionCookieBackend,
        manager: APIKeyManager,
    ) -> None:
        self._authentication = authentication
        self._cookies = cookies
        self._manager = manager

    async def _require_session(self, request: Request) -> Any | None:
        return await self._cookies.authenticate(request)

    @post("/api/login")
    async def login(self, request: Request) -> JSONResponse:
        data = json_loads(await request.body())
        user = await self._authentication.authenticate_user(
            email=str(data.get("email", "")),
            password=str(data.get("password", "")),
        )
        if user.is_err():
            return _error(str(user.unwrap_err()), 401)
        authenticated = user.unwrap()
        response = JSONResponse({"ok": True, "user": {"email": authenticated.email}})
        await self._cookies.login(response, authenticated.user_id)
        return response

    @post("/api/logout")
    async def logout(self, request: Request) -> JSONResponse:
        response = JSONResponse({"ok": True})
        await self._cookies.logout(request, response)
        return response

    @get("/api/keys")
    async def list_keys(self, request: Request) -> JSONResponse:
        user = await self._require_session(request)
        if user is None:
            return _error("not authenticated", 401)
        keys = await self._manager.list_keys(user.user_id)
        return JSONResponse(
            {
                "keys": [
                    {
                        "key_id": k.key_id,
                        "name": k.name,
                        "prefix": k.prefix,
                        "scopes": list(k.scopes),
                        "expires_at": k.expires_at.isoformat()
                        if k.expires_at
                        else None,
                    }
                    for k in keys
                ]
            }
        )

    @post("/api/keys/create")
    async def create_key(self, request: Request) -> JSONResponse:
        """Issue a key; the raw secret appears exactly once in this response."""
        user = await self._require_session(request)
        if user is None:
            return _error("not authenticated", 401)
        data = json_loads(await request.body())
        raw_key, api_key = await self._manager.create_key(
            user_id=user.user_id,
            name=str(data.get("name", "unnamed")),
            scopes=list(data.get("scopes") or ["read"]),
            expires_days=None,
        )
        logger.info("api_key_created", key_id=api_key.key_id, prefix=api_key.prefix)
        return JSONResponse(
            {"raw_key": raw_key, "key_id": api_key.key_id, "prefix": api_key.prefix}
        )

    @post("/api/keys/{key_id}/revoke")
    async def revoke_key(self, request: Request, key_id: str) -> JSONResponse:
        revoked = await self._manager.revoke_key(key_id)
        if not revoked:
            return _error("unknown key", 404)
        return JSONResponse({"ok": True})

    @get("/api/me")
    async def me(self, request: Request) -> JSONResponse:
        """Machine authentication via ``X-API-Key`` header."""
        raw_key = request.headers.get("X-API-Key", "")
        if not raw_key:
            return _error("missing X-API-Key header", 401)
        api_key = await self._manager.validate_key(raw_key)
        if api_key is None:
            return _error("invalid api key", 401)
        return JSONResponse(
            {
                "user_id": api_key.user_id,
                "name": api_key.name,
                "scopes": list(api_key.scopes),
            }
        )


__all__ = ["KeysApiController"]
