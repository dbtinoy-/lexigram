"""Tests for the NotificationsInboxPage admin page."""

from __future__ import annotations

import re
from types import SimpleNamespace

import pytest


def _plain(html: str) -> str:
    """Strip tags so summary/pagination text can be asserted simply."""
    return re.sub(r"<[^>]+>", "", html)


class FakeUser:
    """Stub user attached to requests."""

    id = "user-1"


class FakeRequest:
    """Minimal ASGI request stand-in."""

    user = FakeUser()
    query_params: dict[str, str] = {}
    url = SimpleNamespace(path="/admin/notifications")


class TestNotificationsInboxPage:
    """Unit tests for the inbox page renderer."""

    @pytest.mark.asyncio
    async def test_page_renders_messages_and_unread_count(self) -> None:
        from lexigram.notification.admin import NotificationsInboxPage
        from lexigram.notification.inbox.service import InboxService

        service = InboxService()
        await service.send("user-1", title="Hello", body="World")

        page = NotificationsInboxPage(inbox_service=service)
        response = await page.handle(FakeRequest())  # type: ignore[arg-type]
        html = response.body.decode()

        assert "Notifications" in html
        assert "1 unread" in html
        assert "Hello" in html
        assert "World" in html
        assert "Showing 1 to 1 of 1 results" in _plain(html)

    @pytest.mark.asyncio
    async def test_page_renders_empty_state_for_anon(self) -> None:
        from lexigram.notification.admin import NotificationsInboxPage

        page = NotificationsInboxPage()
        request = FakeRequest()
        request.user = None
        response = await page.handle(request)  # type: ignore[arg-type]

        assert "No notifications" in response.body.decode()

    @pytest.mark.asyncio
    async def test_page_marks_all_read_button_posts(self) -> None:
        from lexigram.notification.admin import NotificationsInboxPage

        page = NotificationsInboxPage()
        response = await page.handle(FakeRequest())  # type: ignore[arg-type]
        html = response.body.decode()

        assert 'hx-post="/admin/notifications/read-all"' in html
        assert "Mark all read" in html

    @pytest.mark.asyncio
    async def test_page_honors_limit(self) -> None:
        from lexigram.notification.admin import NotificationsInboxPage
        from lexigram.notification.inbox.service import InboxService

        service = InboxService()
        for i in range(5):
            await service.send("user-1", title=f"T{i}", body=f"B{i}")

        page = NotificationsInboxPage(inbox_service=service)
        request = FakeRequest()
        request.query_params = {"limit": "2"}
        response = await page.handle(request)  # type: ignore[arg-type]
        html = response.body.decode()

        assert 'hx-post="/admin/notifications/read-all"' in html
        assert "T4" in html
        assert "T3" in html
        assert "T0" not in html
        assert "Showing 1 to 2 of 5 results" in _plain(html)

    @pytest.mark.asyncio
    async def test_page_renders_pagination_for_many(self) -> None:
        from lexigram.notification.admin import NotificationsInboxPage
        from lexigram.notification.inbox.service import InboxService

        service = InboxService()
        for i in range(25):
            await service.send("user-1", title=f"t{i}", body="b")

        page = NotificationsInboxPage(inbox_service=service)
        response = await page.handle(FakeRequest())  # type: ignore[arg-type]
        html = response.body.decode()

        assert "Showing 1 to 20 of 25 results" in _plain(html)
        assert "t24" in html
        assert "t0" not in html
        assert 'hx-get="/admin/notifications?page=2&amp;per_page=20"' in html

    @pytest.mark.asyncio
    async def test_page_paginates_page_two(self) -> None:
        from lexigram.notification.admin import NotificationsInboxPage
        from lexigram.notification.inbox.service import InboxService

        service = InboxService()
        for i in range(5):
            await service.send("user-1", title=f"T{i}", body=f"B{i}")

        page = NotificationsInboxPage(inbox_service=service)
        request = FakeRequest()
        request.query_params = {"page": "2", "per_page": "2"}
        response = await page.handle(request)  # type: ignore[arg-type]
        html = response.body.decode()

        assert "Showing 3 to 4 of 5 results" in _plain(html)
        assert "T2" in html
        assert "T1" in html
        assert "T4" not in html  # page 2 of [T4, T3, T2, T1, T0]

    @pytest.mark.asyncio
    async def test_page_extra_page_has_remaining_item(self) -> None:
        from lexigram.notification.admin import NotificationsInboxPage
        from lexigram.notification.inbox.service import InboxService

        service = InboxService()
        for i in range(5):
            await service.send("user-1", title=f"T{i}", body=f"B{i}")

        page = NotificationsInboxPage(inbox_service=service)
        request = FakeRequest()
        request.query_params = {"page": "3", "per_page": "2"}
        response = await page.handle(request)  # type: ignore[arg-type]
        html = response.body.decode()

        assert "T0" in html
        assert "T4" not in html
        assert "Showing 5 to 5 of 5 results" in _plain(html)

    @pytest.mark.asyncio
    async def test_page_clamps_page_beyond_end(self) -> None:
        from lexigram.notification.admin import NotificationsInboxPage
        from lexigram.notification.inbox.service import InboxService

        service = InboxService()
        for i in range(5):
            await service.send("user-1", title=f"T{i}", body=f"B{i}")

        page = NotificationsInboxPage(inbox_service=service)
        request = FakeRequest()
        request.query_params = {"page": "99", "per_page": "2"}
        response = await page.handle(request)  # type: ignore[arg-type]
        html = response.body.decode()

        # page 99 clamps to the last page (3 of 3)
        assert "Showing 5 to 5 of 5 results" in _plain(html)
        assert "T0" in html

    @pytest.mark.asyncio
    async def test_page_renders_size_selector(self) -> None:
        from lexigram.notification.admin import NotificationsInboxPage
        from lexigram.notification.inbox.service import InboxService

        service = InboxService()
        for i in range(25):
            await service.send("user-1", title=f"t{i}", body="b")

        page = NotificationsInboxPage(inbox_service=service)
        response = await page.handle(FakeRequest())  # type: ignore[arg-type]
        html = response.body.decode()

        assert 'name="per_page"' in html
        assert 'hx-get="/admin/notifications?page=1"' in html
