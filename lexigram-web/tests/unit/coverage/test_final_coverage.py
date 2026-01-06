"""Final coverage push — targets 12 small modules with 3-7 missed lines each."""

from __future__ import annotations

import dataclasses
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest


# ---------------------------------------------------------------------------
# docs/type_registry.py  (lines 37, 47, 76)
# ---------------------------------------------------------------------------


class TestTypeDocumenterRegistry:
    def test_int_documenter_document(self) -> None:
        from lexigram.web.docs.type_registry import IntDocumenter

        d = IntDocumenter()
        param: dict[str, Any] = {}
        d.document(param)
        assert param == {"schema": {"type": "integer"}}

    def test_bool_documenter_document(self) -> None:
        from lexigram.web.docs.type_registry import BoolDocumenter

        d = BoolDocumenter()
        param: dict[str, Any] = {}
        d.document(param)
        assert param == {"schema": {"type": "boolean"}}

    def test_float_documenter_document(self) -> None:
        from lexigram.web.docs.type_registry import FloatDocumenter

        d = FloatDocumenter()
        param: dict[str, Any] = {}
        d.document(param)
        assert param == {"schema": {"type": "number"}}

    def test_registry_returns_none_for_unknown_type(self) -> None:
        from lexigram.web.docs.type_registry import TypeDocumenterRegistry

        registry = TypeDocumenterRegistry()
        result = registry.get_documenter(list)
        assert result is None


# ---------------------------------------------------------------------------
# exceptions.py  (lines 72, 99, 115, 126, 179-180)
# ---------------------------------------------------------------------------


class TestExceptions:
    def test_conflict_error(self) -> None:
        from lexigram.web.exceptions import ConflictError

        exc = ConflictError("resource conflict")
        assert exc.status_code == 409
        assert exc.detail == "resource conflict"
        assert exc.code == "CONFLICT"

    def test_unprocessable_entity_error(self) -> None:
        from lexigram.web.exceptions import UnprocessableEntityError

        exc = UnprocessableEntityError("bad entity")
        assert exc.status_code == 422
        assert exc.code == "UNPROCESSABLE_ENTITY"

    def test_internal_server_error(self) -> None:
        from lexigram.web.exceptions import InternalServerError

        exc = InternalServerError("something broke")
        assert exc.status_code == 500
        assert exc.code == "INTERNAL_SERVER_ERROR"

    def test_dependency_resolution_error(self) -> None:
        from lexigram.web.exceptions import DependencyResolutionError

        exc = DependencyResolutionError("my_param", str)
        assert exc.status_code == 500
        assert exc.param == "my_param"
        assert exc.service_type is str

    def test_too_many_connections_error(self) -> None:
        from lexigram.web.exceptions import TooManyConnectionsError

        exc = TooManyConnectionsError()
        assert exc.status_code == 503
        assert exc.code == "TOO_MANY_CONNECTIONS"

    def test_too_many_connections_error_custom_detail(self) -> None:
        from lexigram.web.exceptions import TooManyConnectionsError

        exc = TooManyConnectionsError("max reached")
        assert exc.detail == "max reached"

    def test_unauthorized_error(self) -> None:
        """Covers line 72 — UnauthorizedError.__init__ super call."""
        from lexigram.web.exceptions import UnauthorizedError

        exc = UnauthorizedError("token expired")
        assert exc.status_code == 401
        assert exc.code == "UNAUTHORIZED"

    def test_method_not_allowed_error(self) -> None:
        """Covers line 99 — MethodNotAllowedError.__init__ super call."""
        from lexigram.web.exceptions import MethodNotAllowedError

        exc = MethodNotAllowedError("PUT not allowed")
        assert exc.status_code == 405
        assert exc.code == "METHOD_NOT_ALLOWED"

    def test_rate_limit_error_with_retry_after(self) -> None:
        """Covers lines 179-180 — RateLimitError with retry_after header."""
        from lexigram.web.exceptions import RateLimitError

        exc = RateLimitError(detail="slow down", retry_after=30)
        assert exc.status_code == 429
        assert exc.headers.get("Retry-After") == "30"


# ---------------------------------------------------------------------------
# filters/builtin.py  (lines 34, 37-38, 44-47)
# ---------------------------------------------------------------------------


