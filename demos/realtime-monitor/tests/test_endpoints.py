"""Endpoint tests for the realtime monitor demo.

Exercises the HTTP and WebSocket transports through a Starlette TestClient
with the demo's own controller and WS endpoint wired the same way the provider
hooks them up. The SSE handler is exercised directly (it is an async generator)
to avoid blocking on an infinite HTTP stream.
"""

from __future__ import annotations

import pytest
from starlette.applications import Starlette
from starlette.routing import WebSocketRoute
from starlette.testclient import TestClient

from ops_console.controllers.console import ConsoleController, EventsStreamHandler
from ops_console.domain import Severity, SystemEvent
from ops_console.services.event_stream import EventStreamService
from ops_console.ui.pages import PagesController


def build_app() -> Starlette:
    events = EventStreamService()
    sse = EventsStreamHandler(events)
    controller = ConsoleController(events, sse)

    async def publish(request) -> None:
        result = await controller.publish_event(request)
        from starlette.responses import JSONResponse

        return JSONResponse(result)

    async def stats(request) -> None:
        from starlette.responses import JSONResponse

        return JSONResponse(await controller.stats(request))

    pages = PagesController()

    async def index(request) -> None:
        return await pages.index(request)

    async def dashboard_js(request) -> None:
        return await pages.dashboard_js(request)

    async def dashboard_css(request) -> None:
        return await pages.stylesheet(request)

    async def ws_endpoint(starlette_ws) -> None:
        from lexigram.web import WebSocket

        from ops_console.controllers.operator import OperatorHandler

        ws = WebSocket(starlette_ws)
        await OperatorHandler(events).handle(ws)

    app = Starlette()
    app.add_route("/api/events/stream", controller.stream)
    app.add_route("/api/stats", stats)
    app.add_route("/static/dashboard.js", dashboard_js)
    app.add_route("/static/style.css", dashboard_css)
    app.add_route("/api/events", publish, methods=["POST"])
    app.add_route("/", index)
    app.router.routes.append(WebSocketRoute("/api/ws/operator", ws_endpoint))
    return app


@pytest.fixture
def client() -> TestClient:
    return TestClient(build_app())


def test_dashboard_page_renders(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "Realtime Console" in response.text
    assert "src=\"/static/dashboard.js\"" in response.text
    assert "href=\"/static/style.css\"" in response.text


def test_stats_endpoint_reports_live_counts(client: TestClient) -> None:
    response = client.get("/api/stats")

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"subscribers", "history"}
    assert isinstance(body["subscribers"], int)
    assert isinstance(body["history"], int)


def test_dashboard_js_asset_is_served(client: TestClient) -> None:
    response = client.get("/static/dashboard.js")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/javascript")
    assert "new EventSource" in response.text
    assert "feed-data" in response.text


def test_dashboard_css_asset_is_served(client: TestClient) -> None:
    response = client.get("/static/style.css")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/css")
    assert "--bg" in response.text
    assert ".topbar" in response.text


@pytest.mark.asyncio
async def test_sse_replays_history_on_connect() -> None:
    events = EventStreamService()
    handler = EventsStreamHandler(events)
    await events.publish(
        SystemEvent(kind="deploy", message="v1.2.0 shipped", severity=Severity.INFO, source="ci")
    )

    gen = handler._create_event_generator(None)
    try:
        first = await anext(gen)
        assert first.retry == 3000
        second = await anext(gen)
        assert second.event == "deploy"
        assert second.data["message"] == "v1.2.0 shipped"
    finally:
        await gen.aclose()


def test_publish_event_endpoint_broadcasts(client: TestClient) -> None:
    response = client.post(
        "/api/events",
        json={"message": "deploy approved", "severity": "critical", "source": "ops"},
    )

    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert response.json()["subscribers"] == 0


def test_websocket_operator_publishes_and_replies(client: TestClient) -> None:
    with client.websocket_connect("/api/ws/operator") as ws:
        ack = ws.receive_json()
        assert ack["ok"] is True

        ws.send_json({"message": "rollback now", "severity": "warn"})
        reply = ws.receive_json()

    assert reply["ok"] is True
    assert reply["severity"] == "warn"