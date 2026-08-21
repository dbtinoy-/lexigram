"""HTTP request/response contexts and client lifecycle/request tests."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.http.config import ConnectionPoolConfig, HTTPClientConfig
from lexigram.http.constants import (
    CONTENT_TYPE_JSON,
    DEFAULT_ENCODING,
    DEFAULT_MAX_CONNECTIONS,
    DEFAULT_TIMEOUT,
    GET,
    POST,
)
from lexigram.http.exceptions import (
    HTTPCircuitOpenError,
    HTTPClientError,
    HTTPConnectionError,
    HTTPInterceptorError,
    HTTPRetryExhaustedError,
    HTTPTimeoutError,
)
from lexigram.http.lib import (
    build_url,
    extract_json_type,
    format_timeout,
    merge_headers,
    parse_headers,
    parse_url_parts,
)
from lexigram.http.pool import ConnectionPool
from lexigram.http.types import RequestContext, ResponseContext
from lexigram.http.validation import (
    validate_host,
    validate_port,
    validate_positive_int,
    validate_timeout,
    validate_url,
)

# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------



from http_module_test_support import _make_mock_retry_policy, _make_raw_response


class TestRequestContext:
    def test_defaults_populated(self) -> None:
        ctx = RequestContext(method="GET", url="http://example.com", headers={})
        assert ctx.start_time is not None
        assert ctx.attempt == 0
        assert ctx.service_name is None

    def test_headers_mutable(self) -> None:
        ctx = RequestContext(method="GET", url="http://example.com", headers={})
        ctx.headers["x-my-header"] = "value"
        assert ctx.headers["x-my-header"] == "value"


class TestResponseContext:
    def test_defaults(self) -> None:
        ctx = ResponseContext(status=200, headers={})
        assert ctx.success is True
        assert ctx.error is None
        assert ctx.duration is None


# ---------------------------------------------------------------------------
# HTTPClient — unit tests (pool and session mocked)
# ---------------------------------------------------------------------------




class TestHTTPClientLifecycle:
    @pytest.mark.asyncio
    async def test_start_and_stop(self) -> None:
        from lexigram.http.client import HTTPClient

        client = HTTPClient()
        await client.start()
        assert client._pool.is_started()
        await client.stop()
        assert not client._pool.is_started()

    @pytest.mark.asyncio
    async def test_defaults_set(self) -> None:
        from lexigram.http.client import HTTPClient

        client = HTTPClient()
        assert isinstance(client.config, HTTPClientConfig)
        assert isinstance(client._pool, ConnectionPool)
        assert client._circuit_breaker is None

    @pytest.mark.asyncio
    async def test_custom_pool_override(self) -> None:
        from lexigram.http.client import HTTPClient

        custom_pool = ConnectionPool(max_connections=200)
        client = HTTPClient(pool=custom_pool)
        assert client._pool.max_connections == 200

    @pytest.mark.asyncio
    async def test_custom_retry_policy_injected(self) -> None:
        from lexigram.http.client import HTTPClient

        mock_policy = MagicMock()
        client = HTTPClient(retry_policy=mock_policy)
        assert client._retry_policy is mock_policy

    @pytest.mark.asyncio
    async def test_session_context_starts_and_stops(self) -> None:
        from lexigram.http.client import HTTPClient

        async with HTTPClient.session_context() as client:
            assert client._pool.is_started()

    @pytest.mark.asyncio
    async def test_session_context_stops_on_error(self) -> None:
        from lexigram.http.client import HTTPClient

        with pytest.raises(ValueError):
            async with HTTPClient.session_context() as client:
                assert client._pool.is_started()
                raise ValueError("boom")

        assert not client._pool.is_started()


class TestHTTPClientRequests:
    """Unit-test request dispatch with a fully mocked pool session."""

    def _make_client_with_fake_session(
        self,
        raw_response: MagicMock,
    ):  # type: ignore[return]  # pragma: no cover
        from lexigram.http.client import HTTPClient

        retry_policy = _make_mock_retry_policy()
        client = HTTPClient(retry_policy=retry_policy)
        # Inject a fake pool with a fake session
        client._pool = SimpleNamespace(  # type: ignore[assignment]
            _session=SimpleNamespace(
                request=AsyncMock(return_value=raw_response),
            ),
            is_started=lambda: True,
        )
        return client

    @pytest.mark.asyncio
    async def test_get_returns_http_response(self) -> None:
        from lexigram.contracts.web import HttpResponse

        raw = _make_raw_response(status=200, body=b"hello")
        client = self._make_client_with_fake_session(raw)
        result = await client.get("http://example.com/")
        assert result.is_ok()
        response = result.unwrap()
        assert isinstance(response, HttpResponse)
        assert response.status == 200
        assert response.method == "GET"

    @pytest.mark.asyncio
    async def test_post_passes_kwargs(self) -> None:
        from lexigram.contracts.web import HttpResponse

        raw = _make_raw_response(status=201)
        client = self._make_client_with_fake_session(raw)
        result = await client.post("http://example.com/", json={"key": "val"})
        assert result.is_ok()
        response = result.unwrap()
        assert isinstance(response, HttpResponse)
        assert response.status == 201
        assert response.method == "POST"

    @pytest.mark.asyncio
    async def test_delete_method(self) -> None:
        raw = _make_raw_response(status=204)
        client = self._make_client_with_fake_session(raw)
        result = await client.delete("http://example.com/1")
        assert result.is_ok()
        response = result.unwrap()
        assert response.status == 204
        assert response.method == "DELETE"

    @pytest.mark.asyncio
    async def test_patch_method(self) -> None:
        raw = _make_raw_response(status=200)
        client = self._make_client_with_fake_session(raw)
        result = await client.patch("http://example.com/1", json={})
        assert result.is_ok()
        assert result.unwrap().method == "PATCH"

    @pytest.mark.asyncio
    async def test_put_method(self) -> None:
        raw = _make_raw_response(status=200)
        client = self._make_client_with_fake_session(raw)
        result = await client.put("http://example.com/1", json={})
        assert result.is_ok()
        assert result.unwrap().method == "PUT"

    @pytest.mark.asyncio
    async def test_head_method(self) -> None:
        raw = _make_raw_response(status=200)
        client = self._make_client_with_fake_session(raw)
        result = await client.head("http://example.com/")
        assert result.is_ok()
        assert result.unwrap().method == "HEAD"

    @pytest.mark.asyncio
    async def test_4xx_returns_err_status_error(self) -> None:
        from lexigram.http.exceptions import HTTPStatusError

        raw = _make_raw_response(status=404, body=b"not found")
        client = self._make_client_with_fake_session(raw)
        result = await client.get("http://example.com/missing")
        assert result.is_err()
        error = result.unwrap_err()
        assert isinstance(error, HTTPStatusError)
        assert error.status == 404

    @pytest.mark.asyncio
    async def test_5xx_returns_err_status_error(self) -> None:
        from lexigram.http.exceptions import HTTPStatusError

        raw = _make_raw_response(status=500, body=b"server error")
        client = self._make_client_with_fake_session(raw)
        result = await client.post("http://example.com/action", json={})
        assert result.is_err()
        error = result.unwrap_err()
        assert isinstance(error, HTTPStatusError)
        assert error.status == 500

    @pytest.mark.asyncio
    async def test_json_body_parsed(self) -> None:
        raw = _make_raw_response(
            status=200,
            body=b'{"result": "ok"}',
            content_type="application/json",
        )
        raw.json = AsyncMock(return_value={"result": "ok"})

        from lexigram.http.client import HTTPClient

        retry_policy = _make_mock_retry_policy()
        client = HTTPClient(retry_policy=retry_policy)
        client._pool = SimpleNamespace(  # type: ignore[assignment]
            _session=SimpleNamespace(request=AsyncMock(return_value=raw)),
        )
        result = await client.get("http://example.com/data")
        assert result.is_ok()
        assert result.unwrap().json == {"result": "ok"}

    @pytest.mark.asyncio
    async def test_circuit_open_short_circuits(self) -> None:
        from lexigram.http.client import HTTPClient

        cb = MagicMock()
        cb.state = MagicMock()
        cb.state.value = "open"

        client = HTTPClient(
            circuit_breaker=cb, config=HTTPClientConfig(enforce_url_safety=False)
        )
        client._pool = SimpleNamespace(  # type: ignore[assignment]
            _session=SimpleNamespace(request=AsyncMock()),
        )

        with pytest.raises(HTTPCircuitOpenError):
            await client.request("GET", "http://example.com/")

    @pytest.mark.asyncio
    async def test_retry_exhausted_wrapped(self) -> None:
        from lexigram.http.client import HTTPClient
        from lexigram.resilience import RetryExhaustedError

        policy = MagicMock()
        policy.execute = AsyncMock(side_effect=RetryExhaustedError("exhausted"))
        client = HTTPClient(
            retry_policy=policy, config=HTTPClientConfig(enforce_url_safety=False)
        )
        client._pool = SimpleNamespace(  # type: ignore[assignment]
            _session=SimpleNamespace(request=AsyncMock()),
        )

        with pytest.raises(HTTPRetryExhaustedError):
            await client.request("GET", "http://example.com/")

    @pytest.mark.asyncio
    async def test_not_started_raises_runtime_error(self) -> None:
        from lexigram.http.client import HTTPClient

        retry_policy = _make_mock_retry_policy()
        client = HTTPClient(
            retry_policy=retry_policy, config=HTTPClientConfig(enforce_url_safety=False)
        )
        # pool._session is None (not started)

        with pytest.raises(RuntimeError, match="not started"):
            await client.get("http://example.com/")