class TestValidationErrorFilterLines:
    def test_can_handle_value_error_with_validation_keyword(self) -> None:
        """Covers line 34 — the isinstance(exc, ValueError) branch."""
        from lexigram.web.filters.builtin import ValidationErrorFilter

        f = ValidationErrorFilter()
        exc = ValueError("validation failed: bad input")
        assert f.can_handle(exc) is True

    @pytest.mark.asyncio
    async def test_handle_with_list_errors_attribute(self) -> None:
        """Covers lines 35-36 — exc.errors is a list (not callable)."""
        from lexigram.web.filters.builtin import ValidationErrorFilter

        class _FakeExc:
            errors = [{"msg": "field required", "loc": ["name"]}]

        f = ValidationErrorFilter()
        response = await f.handle(_FakeExc(), None)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_handle_with_args_path(self) -> None:
        """Covers lines 37-38 — exc has no errors attr, only args."""
        from lexigram.web.filters.builtin import ValidationErrorFilter

        class _FakeExcWithArgs:
            args = ("validation error: field is required",)

        f = ValidationErrorFilter()
        response = await f.handle(_FakeExcWithArgs(), None)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_handle_with_dataclass_errors(self) -> None:
        """Covers lines 42-43 — dataclass error instances in raw_errors."""
        from lexigram.web.filters.builtin import ValidationErrorFilter

        @dataclasses.dataclass
        class ErrorInfo:
            msg: str
            loc: str = "field"

        class _FakeExcCallable:
            def errors(self) -> list[ErrorInfo]:
                return [ErrorInfo(msg="required")]

        f = ValidationErrorFilter()
        response = await f.handle(_FakeExcCallable(), None)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_handle_with_string_error_items(self) -> None:
        """Covers line 47 — else branch: non-dict, non-dataclass error items."""
        from lexigram.web.filters.builtin import ValidationErrorFilter

        class _FakeExcWithStringErrors:
            def errors(self) -> list[str]:
                return ["field is required", "value too long"]

        f = ValidationErrorFilter()
        response = await f.handle(_FakeExcWithStringErrors(), None)
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# pipes/decorators.py  (lines 39-51 — inspect.isclass branch)
# ---------------------------------------------------------------------------


class TestUsePipesOnClass:
    def test_use_pipes_applied_to_class_methods(self) -> None:
        """Covers lines 39-51 — applying use_pipes to a class."""
        from lexigram.web.pipes import PipeBase
        from lexigram.web.pipes.decorators import use_pipes

        class _IdentityPipe(PipeBase):
            pass

        pipe = _IdentityPipe()

        @use_pipes(pipe)
        class _MyController:
            def create(self) -> None:
                pass

            def update(self) -> None:
                pass

        assert hasattr(_MyController.create, "_lexigram_pipes")
        assert pipe in _MyController.create._lexigram_pipes

    def test_use_pipes_prepends_to_existing_method_pipes(self) -> None:
        """Class-level pipes added before method-level pipes."""
        from lexigram.web.pipes import PipeBase
        from lexigram.web.pipes.decorators import use_pipes

        class _PipeA(PipeBase):
            pass

        class _PipeB(PipeBase):
            pass

        pipe_a = _PipeA()
        pipe_b = _PipeB()

        @use_pipes(pipe_a)
        class _MyController:
            def handle(self) -> None:
                pass

        # Simulate a method that already had _lexigram_pipes set
        _MyController.handle._lexigram_pipes = [pipe_b]

        @use_pipes(pipe_a)
        class _MyController2:
            handle = _MyController.handle

        # After re-applying, pipe_a should be prepended
        assert _MyController2.handle._lexigram_pipes[0] is pipe_a


# ---------------------------------------------------------------------------
# responses/adapter.py  (lines 24, 37, 50-52)
# ---------------------------------------------------------------------------


class TestStarletteResponseAdapter:
    def test_json(self) -> None:
        from lexigram.web.responses.adapter import StarletteResponseAdapter

        adapter = StarletteResponseAdapter()
        response = adapter.json({"key": "value"}, status_code=201)
        assert response.status_code == 201

    def test_html(self) -> None:
        from lexigram.web.responses.adapter import StarletteResponseAdapter

        adapter = StarletteResponseAdapter()
        response = adapter.html("<h1>hello</h1>", status_code=200)
        assert response.status_code == 200

    def test_redirect(self) -> None:
        from lexigram.web.responses.adapter import StarletteResponseAdapter

        adapter = StarletteResponseAdapter()
        response = adapter.redirect("/new-url", status_code=302)
        assert response.status_code == 302

    def test_redirect_with_custom_status(self) -> None:
        from lexigram.web.responses.adapter import StarletteResponseAdapter

        adapter = StarletteResponseAdapter()
        response = adapter.redirect("/permanent", status_code=301)
        assert response.status_code == 301


# ---------------------------------------------------------------------------
# routing/__init__.py  (lines 15-29 — __getattr__ lazy loader)
# ---------------------------------------------------------------------------


