"""Tests for lexigram.http — the core async HTTP client module."""

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


class TestExceptionHierarchy:
    """Verify the exception hierarchy so callers can catch at any level."""

    def test_all_http_errors_inherit_from_http_error(self) -> None:
        from lexigram.contracts.exceptions import InfrastructureError

        for cls in (
            HTTPConnectionError,
            HTTPTimeoutError,
            HTTPInterceptorError,
            HTTPCircuitOpenError,
            HTTPRetryExhaustedError,
        ):
            assert issubclass(cls, HTTPClientError)
            assert issubclass(cls, InfrastructureError)

    def test_http_error_is_infrastructure_error(self) -> None:
        from lexigram.contracts.exceptions import InfrastructureError

        assert issubclass(HTTPClientError, InfrastructureError)

    def test_error_message_preserved(self) -> None:
        err = HTTPClientError("bad things happened")
        assert "bad things happened" in str(err)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestConstants:
    def test_method_names(self) -> None:
        assert GET == "GET"
        assert POST == "POST"

    def test_defaults(self) -> None:
        assert DEFAULT_MAX_CONNECTIONS == 10
        assert DEFAULT_TIMEOUT == 30.0

    def test_content_type_json(self) -> None:
        assert "json" in CONTENT_TYPE_JSON.lower()

    def test_encoding(self) -> None:
        assert DEFAULT_ENCODING == "utf-8"


# ---------------------------------------------------------------------------
# Config dataclasses
# ---------------------------------------------------------------------------


class TestConnectionPoolConfig:
    def test_defaults(self) -> None:
        cfg = ConnectionPoolConfig()
        assert cfg.max_connections == DEFAULT_MAX_CONNECTIONS
        assert cfg.timeout == DEFAULT_TIMEOUT
        assert cfg.force_close is False

    def test_custom_values(self) -> None:
        cfg = ConnectionPoolConfig(max_connections=50, timeout=60.0, force_close=True)
        assert cfg.max_connections == 50
        assert cfg.timeout == 60.0
        assert cfg.force_close is True


class TestHTTPClientConfig:
    def test_defaults(self) -> None:
        cfg = HTTPClientConfig()
        assert isinstance(cfg.pool, ConnectionPoolConfig)

    def test_custom_pool(self) -> None:
        pool_cfg = ConnectionPoolConfig(max_connections=100)
        cfg = HTTPClientConfig(pool=pool_cfg)
        assert cfg.pool.max_connections == 100


# ---------------------------------------------------------------------------
# Connection pool
# ---------------------------------------------------------------------------


class TestConnectionPool:
    @pytest.mark.asyncio
    async def test_start_creates_session(self) -> None:
        pool = ConnectionPool()
        assert not pool.is_started()
        await pool.start()
        assert pool.is_started()
        assert pool._session is not None
        await pool.stop()

    @pytest.mark.asyncio
    async def test_stop_closes_session(self) -> None:
        pool = ConnectionPool()
        await pool.start()
        await pool.stop()
        assert not pool.is_started()
        assert pool._session is None

    @pytest.mark.asyncio
    async def test_start_is_idempotent(self) -> None:
        pool = ConnectionPool()
        await pool.start()
        session_first = pool._session
        await pool.start()  # second call should not create another session
        assert pool._session is session_first
        await pool.stop()

    @pytest.mark.asyncio
    async def test_custom_limits_applied(self) -> None:
        pool = ConnectionPool(max_connections=50, max_connections_per_host=20)
        await pool.start()
        connector = pool._session.connector  # type: ignore[union-attr]
        assert connector.limit == 50
        assert connector.limit_per_host == 20
        await pool.stop()

    def test_defaults(self) -> None:
        pool = ConnectionPool()
        assert pool.max_connections == 10
        assert pool.max_keepalive_connections == 5
        assert pool.timeout == 30.0
        assert pool.ttl_dns_cache == 300
        assert pool.force_close is False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class TestBuildUrl:
    def test_simple_path(self) -> None:
        assert (
            build_url("http://api.example.com", "/users")
            == "http://api.example.com/users"
        )

    def test_trailing_slash_on_base(self) -> None:
        assert (
            build_url("http://api.example.com/", "/users")
            == "http://api.example.com/users"
        )

    def test_query_params(self) -> None:
        url = build_url("http://localhost", "/search", {"q": "hello", "page": 2})
        assert "q=hello" in url
        assert "page=2" in url

    def test_none_params_omitted(self) -> None:
        url = build_url("http://localhost", "/x", {"a": 1, "b": None})
        assert "b=" not in url
        assert "a=1" in url

    def test_no_path(self) -> None:
        assert build_url("http://example.com") == "http://example.com"


