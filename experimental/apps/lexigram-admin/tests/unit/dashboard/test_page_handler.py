from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.admin.dashboard.route_integrator import AdminPageHandler


class _FakeService:
    """Fake DI service used as constructor param type."""


class _FakePage:
    """Fake page handler with one DI param."""

    def __init__(self, service: _FakeService) -> None:
        self.service = service

    async def handle(self, request: object) -> AsyncMock:
        return AsyncMock()


class TestAdminPageHandler:
    """Tests for AdminPageHandler ASGI wrapper class."""

    @pytest.mark.asyncio
    async def test_resolves_typed_params_from_container(self) -> None:
        """_resolve_page resolves typed params and constructs the page."""
        service_instance = _FakeService()
        container = MagicMock()
        container.resolve = AsyncMock(return_value=service_instance)

        handler = AdminPageHandler(_FakePage, container)
        page = await handler._resolve_page()

        assert isinstance(page, _FakePage)
        assert page.service is service_instance
        container.resolve.assert_awaited_once_with(_FakeService)

    @pytest.mark.asyncio
    async def test_uses_default_when_param_unresolvable(self) -> None:
        """Params with defaults use the default when type isn't registered."""

        class _PageWithDefault:
            def __init__(self, service: _FakeService, page_size: int = 20) -> None:
                self.service = service
                self.page_size = page_size

            async def handle(self, request: object) -> AsyncMock:
                return AsyncMock()

        service_instance = _FakeService()
        container = MagicMock()
        from lexigram.contracts.exceptions import UnresolvableDependencyError

        container.resolve = AsyncMock(
            side_effect=lambda t: (
                service_instance
                if t is _FakeService
                else (_ for _ in ()).throw(UnresolvableDependencyError(f"{t} not registered"))
            ),
        )

        handler = AdminPageHandler(_PageWithDefault, container)
        page = await handler._resolve_page()

        assert isinstance(page, _PageWithDefault)
        assert page.service is service_instance
        assert page.page_size == 20

    @pytest.mark.asyncio
    async def test_raises_when_param_has_no_type_and_no_default(self) -> None:
        """Missing type hint and no default raises UnresolvableDependencyError."""

        class _BadPage:
            def __init__(self, unknown) -> None:  # no type hint, no default
                self.unknown = unknown

            async def handle(self, request: object) -> AsyncMock:
                return AsyncMock()

        from lexigram.contracts.exceptions import UnresolvableDependencyError

        container = MagicMock()

        handler = AdminPageHandler(_BadPage, container)

        with pytest.raises(UnresolvableDependencyError):
            await handler._resolve_page()

    @pytest.mark.asyncio
    async def test_call_resolves_page_and_sends_response(self) -> None:
        """__call__ resolves page, calls handle, and sends ASGI response."""

        class _SimplePage:
            def __init__(self) -> None:
                pass

            async def handle(self, request: object) -> AsyncMock:
                return AsyncMock()

        container = MagicMock()
        container.resolve = AsyncMock(side_effect=LookupError)

        handler = AdminPageHandler(_SimplePage, container)
        scope: dict = {
            "type": "http",
            "method": "GET",
            "path": "/test",
            "headers": [],
            "query_string": b"",
            "scheme": "http",
            "server": ("test", 80),
            "client": ("127.0.0.1", 1234),
            "asgi": {"version": "3.0", "spec_version": "2.0"},
            "app": None,
            "root_path": "",
        }
        receive = AsyncMock()
        send = AsyncMock()

        await handler(scope, receive, send)
        # Should not raise — the response mock should be callable
        # and awaited with (scope, receive, send)

    @pytest.mark.asyncio
    async def test_call_renders_page_content_results(self) -> None:
        """__call__ renders PageContent from handle() into an HTML response."""

        class _PageContentPage:
            async def handle(self, request: object) -> Any:
                from lexigram.contracts.admin import PageContent
                from lexigram.contracts.admin.widget_content import EmptyContent

                return PageContent(
                    title="Content Page", body=EmptyContent(title="x")
                )

        container = MagicMock()
        container.resolve = AsyncMock(side_effect=LookupError)

        sent: list[dict[str, Any]] = []

        async def fake_send(message: dict[str, Any]) -> None:
            sent.append(message)

        scope: dict[str, Any] = {
            "type": "http",
            "method": "GET",
            "path": "/admin/content",
            "headers": [],
            "query_string": b"",
            "scheme": "http",
            "server": ("test", 80),
            "client": ("127.0.0.1", 1234),
            "asgi": {"version": "3.0", "spec_version": "2.0"},
            "app": None,
            "root_path": "",
        }
        handler = AdminPageHandler(_PageContentPage, container)
        await handler(scope, None, fake_send)
        body = b"".join(
            m["body"] for m in sent if m["type"] == "http.response.body"
        )
        assert b"Content Page" in body