class TestRoutingInit:
    def test_lazy_load_get_decorator(self) -> None:
        import importlib

        routing = importlib.import_module("lexigram.web.routing")
        get_fn = routing.__getattr__("get")
        assert callable(get_fn)

    def test_lazy_load_post_decorator(self) -> None:
        import importlib

        routing = importlib.import_module("lexigram.web.routing")
        post_fn = routing.__getattr__("post")
        assert callable(post_fn)

    def test_lazy_load_raises_attribute_error(self) -> None:
        import importlib

        routing = importlib.import_module("lexigram.web.routing")
        with pytest.raises(AttributeError):
            routing.__getattr__("nonexistent_method")

    def test_websocket_decorator_returns_callable(self) -> None:
        """Covers line 172 — websocket() calls route() and returns decorator."""
        from lexigram.web.routing.decorators import websocket

        decorator = websocket("/ws/chat")
        assert callable(decorator)


# ---------------------------------------------------------------------------
# security/context.py  (lines 39, 43, 57)
# ---------------------------------------------------------------------------


class TestSecurityContextMethods:
    def test_has_any_role_true(self) -> None:
        from lexigram.web.security.context import SecurityContext

        ctx = SecurityContext(roles=["admin", "user"])
        assert ctx.has_any_role("admin", "moderator") is True

    def test_has_any_role_false(self) -> None:
        from lexigram.web.security.context import SecurityContext

        ctx = SecurityContext(roles=["user"])
        assert ctx.has_any_role("admin", "moderator") is False

    def test_has_all_roles_true(self) -> None:
        from lexigram.web.security.context import SecurityContext

        ctx = SecurityContext(roles=["admin", "user"])
        assert ctx.has_all_roles("admin", "user") is True

    def test_has_all_roles_false(self) -> None:
        from lexigram.web.security.context import SecurityContext

        ctx = SecurityContext(roles=["admin"])
        assert ctx.has_all_roles("admin", "user") is False

    def test_get_security_context_creates_new_when_absent(self) -> None:
        """Covers line 57 — request.state has no security attr."""
        from lexigram.web.security.context import SecurityContext, get_security_context

        class _FakeState:
            pass

        class _FakeRequest:
            state = _FakeState()

        ctx = get_security_context(_FakeRequest())  # type: ignore[arg-type]
        assert isinstance(ctx, SecurityContext)
        assert hasattr(_FakeRequest.state, "security")


# ---------------------------------------------------------------------------
# static/provider.py  (lines 10-12, 16)
# ---------------------------------------------------------------------------


class TestStaticFileProvider:
    def test_init_stores_attrs(self) -> None:
        from lexigram.web.static.provider import StaticFileProvider

        provider = StaticFileProvider(directory="public", prefix="/files", html=True)
        assert provider.directory == "public"
        assert provider.prefix == "/files"
        assert provider.html is True

    def test_create_middleware_returns_config(self) -> None:
        from lexigram.web.static.provider import StaticFileProvider

        provider = StaticFileProvider(directory="assets", prefix="/assets")
        config = provider.create_middleware()
        assert config == {"directory": "assets", "prefix": "/assets", "html": False}

    def test_default_init(self) -> None:
        from lexigram.web.static.provider import StaticFileProvider

        provider = StaticFileProvider()
        assert provider.directory == "static"
        assert provider.prefix == "/static"
        assert provider.html is False


# ---------------------------------------------------------------------------
# transport/__init__.py  (lines 41-47, 52)
# ---------------------------------------------------------------------------


class TestTransportInit:
    def test_lazy_load_json_response(self) -> None:
        import importlib

        transport = importlib.import_module("lexigram.web.transport")
        cls = transport.__getattr__("JSONResponse")
        assert cls is not None

    def test_lazy_load_raises_attribute_error(self) -> None:
        import importlib

        transport = importlib.import_module("lexigram.web.transport")
        with pytest.raises(AttributeError, match="nonexistent_attr"):
            transport.__getattr__("nonexistent_attr")

    def test_dir_includes_lazy_imports(self) -> None:
        import importlib

        transport = importlib.import_module("lexigram.web.transport")
        names = transport.__dir__()
        assert "JSONResponse" in names
        assert "ServerSentEvent" in names


# ---------------------------------------------------------------------------
# transport/sse.py  (lines 37, 45, 89)
# ---------------------------------------------------------------------------


class TestTransportSSE:
    def test_encode_with_event_id(self) -> None:
        from lexigram.web.transport.sse import ServerSentEvent

        event = ServerSentEvent(data="hello", event_id="abc-123")
        encoded = event.encode()
        assert "id: abc-123" in encoded

    def test_encode_with_retry(self) -> None:
        from lexigram.web.transport.sse import ServerSentEvent

        event = ServerSentEvent(data="hello", retry=3000)
        encoded = event.encode()
        assert "retry: 3000" in encoded

    def test_encode_with_non_string_data(self) -> None:
        """Covers line 45 — non-string data serialized via dumps()."""
        from lexigram.web.transport.sse import ServerSentEvent

        event = ServerSentEvent(data={"key": "value", "count": 42})
        encoded = event.encode()
        assert "data:" in encoded

    def test_sse_response_helper(self) -> None:
        from lexigram.web.transport.sse import EventSourceResponse, ServerSentEvent, sse_response

        async def _gen():
            yield ServerSentEvent(data="test")

        response = sse_response(_gen())
        assert isinstance(response, EventSourceResponse)


