import pytest
from starlette.testclient import TestClient

from lexigram.web.config import WebProviderConfig
from lexigram.web.routing.controllers import Controller
from lexigram.web import get


class DebugController(Controller):
    @get("/x")
    def x(self):
        return {"ok": True}


@pytest.mark.asyncio
async def test_debug_routes_endpoint_lists_routes(test_bed):
    """Test that the debug routes endpoint returns a list of registered routes."""
    from lexigram.web.di.provider import WebProvider
    
    web = await test_bed.resolve(WebProvider)
    
    client = TestClient(web.starlette)
    r = client.get("/debug/routes")
    assert r.status_code == 200
    j = r.json()
    assert "routes" in j
