from __future__ import annotations

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
        scope: dict = {"type": "http", "method": "GET", "path": "/test"}
        receive = AsyncMock()
        send = AsyncMock()

        await handler(scope, receive, send)
        # Should not raise — the response mock should be callable
        # and awaited with (scope, receive, send)