# ---------------------------------------------------------------------------
# transport/websockets.py  (lines 18, 21, 27, 33, 38)
# ---------------------------------------------------------------------------


class TestTransportWebSocket:
    @pytest.mark.asyncio
    async def test_accept(self) -> None:
        from lexigram.web.transport.websockets import WebSocket

        mock_ws = AsyncMock()
        ws = WebSocket(mock_ws)
        await ws.accept()
        mock_ws.accept.assert_called_once_with(subprotocol=None)

    @pytest.mark.asyncio
    async def test_close(self) -> None:
        from lexigram.web.transport.websockets import WebSocket

        mock_ws = AsyncMock()
        ws = WebSocket(mock_ws)
        await ws.close(code=1001)
        mock_ws.close.assert_called_once_with(code=1001)

    @pytest.mark.asyncio
    async def test_receive_text(self) -> None:
        from lexigram.web.transport.websockets import WebSocket

        mock_ws = AsyncMock()
        mock_ws.receive_text.return_value = "hello"
        ws = WebSocket(mock_ws)
        result = await ws.receive_text()
        assert result == "hello"

    @pytest.mark.asyncio
    async def test_receive_json(self) -> None:
        from lexigram.web.transport.websockets import WebSocket

        mock_ws = AsyncMock()
        mock_ws.receive_json.return_value = {"msg": "hi"}
        ws = WebSocket(mock_ws)
        result = await ws.receive_json()
        assert result == {"msg": "hi"}

    @pytest.mark.asyncio
    async def test_send_bytes(self) -> None:
        from lexigram.web.transport.websockets import WebSocket

        mock_ws = AsyncMock()
        ws = WebSocket(mock_ws)
        await ws.send_bytes(b"binary data")
        mock_ws.send_bytes.assert_called_once_with(b"binary data")


# ---------------------------------------------------------------------------
# routing/result_bridge.py  (line 60 — _serialize_details returns primitive)
# ---------------------------------------------------------------------------


class TestSerializeDetails:
    def test_primitive_passthrough(self) -> None:
        """Covers line 60 — return value for primitives."""
        from lexigram.web.routing.result_bridge import _serialize_details

        assert _serialize_details(42) == 42
        assert _serialize_details("hello") == "hello"
        assert _serialize_details(None) is None

    def test_dict_with_primitive_values(self) -> None:
        """Triggers primitive path (line 60) recursively from dict."""
        from lexigram.web.routing.result_bridge import _serialize_details

        result = _serialize_details({"code": 404, "message": "not found"})
        assert result == {"code": 404, "message": "not found"}


# ---------------------------------------------------------------------------
# middleware/timing.py  (lines 24-25 — non-HTTP scope passthrough)
# ---------------------------------------------------------------------------


class TestTimingMiddleware:
    @pytest.mark.asyncio
    async def test_non_http_scope_passthrough(self) -> None:
        """Covers lines 24-25 — non-HTTP scope passed through unchanged."""
        from lexigram.web.middleware.timing import TimingMiddleware

        calls: list[str] = []

        async def _inner(scope, receive, send) -> None:
            calls.append(scope["type"])

        middleware = TimingMiddleware(_inner)
        await middleware({"type": "websocket"}, None, None)
        assert calls == ["websocket"]


# ---------------------------------------------------------------------------
# websocket/decorators.py  (lines 55, 57, 59 — optional attr overrides)
# ---------------------------------------------------------------------------


class TestWebSocketDecorators:
    def test_websocket_handler_with_all_optional_attrs(self) -> None:
        from lexigram.web.websocket.decorators import websocket_handler

        @websocket_handler(
            "/ws/chat",
            ping_interval=30,
            ping_timeout=10,
            max_connections_per_user=5,
        )
        class _ChatHandler:
            ping_interval = 0
            ping_timeout = 0
            max_connections_per_user = 0

        assert _ChatHandler._ws_path == "/ws/chat"
        assert _ChatHandler.ping_interval == 30
        assert _ChatHandler.ping_timeout == 10
        assert _ChatHandler.max_connections_per_user == 5

    def test_websocket_handler_overrides_ping_interval_only(self) -> None:
        from lexigram.web.websocket.decorators import websocket_handler

        @websocket_handler("/ws", ping_interval=15)
        class _Handler:
            ping_interval = 0

        assert _Handler.ping_interval == 15
        assert _Handler._ws_metadata["ping_interval"] == 15
