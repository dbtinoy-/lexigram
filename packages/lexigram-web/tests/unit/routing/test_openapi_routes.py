import asyncio
import pytest
from lexigram.app.base import Application
from lexigram.web.config import WebConfig, RateLimitConfig
from lexigram.web.di.provider import WebProvider
from lexigram.web.routing.controllers import Controller
from lexigram.web import get


class DummyController(Controller):
    @get("/dummy/{item_id}")
    async def get_item(self):
        return {"id": "123"}


@pytest.mark.asyncio
async def test_openapi_routes_present():
    app = Application(name="test-app")

    async def _allow_all(request):
        return True

    web = WebProvider(
        web_config=WebConfig(
            rate_limit=RateLimitConfig(enabled=False),
            debug_routes=True,
        ),
        controllers=[DummyController],
        debug_routes_auth=_allow_all,
    )

    await web.register(app.container)
    await web.boot(app.container)

    assert web.starlette is not None

    paths = list(map(lambda r: r.path, web.starlette.routes))
    assert "/openapi.json" in paths
    assert "/docs" in paths
    assert "/dummy/{item_id}" in paths

    await web.shutdown()
