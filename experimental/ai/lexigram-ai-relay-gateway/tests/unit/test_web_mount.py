"""Contributor registration and route mounting for the relay gateway."""

from __future__ import annotations

from lexigram.ai.relay.gateway.web.contributor import RelayGatewayWebContributor
from lexigram.ai.relay.gateway.web.routes import MODEL_ROUTE_PATHS, RELAY_ROUTE_PATHS

from web_test_helpers import FakeApp


def test_contributor_id() -> None:
    """The contributor exposes its registered identifier."""
    assert RelayGatewayWebContributor().contributor_id == "relay-gateway"

def test_contributor_get_controllers_empty() -> None:
    """Controllers and middleware are contributed by the host, not the gateway."""
    contributor = RelayGatewayWebContributor()
    assert contributor.get_controllers() == []
    assert contributor.get_middleware() == []

async def test_mount_registers_routes_once() -> None:
    """Repeated mounts register each relay, model, and health path exactly once."""
    app = FakeApp()
    contributor = RelayGatewayWebContributor()
    await contributor.mount_to_app(app, object())
    await contributor.mount_to_app(app, object())
    expected = list(RELAY_ROUTE_PATHS) + list(MODEL_ROUTE_PATHS) + ["/health"]
    actual = [path for path, _, _ in app.registrations]
    assert sorted(actual) == sorted(expected)
    assert len(app.registrations) == len(expected)
    for path, _, methods in app.registrations:
        if path == "/health":
            assert methods == ["GET", "HEAD"]
        else:
            assert methods == (
                ["GET", "HEAD"] if path in MODEL_ROUTE_PATHS else ["POST"]
            )