class TestStructuredPageHandlerProtocolDispatch:
    """StructuredPageHandler must dispatch to ``handle(request)`` on
    protocol-style page instances (ManagementPageHandler), not call the
    instance itself."""

    @pytest.mark.asyncio
    async def test_dispatches_to_handle_method(self) -> None:
        from lexigram.admin.dashboard.route_integrator import (
            StructuredPageHandler,
        )
        from lexigram.contracts.admin import PageContent
        from lexigram.contracts.admin.widget_content import EmptyContent

        calls: list[object] = []

        class _ProtocolPage:
            async def handle(self, request: object) -> PageContent:
                calls.append(request)
                return PageContent(title="Protocol Page", body=EmptyContent(title="x"))

        sent: list[dict[str, Any]] = []

        async def fake_send(message: dict[str, Any]) -> None:
            sent.append(message)

        scope: dict[str, Any] = {
            "type": "http",
            "method": "GET",
            "path": "/x",
            "headers": [],
            "query_string": b"",
            "scheme": "http",
            "server": ("test", 80),
            "client": ("127.0.0.1", 1234),
            "asgi": {"version": "3.0", "spec_version": "2.0"},
            "app": None,
            "root_path": "",
        }
        wrapped = StructuredPageHandler(_ProtocolPage())
        await wrapped(scope, None, fake_send)
        assert len(calls) == 1
        body = b"".join(
            m["body"] for m in sent if m["type"] == "http.response.body"
        )
        assert b"Protocol Page" in body

    @pytest.mark.asyncio
    async def test_still_calls_plain_callable_handlers(self) -> None:
        from lexigram.admin.dashboard.route_integrator import (
            StructuredPageHandler,
        )

        calls: list[object] = []

        async def plain_handler(request: object) -> str:
            calls.append(request)
            return "<div>plain</div>"

        sent: list[dict[str, Any]] = []

        async def fake_send(message: dict[str, Any]) -> None:
            sent.append(message)

        scope: dict[str, Any] = {
            "type": "http",
            "method": "GET",
            "path": "/x",
            "headers": [],
            "query_string": b"",
            "scheme": "http",
            "server": ("test", 80),
            "client": ("127.0.0.1", 1234),
            "asgi": {"version": "3.0", "spec_version": "2.0"},
            "app": None,
            "root_path": "",
        }
        await StructuredPageHandler(plain_handler)(scope, None, fake_send)
        assert len(calls) == 1


class TestRegisterPagesWrapping:
    """Route registration must apply exactly one wrapper per handler type."""

    @staticmethod
    def _fake_naming() -> Any:
        from lexigram.admin.dashboard.naming_policy import NamingPolicy

        return NamingPolicy()

    def test_class_handler_wrapped_as_admin_page_handler_only(self) -> None:
        from lexigram.admin.dashboard.route_integrator import (
            StructuredPageHandler,
            _register_pages,
        )
        from lexigram.contracts.admin.types import ManagementPageDefinition

        class _Page:
            async def handle(self, request: object) -> object:
                return None

        collected: list[Any] = []

        class _FakeRouter:
            def add_route(
                self, path: str, method: str, handler: Any, name: str
            ) -> None:
                collected.append(handler)

        _register_pages(
            _FakeRouter(),  # type: ignore[arg-type]
            self._fake_naming(),
            "/admin",
            [
                ManagementPageDefinition(
                    name="p",
                    title="P",
                    contributor="c",
                    route_path="/admin/p",
                    handler=_Page,
                )
            ],
            container=object(),
        )
        assert len(collected) == 1
        assert isinstance(collected[0], AdminPageHandler)
        assert not isinstance(collected[0], StructuredPageHandler)

    def test_instance_handler_wrapped_as_structured_handler_only(self) -> None:
        from lexigram.admin.dashboard.route_integrator import (
            StructuredPageHandler,
            _register_pages,
        )
        from lexigram.contracts.admin.types import ManagementPageDefinition

        class _Page:
            async def handle(self, request: object) -> object:
                return None

        collected: list[Any] = []

        class _FakeRouter:
            def add_route(
                self, path: str, method: str, handler: Any, name: str
            ) -> None:
                collected.append(handler)

        _register_pages(
            _FakeRouter(),  # type: ignore[arg-type]
            self._fake_naming(),
            "/admin",
            [
                ManagementPageDefinition(
                    name="p",
                    title="P",
                    contributor="c",
                    route_path="/admin/p",
                    handler=_Page(),
                )
            ],
            container=object(),
        )
        assert len(collected) == 1
        assert isinstance(collected[0], StructuredPageHandler)
        assert not isinstance(collected[0], AdminPageHandler)
