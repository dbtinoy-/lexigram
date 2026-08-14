from types import SimpleNamespace

import pytest
from starlette.applications import Starlette
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Route

from lexigram.admin.auth.guards import AuthGuardMiddleware


@pytest.mark.integration
@pytest.mark.asyncio
async def test_request_session_auth_integration_with_middleware():
    class FakeUserStore:
        async def get_user_by_id(self, user_id):
            return SimpleNamespace(id=user_id, email="session@int.com")

    auth_provider = SimpleNamespace(user_store=FakeUserStore())

    async def protected(request):
        user = getattr(request.state, "user", None)
        if not user:
            return JSONResponse({"authenticated": False}, status_code=401)
        return JSONResponse(
            {"authenticated": True, "email": getattr(user, "email", None)},
        )

    async def login(request):
        request.session["admin_user_id"] = "int-session-1"
        return JSONResponse({"ok": True})

    app = Starlette(
        routes=[
            Route("/admin/login", login, methods=["GET"]),
            Route("/admin/protected", protected, methods=["GET"]),
        ]
    )
    app.add_middleware(AuthGuardMiddleware, auth_provider=auth_provider)
    app.add_middleware(SessionMiddleware, secret_key="test-secret")  # noqa: S106

    import httpx

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        # Seed signed session cookie via app login route.
        login_resp = await client.get("/admin/login")
        assert login_resp.status_code == 200

        resp = await client.get("/admin/protected")
        assert resp.status_code == 200
        body = resp.json()
        assert body.get("authenticated") is True
        assert body.get("email") == "session@int.com"
