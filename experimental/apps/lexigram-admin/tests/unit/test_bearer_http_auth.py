import pytest
from types import SimpleNamespace
from pydantic import SecretStr

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from lexigram.admin.auth.guards import AuthGuardMiddleware
import httpx
from httpx import ASGITransport
import lexigram.auth as la
from lexigram.auth.authn.jwt import JWTTokenManager


async def _async_get_user_by_id(uid):
    return SimpleNamespace(id=uid, email=f"{uid}@example.com")


@pytest.mark.asyncio
async def test_bearer_token_http_auth_accepts_hs256_token(monkeypatch):
    ap = la.AuthenticationProvider()
    class DummyCache:
        async def get(self, *a, **kw): return None
        async def set(self, *a, **kw): pass
        async def delete(self, *a, **kw): pass
        async def exists(self, *a, **kw): return False
    ap.token_manager = JWTTokenManager(
        current_key_id="test-key",
        keys={"test-key": SecretStr("a-test-secret-that-is-at-least-32-chars-long")},
        cache_service=DummyCache(),
    )
    ap.user_store = SimpleNamespace(get_user_by_id=_async_get_user_by_id)

    # Create a valid HS256 access token
    user = SimpleNamespace(
        user_id="user-hs-1",
        username="user-hs-1",
        name="user-hs-1",
        email="user-hs-1@example.com",
        roles=[],
        permissions=[],
    )
    token = ap.token_manager.create_access_token(user)

    # Protected route
    async def protected(request):
        user = getattr(request.state, "user", None)
        if not user:
            return JSONResponse({"authenticated": False}, status_code=401)
        return JSONResponse(
            {"authenticated": True, "email": getattr(user, "email", None)},
        )

    app = Starlette(routes=[Route("/protected", protected, methods=["GET"])])
    from lexigram.admin.auth.guards import GuardConfig

    config = GuardConfig(allow_bearer_tokens=True)
    app.add_middleware(AuthGuardMiddleware, auth_provider=ap, config=config)


    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        resp = await client.get("/protected", headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 200, resp.text
    assert resp.json().get("authenticated") is True
    assert resp.json().get("email") == "user-hs-1@example.com"


@pytest.mark.asyncio
async def test_bearer_token_http_auth_rejects_invalid_alg(monkeypatch, caplog):
    ap = la.AuthenticationProvider()
    class DummyCache:
        async def get(self, *a, **kw): return None
        async def set(self, *a, **kw): pass
        async def delete(self, *a, **kw): pass
    ap.token_manager = JWTTokenManager(
        current_key_id="test-key",
        keys={"test-key": SecretStr("a-test-secret-that-is-at-least-32-chars-long")},
        cache_service=DummyCache(),
    )
    ap.user_store = SimpleNamespace(get_user_by_id=_async_get_user_by_id)

    # Craft a token whose header declares RS256 (not accepted by HS256 server)
    header_b64 = "eyJhbGciOiJSUzI1NiIsImtpZCI6ImtleTEifQ"
    payload_b64 = "eyJzdWIiOiJ1c2VyLVJTMTEiLCJ0eXBlIjoiYWNjZXNzIn0"
    fake_token = f"{header_b64}.{payload_b64}.invalidsig"

    # Protected route
    async def protected(request):
        user = getattr(request.state, "user", None)
        if not user:
            return JSONResponse({"authenticated": False}, status_code=401)
        return JSONResponse(
            {"authenticated": True, "email": getattr(user, "email", None)},
        )

    app = Starlette(routes=[Route("/protected", protected, methods=["GET"])])
    from lexigram.admin.auth.guards import GuardConfig

    config = GuardConfig(allow_bearer_tokens=True)
    app.add_middleware(AuthGuardMiddleware, auth_provider=ap, config=config)

    caplog.clear()
    with caplog.at_level("WARNING"):
        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            resp = await client.get("/protected", headers={"Authorization": f"Bearer {fake_token}"})

    assert resp.status_code == 401
    assert resp.json().get("authenticated") is False