class TestParseHeaders:
    def test_lowercase_keys(self) -> None:
        result = parse_headers({"Content-Type": "application/json"})
        assert "content-type" in result
        assert "Content-Type" not in result

    def test_strip_values(self) -> None:
        result = parse_headers({"accept": "  */*  "})
        assert result["accept"] == "*/*"


class TestMergeHeaders:
    def test_later_wins(self) -> None:
        result = merge_headers({"a": "1"}, {"a": "2"})
        assert result["a"] == "2"

    def test_no_normalize(self) -> None:
        result = merge_headers({"X-Foo": "bar"}, normalize=False)
        assert "X-Foo" in result

    def test_normalize_by_default(self) -> None:
        result = merge_headers({"X-Foo": "bar"})
        assert "x-foo" in result


class TestFormatTimeout:
    def test_seconds_suffix(self) -> None:
        assert format_timeout(30.0) == "30.0s"

    def test_none_returns_no_timeout(self) -> None:
        assert format_timeout(None) == "no timeout"


class TestParseUrlParts:
    def test_full_url(self) -> None:
        parts = parse_url_parts("http://service.example.com:8080/api/v1")
        assert parts["scheme"] == "http"
        assert parts["host"] == "service.example.com"
        assert parts["port"] == 8080
        assert parts["path"] == "/api/v1"


class TestExtractJsonType:
    def test_json_content_type(self) -> None:
        assert extract_json_type("application/json") == "application/json"

    def test_json_with_charset(self) -> None:
        assert (
            extract_json_type("application/json; charset=utf-8") == "application/json"
        )

    def test_non_json(self) -> None:
        assert extract_json_type("text/html") is None

    def test_empty(self) -> None:
        assert extract_json_type("") is None


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TestValidateUrl:
    def test_valid_http(self) -> None:
        validate_url("http://example.com")

    def test_valid_https(self) -> None:
        validate_url("https://example.com:8080/path")

    @pytest.mark.parametrize("url", ["not-a-url", "http://", "", "://bad"])
    def test_invalid_raises_http_error(self, url: str) -> None:
        with pytest.raises(HTTPClientError):
            validate_url(url)


class TestValidateHost:
    def test_valid_hostname(self) -> None:
        validate_host("localhost")
        validate_host("example.com")

    def test_valid_ipv4(self) -> None:
        validate_host("192.168.1.1")

    def test_empty_raises(self) -> None:
        with pytest.raises(HTTPClientError):
            validate_host("")

    def test_double_dot_raises(self) -> None:
        with pytest.raises(HTTPClientError):
            validate_host("invalid..host")


class TestValidatePort:
    def test_valid_ports(self) -> None:
        validate_port(1)
        validate_port(8080)
        validate_port(65535)

    def test_zero_raises(self) -> None:
        with pytest.raises(HTTPClientError):
            validate_port(0)

    def test_too_large_raises(self) -> None:
        with pytest.raises(HTTPClientError):
            validate_port(70000)


class TestValidateTimeout:
    def test_valid_timeout(self) -> None:
        validate_timeout(5.0)
        validate_timeout(0.1)

    def test_none_is_allowed(self) -> None:
        validate_timeout(None)  # should not raise

    def test_zero_raises(self) -> None:
        with pytest.raises(HTTPClientError):
            validate_timeout(0)

    def test_negative_raises(self) -> None:
        with pytest.raises(HTTPClientError):
            validate_timeout(-1.0)


class TestValidatePositiveInt:
    def test_valid(self) -> None:
        validate_positive_int(1)
        validate_positive_int(100)

    def test_zero_raises(self) -> None:
        with pytest.raises(HTTPClientError):
            validate_positive_int(0)

    def test_negative_raises(self) -> None:
        with pytest.raises(HTTPClientError):
            validate_positive_int(-5)


# ---------------------------------------------------------------------------
# RequestContext / ResponseContext
# ---------------------------------------------------------------------------


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


