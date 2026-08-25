"""Health endpoint test using the canonical Application+WebProvider pattern."""

from __future__ import annotations

import asyncio

from starlette.testclient import TestClient

from lexigram.app.base import Application
from lexigram.builder.constants import __version__
from lexigram.web.config import RateLimitConfig, WebConfig
from lexigram.web.di.provider import WebProvider


def _boot_web():
    app = Application(name="builder-health-test")
    web = WebProvider(
        controllers=[_controller_cls()],
        web_config=WebConfig(rate_limit=RateLimitConfig(enabled=False)),
    )
    return app, web


def _controller_cls():
    from lexigram.builder.controllers.builder_controller import BuilderController

    return BuilderController


def test_health_endpoint_returns_ok() -> None:
    app, web = _boot_web()
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(web.register(app.container))
        loop.run_until_complete(web.boot(app.container))
        client = TestClient(web.starlette)
        response = client.get("/builder/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["version"] == __version__
    finally:
        loop.run_until_complete(web.shutdown())
        loop.close()
