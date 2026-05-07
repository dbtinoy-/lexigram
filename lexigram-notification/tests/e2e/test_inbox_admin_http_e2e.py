"""End-to-end test: contributor inbox endpoints + page over real HTTP.

Builds a minimal Starlette app from :class:`NotificationAdminContributor`
routes, attaches a synthetic user via middleware, and drives the full
stack (routing, path params, JSON serialization, page rendering) with an
ASGI HTTP client.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

httpx = pytest.importorskip("httpx")

from starlette.applications import Starlette  # noqa: E402
from starlette.middleware import Middleware  # noqa: E402
from starlette.middleware.base import BaseHTTPMiddleware  # noqa: E402
from starlette.requests import Request  # noqa: E402
from starlette.responses import Response  # noqa: E402
from starlette.routing import Route  # noqa: E402

from lexigram.notification.admin import NotificationAdminContributor  # noqa: E402
from lexigram.notification.inbox.service import InboxService  # noqa: E402

_USER_ID = "user-e2e"


class FakeUser:
    """Stub user attached to requests by the test middleware."""

    id = _USER_ID


class _UserMiddleware(BaseHTTPMiddleware):
    """Attach a synthetic authenticated user, as admin auth middleware does."""

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        request.scope["user"] = FakeUser()
        request.scope["state"] = {"user": FakeUser()}
        return await call_next(request)


class FakeResolver:
    """Minimal container resolver returning the shared InboxService."""

    def __init__(self, service: InboxService) -> None:
        self._service = service

    async def resolve(self, service_type: Any) -> Any:
        return self._service


def _resolve_page_handler(dotted: str) -> Any:
    """Resolve a ``module:Class`` handler string (admin boot mechanism)."""
    module_path, _, name = dotted.partition(":")
    module = __import__(module_path, fromlist=[name])
    return getattr(module, name)


@dataclass
class _E2ECtx:
    """Client plus the InboxService its handlers are bound to."""

    client: Any
    service: InboxService


def _build_app(
    contributor: NotificationAdminContributor, service: InboxService
) -> Starlette:
    """Assemble the contributor's routes + page into a Starlette app."""
    routes = [
        Route(spec.path, spec.handler, methods=[spec.method])
        for spec in contributor.get_routes()
    ]
    page_cls = _resolve_page_handler(
        contributor.get_management_pages()[0].handler  # type: ignore[union-attr]
    )
    routes.append(Route("/admin/notifications", page_cls(inbox_service=service).handle))
    return Starlette(routes=routes, middleware=[Middleware(_UserMiddleware)])


@pytest.fixture
async def ctx() -> _E2ECtx:
    """Client wired to the contributor using a shared InboxService."""
    contributor = NotificationAdminContributor()
    service = InboxService()
    await contributor.on_admin_boot(FakeResolver(service))

    app = _build_app(contributor, service)
    transport = httpx.ASGITransport(app=app)
    client = httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"X-Requested-With": "fetch"},
    )
    yield _E2ECtx(client=client, service=service)
    await client.aclose()