def _make_raw_response(
    *,
    status: int = 200,
    body: bytes = b"",
    content_type: str = "text/plain",
    url: str = "http://example.com",
) -> MagicMock:
    """Build a minimal mock that matches what ``_to_http_response`` expects."""
    resp = MagicMock()
    resp.status = status
    resp.headers = {"Content-Type": content_type}
    resp.read = AsyncMock(return_value=body)
    resp.get_encoding = MagicMock(return_value="utf-8")
    resp.json = AsyncMock(return_value=None)
    resp.url = url
    return resp


def _make_mock_retry_policy() -> MagicMock:
    """Retry policy that executes the callable directly — no delay."""
    policy = MagicMock()

    async def execute(fn, method=None):  # type: ignore[no-untyped-def]
        return await fn()

    policy.execute = AsyncMock(side_effect=execute)
    return policy


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


class TestHTTPClientInterceptors:
    """Verify interceptors receive and can modify request/response."""

    @pytest.mark.asyncio
    async def test_request_interceptor_modifies_headers(self) -> None:
        from lexigram.http.client import HTTPClient

        class HeaderInjector:
            async def intercept_request(self, ctx: RequestContext) -> RequestContext:
                ctx.headers["x-injected"] = "yes"
                return ctx

            async def intercept_response(self, resp: object) -> object:
                return resp

        raw = _make_raw_response(status=200)
        retry_policy = _make_mock_retry_policy()
        client = HTTPClient(retry_policy=retry_policy, interceptors=[HeaderInjector()])

        captured_headers: dict[str, str] = {}

        async def fake_request(method: str, url: str, **kwargs: object) -> MagicMock:
            captured_headers.update(kwargs.get("headers", {}))  # type: ignore[arg-type]
            return raw

        client._pool = SimpleNamespace(  # type: ignore[assignment]
            _session=SimpleNamespace(request=fake_request),
        )
        await client.get("http://example.com/")
        assert captured_headers.get("x-injected") == "yes"

    @pytest.mark.asyncio
    async def test_response_interceptor_annotates_response(self) -> None:
        from lexigram.http.client import HTTPClient

        class Annotator:
            async def intercept_request(self, ctx: object) -> object:
                return ctx

            async def intercept_response(self, resp: object) -> object:
                resp.annotated = True
                return resp

        raw = _make_raw_response(status=200)
        retry_policy = _make_mock_retry_policy()
        client = HTTPClient(retry_policy=retry_policy, interceptors=[Annotator()])
        client._pool = SimpleNamespace(  # type: ignore[assignment]
            _session=SimpleNamespace(request=AsyncMock(return_value=raw)),
        )
        await client.get("http://example.com/")
        assert getattr(raw, "annotated", False) is True


# ---------------------------------------------------------------------------
# Interceptor chain ordering
# ---------------------------------------------------------------------------


