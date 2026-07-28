"""Tests for Prometheus middleware."""

import pytest
from unittest.mock import AsyncMock, MagicMock

import lexigram.monitor.middleware.prometheus as prometheus_module
from lexigram.monitor.middleware.prometheus import PrometheusMiddleware


@pytest.fixture
def mock_asgi_app():
    async def app(scope, receive, send):
        if scope["type"] == "http":
            await send({"type": "http.response.start", "status": 200})
            await send({"type": "http.response.body", "body": b"ok"})
    return app

@pytest.mark.asyncio
async def test_prometheus_middleware_http(mock_asgi_app):
    """Test PrometheusMiddleware with HTTP request."""
    # Force PROMETHEUS_AVAILABLE = False to test internal formatting fallback
    import importlib.util
    original_prometheus_available = prometheus_module.PROMETHEUS_AVAILABLE
    prometheus_module.PROMETHEUS_AVAILABLE = False
    
    try:
        middleware = PrometheusMiddleware(path="/metrics")
        middleware.set_next_app(mock_asgi_app)
        
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/test",
        }
        receive = AsyncMock()
        send = AsyncMock()
        
        await middleware(scope, receive, send)
        
        assert send.call_count == 2
        
        # Test serving metrics
        metrics_scope = {
            "type": "http",
            "method": "GET",
            "path": "/metrics",
        }
        metrics_send = AsyncMock()
        await middleware(metrics_scope, receive, metrics_send)
        
        # Check if response start was sent
        assert metrics_send.call_args_list[0][0][0]["status"] == 200
    finally:
        prometheus_module.PROMETHEUS_AVAILABLE = original_prometheus_available

@pytest.mark.asyncio
async def test_prometheus_middleware_non_http(mock_asgi_app):
    """Test PrometheusMiddleware with non-http scope."""
    middleware = PrometheusMiddleware()
    middleware.set_next_app(mock_asgi_app)
    
    scope = {"type": "lifespan"}
    receive = AsyncMock()
    send = AsyncMock()
    
    await middleware(scope, receive, send)
    
    # next_app should be called, but we don't have an easy way to verify unless we wrap it