class TestInboxHttpE2E:
    """Exercises the inbox endpoints over real HTTP."""

    @pytest.mark.asyncio
    async def test_get_inbox_returns_messages_and_unread_count(
        self, ctx: _E2ECtx
    ) -> None:
        await ctx.service.send(_USER_ID, title="Hello", body="World")
        await ctx.service.send(_USER_ID, title="Second", body="Again")

        response = await ctx.client.get("/admin/notifications/inbox")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        payload = response.json()
        assert payload["unread_count"] == 2
        assert [n["title"] for n in payload["notifications"]] == ["Second", "Hello"]
        first = payload["notifications"][0]
        assert first["message"] == "Again"
        assert first["read"] is False
        assert "timestamp" in first

    @pytest.mark.asyncio
    async def test_mark_read_round_trip_updates_inbox(self, ctx: _E2ECtx) -> None:
        message = await ctx.service.send(_USER_ID, title="Hello", body="World")

        response = await ctx.client.post(f"/admin/notifications/read/{message.id}")
        assert response.status_code == 200
        assert response.json() == {"ok": True}

        payload = (await ctx.client.get("/admin/notifications/inbox")).json()
        assert payload["unread_count"] == 0
        assert payload["notifications"][0]["read"] is True

    @pytest.mark.asyncio
    async def test_mark_read_unknown_id_is_noop(self, ctx: _E2ECtx) -> None:
        response = await ctx.client.post("/admin/notifications/read/does-not-exist")
        assert response.status_code == 200
        assert response.json() == {"ok": True}

    @pytest.mark.asyncio
    async def test_mark_all_read_clears_unread(self, ctx: _E2ECtx) -> None:
        await ctx.service.send(_USER_ID, title="A", body="1")
        await ctx.service.send(_USER_ID, title="B", body="2")

        response = await ctx.client.post("/admin/notifications/read-all")
        assert response.status_code == 200
        assert response.json() == {"ok": True}

        payload = (await ctx.client.get("/admin/notifications/inbox")).json()
        assert payload["unread_count"] == 0
        assert all(n["read"] for n in payload["notifications"])

    @pytest.mark.asyncio
    async def test_bell_happy_path_fetch_and_read(self, ctx: _E2ECtx) -> None:
        """The bell's exact request sequence: fetch inbox, read one, refetch."""
        await ctx.service.send(_USER_ID, title="PageFeed", body="Seeded")

        payload = (await ctx.client.get("/admin/notifications/inbox")).json()
        target = payload["notifications"][0]

        await ctx.client.post(f"/admin/notifications/read/{target['id']}")

        after = (await ctx.client.get("/admin/notifications/inbox")).json()
        assert after["unread_count"] == 0

    @pytest.mark.asyncio
    async def test_inbox_page_renders_over_http(self, ctx: _E2ECtx) -> None:
        await ctx.service.send(_USER_ID, title="PageFeed", body="Seeded")

        response = await ctx.client.get("/admin/notifications")
        assert response.status_code == 200
        html = response.text
        assert "Notifications" in html
        assert "1 unread" in html
        assert "PageFeed" in html
        assert 'hx-post="/admin/notifications/read-all"' in html


class TestInboxAdminPageContainerIntegration:
    """The page through the real AdminPageHandler + container DI path."""

    @pytest.mark.asyncio
    async def test_page_resolved_from_container_and_wrapped_in_shell(
        self,
    ) -> None:
        """Boot the production admin page handler with a real container.

        ``AdminPageHandler`` resolves the page's constructor DI parameters
        from the container at request time and wraps the response in the
        admin shell for non-fragment requests.  Content seeded via the
        container's own InboxService must appear in the shell-wrapped
        response (a resolution failure would fall back to the placeholder
        page instead).
        """
        pytest.importorskip("lexigram.admin")
        from lexigram.admin.dashboard.route_integrator import AdminPageHandler
        from lexigram.di import Container

        service = InboxService()
        container = Container()
        container.singleton(InboxService, service)

        contributor = NotificationAdminContributor()
        page_cls = _resolve_page_handler(
            contributor.get_management_pages()[0].handler  # type: ignore[union-attr]
        )
        endpoint = AdminPageHandler(page_cls, container)

        app = Starlette(
            routes=[Route("/admin/notifications", endpoint)],
            middleware=[Middleware(_UserMiddleware)],
        )
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            await service.send(_USER_ID, title="ShellPage", body="ViaContainer")
            response = await client.get("/admin/notifications")

        assert response.status_code == 200
        html = response.text
        assert "ShellPage" in html
        assert "ViaContainer" in html
        assert "<html" in html or "<body" in html
        assert 'hx-post="/admin/notifications/read-all"' in html


class TestInboxHttpAnonymous:
    """Unauthenticated requests must not leak inbox state."""

    @pytest.mark.asyncio
    async def test_anon_requests_are_empty_and_rejected(self) -> None:
        contributor = NotificationAdminContributor()
        app = Starlette(
            routes=[
                Route(spec.path, spec.handler, methods=[spec.method])
                for spec in contributor.get_routes()
            ]
        )
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as anon:
            payload = (await anon.get("/admin/notifications/inbox")).json()
            assert payload == {"unread_count": 0, "notifications": []}
            assert (await anon.post("/admin/notifications/read-all")).status_code == 401
            assert (await anon.post("/admin/notifications/read/x")).status_code == 401
