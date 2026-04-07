from unittest.mock import AsyncMock, Mock

import pytest

from lexigram.admin.middleware.cache import AdminCacheMiddleware


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_backend(*, get_result=None, set_result=None):
    """Build a minimal CacheBackendProtocol mock that returns Result values."""
    from lexigram.result import Ok

    backend = AsyncMock()
    backend.get = AsyncMock(return_value=Ok(get_result))
    backend.set = AsyncMock(return_value=Ok(None) if set_result is None else set_result)
    return backend


@pytest.fixture
def mock_app():
    return AsyncMock()


@pytest.fixture
def mock_settings():
    settings = Mock()
    settings.get = AsyncMock(return_value=None)
    return settings


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cache_miss_and_store(mock_app):
    backend = _make_backend(get_result=None)  # cache miss
    middleware = AdminCacheMiddleware(mock_app, cache_backend=backend, ttl=60)

    async def app_impl(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"Response Data"})

    mock_app.side_effect = app_impl

    send_mock = AsyncMock()
    scope = {"type": "http", "method": "GET", "path": "/data", "query_string": b""}

    # First call: Cache Miss — app is invoked.
    await middleware(scope, None, send_mock)
    mock_app.assert_called_once()

    # Response forwarded.
    assert send_mock.call_count == 2
    assert send_mock.call_args_list[1][0][0]["body"] == b"Response Data"

    # Backend.set was called to store the response.
    backend.set.assert_called_once()
    call_kwargs = backend.set.call_args
    stored_payload = call_kwargs[0][1]  # positional arg: value
    assert stored_payload["body"] == b"Response Data"
    assert stored_payload["status_code"] == 200


@pytest.mark.asyncio
async def test_cache_hit(mock_app):
    cached_payload = {
        "status_code": 200,
        "headers": [(b"content-type", b"text/plain")],
        "body": b"Cached Data",
    }
    backend = _make_backend(get_result=cached_payload)
    middleware = AdminCacheMiddleware(mock_app, cache_backend=backend, ttl=60)

    scope = {"type": "http", "method": "GET", "path": "/data", "query_string": b""}
    send_mock = AsyncMock()
    await middleware(scope, None, send_mock)

    # App NOT called — served from cache.
    mock_app.assert_not_called()

    # Response comes from cached payload.
    assert send_mock.call_count == 2
    assert send_mock.call_args_list[1][0][0]["body"] == b"Cached Data"


@pytest.mark.asyncio
async def test_cache_bypass_no_cache(mock_app):
    backend = _make_backend(get_result=None)
    middleware = AdminCacheMiddleware(mock_app, cache_backend=backend, ttl=60)

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/data",
        "query_string": b"",
        "headers": [(b"cache-control", b"no-cache")],
    }

    await middleware(scope, None, AsyncMock())

    # no-cache header bypasses even a warm cache.
    mock_app.assert_called_once()
    backend.get.assert_not_called()


@pytest.mark.asyncio
async def test_cache_disabled_via_settings(mock_app, mock_settings):
    mock_settings.get.side_effect = (
        lambda k: False if k == "admin.cache.enabled" else None
    )
    backend = _make_backend(get_result={"status_code": 200, "headers": [], "body": b"Old"})
    middleware = AdminCacheMiddleware(
        mock_app, cache_backend=backend, settings_service=mock_settings
    )

    scope = {"type": "http", "method": "GET", "path": "/data", "query_string": b""}
    await middleware(scope, None, AsyncMock())

    # Cache disabled → app called, backend.get never consulted.
    mock_app.assert_called_once()
    backend.get.assert_not_called()