class TestHTTPInterceptorChainOrder:
    """Verify that multiple interceptors are applied in registration order."""

    @pytest.mark.asyncio
    async def test_request_interceptors_applied_in_order(self) -> None:
        """Request interceptors run in the order they are passed to HTTPClient."""
        from lexigram.http.client import HTTPClient

        order: list[str] = []

        class First:
            async def intercept_request(self, ctx: RequestContext) -> RequestContext:
                order.append("first-req")
                ctx.headers["x-first"] = "1"
                return ctx

            async def intercept_response(self, resp: object) -> object:
                order.append("first-resp")
                return resp

        class Second:
            async def intercept_request(self, ctx: RequestContext) -> RequestContext:
                order.append("second-req")
                ctx.headers["x-second"] = "2"
                return ctx

            async def intercept_response(self, resp: object) -> object:
                order.append("second-resp")
                return resp

        raw = _make_raw_response(status=200)
        retry_policy = _make_mock_retry_policy()
        client = HTTPClient(
            retry_policy=retry_policy,
            interceptors=[First(), Second()],
        )
        captured: dict[str, str] = {}

        async def fake_request(method: str, url: str, **kwargs: object) -> MagicMock:
            captured.update(kwargs.get("headers", {}))  # type: ignore[arg-type]
            return raw

        client._pool = SimpleNamespace(  # type: ignore[assignment]
            _session=SimpleNamespace(request=fake_request),
        )
        await client.get("http://example.com/")

        # Request interceptors run first→second
        assert order.index("first-req") < order.index("second-req")
        # Response interceptors run first→second (same order, not reversed)
        assert order.index("first-resp") < order.index("second-resp")
        # Both headers were injected
        assert captured.get("x-first") == "1"
        assert captured.get("x-second") == "2"

    @pytest.mark.asyncio
    async def test_later_interceptor_can_see_earlier_header_mutation(self) -> None:
        """A downstream interceptor sees mutations made by earlier interceptors."""
        from lexigram.http.client import HTTPClient

        class Setter:
            async def intercept_request(self, ctx: RequestContext) -> RequestContext:
                ctx.headers["x-chain"] = "set"
                return ctx

            async def intercept_response(self, resp: object) -> object:
                return resp

        class Reader:
            def __init__(self) -> None:
                self.saw: str | None = None

            async def intercept_request(self, ctx: RequestContext) -> RequestContext:
                self.saw = ctx.headers.get("x-chain")
                return ctx

            async def intercept_response(self, resp: object) -> object:
                return resp

        reader = Reader()
        raw = _make_raw_response(status=200)
        retry_policy = _make_mock_retry_policy()
        client = HTTPClient(
            retry_policy=retry_policy,
            interceptors=[Setter(), reader],
        )
        client._pool = SimpleNamespace(  # type: ignore[assignment]
            _session=SimpleNamespace(request=AsyncMock(return_value=raw)),
        )
        await client.get("http://example.com/")
        assert reader.saw == "set"


# ---------------------------------------------------------------------------
# HTTPProvider (DI)
# ---------------------------------------------------------------------------


class TestHTTPProvider:
    @pytest.mark.asyncio
    async def test_get_client_before_boot_raises(self) -> None:
        from lexigram.http.di.provider import HTTPProvider

        provider = HTTPProvider()
        with pytest.raises(RuntimeError, match="not been booted"):
            provider._get_client()

    @pytest.mark.asyncio
    async def test_health_check_unhealthy_before_boot(self) -> None:
        from lexigram.contracts.core import HealthStatus
        from lexigram.http.di.provider import HTTPProvider

        provider = HTTPProvider()
        result = await provider.health_check()
        assert result.status == HealthStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_register_adds_singleton_bindings(self) -> None:
        from lexigram.contracts.web import HTTPClientProtocol
        from lexigram.http.client import HTTPClient
        from lexigram.http.di.provider import HTTPProvider

        provider = HTTPProvider()

        registered: dict[type, object] = {}

        class FakeRegistrar:
            def singleton(self, key: type, factory: object) -> None:
                registered[key] = factory

        await provider.register(FakeRegistrar())  # type: ignore[arg-type]
        assert HTTPClient in registered
        assert HTTPClientProtocol in registered

    @pytest.mark.asyncio
    async def test_boot_and_shutdown_lifecycle(self) -> None:
        from lexigram.contracts.core import HealthStatus
        from lexigram.http.di.provider import HTTPProvider

        provider = HTTPProvider()

        class FakeResolver:
            async def resolve(self, key: type) -> object:
                raise RuntimeError("not registered")

        await provider.boot(FakeResolver())  # type: ignore[arg-type]
        result = await provider.health_check()
        assert result.status == HealthStatus.HEALTHY

        await provider.shutdown()
        result = await provider.health_check()
        assert result.status == HealthStatus.UNHEALTHY


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


class TestProtocolConformance:
    def test_http_client_satisfies_protocol(self) -> None:
        from lexigram.contracts.web import HTTPClientProtocol
        from lexigram.http.client import HTTPClient

        assert isinstance(HTTPClient(), HTTPClientProtocol)

    def test_connection_pool_is_importable_via_public_api(self) -> None:
        from lexigram.http.client import ConnectionPool as CP

        assert CP is ConnectionPool

    def test_lazy_api_exports_all_names(self) -> None:
        import lexigram.http as http_mod

        for name in [
            "HTTPClient",
            "HTTPProvider",
            "HTTPClientConfig",
            "ConnectionPoolConfig",
            "ConnectionPool",
            "HTTPClientError",
            "build_url",
            "validate_url",
            "RequestContext",
            "ResponseContext",
        ]:
            assert hasattr(http_mod, name), f"lexigram.http.client missing {name!r}"
