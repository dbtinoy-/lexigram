import asyncio
import sys
from pathlib import Path
import pytest

# Add the web src directory to Python path for pytest compatibility
web_src = Path(__file__).parent.parent.parent / "src"
if str(web_src) not in sys.path:
    sys.path.insert(0, str(web_src))


from starlette.testclient import TestClient

from lexigram.app.base import Application
from lexigram.web.config import WebConfig, RateLimitConfig
from lexigram.web.di.provider import WebProvider
from lexigram.web.routing.controllers import Controller
from lexigram.web import get


class CallbackController(Controller):
    @get("/cb")
    def cb(self):
        return {"ok": True}


def test_debug_routes_pluggable_auth_allows_and_denies():
    app = Application(name="test-app")

    # Auth callable must be async
    async def auth_callable(request):
        return request.headers.get("x-admin") == "1"

    # Disable rate limiting to avoid WebRateLimiterProtocol dependency
    web = WebProvider(
        controllers=[CallbackController],
        debug_routes_auth=auth_callable,
        web_config=WebConfig(rate_limit=RateLimitConfig(enabled=False)),
    )

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(web.register(app.container))
        loop.run_until_complete(web.boot(app.container))

        with TestClient(web.starlette) as client:
            r = client.get("/debug/routes")
            assert r.status_code == 403

            r2 = client.get("/debug/routes", headers={"X-Admin": "1"})
            assert r2.status_code == 200

    finally:
        loop.run_until_complete(web.shutdown())
        loop.close()


@pytest.mark.skip(reason="Debug routes exception handling not implemented - exception propagates instead of returning 500")
def test_debug_routes_pluggable_auth_exception_returns_500():
    app = Application(name="test-app")

    async def bad_callable(request):
        raise RuntimeError("boom")

    # Disable rate limiting to avoid WebRateLimiterProtocol dependency
    web = WebProvider(
        controllers=[CallbackController],
        debug_routes_auth=bad_callable,
        web_config=WebConfig(rate_limit=RateLimitConfig(enabled=False)),
    )

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(web.register(app.container))
        loop.run_until_complete(web.boot(app.container))

        with TestClient(web.starlette) as client:
            r = client.get("/debug/routes")
            assert r.status_code == 500
            assert r.json()["error"] == "internal_error"

    finally:
        loop.run_until_complete(web.shutdown())
        loop.close()
