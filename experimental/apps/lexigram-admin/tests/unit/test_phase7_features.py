"""Tests for Phase 7 features:
- InboxService from lexigram-notification (database notifications)
- Timezone handling (format_datetime, convert_to_timezone, get_user_timezone)
- AutoRefreshWidget / LiveDataTable (live polling)
- DateHierarchyFilter (date hierarchy)
- SimplePagination (no-count pagination)
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# InboxService (lexigram-notification)
# ---------------------------------------------------------------------------
from lexigram.notification import InboxMessage, InboxService, InMemoryInboxStore


class TestInboxMessage:
    def test_has_unique_id(self) -> None:
        m1 = InboxMessage.create(user_id="u1", title="T", body="B")
        m2 = InboxMessage.create(user_id="u1", title="T", body="B")
        assert m1.id != m2.id

    def test_not_read_by_default(self) -> None:
        m = InboxMessage.create(user_id="u1", title="T", body="B")
        assert not m.read

    def test_metadata_defaults_to_empty_dict(self) -> None:
        m = InboxMessage.create(user_id="u1", title="T", body="B")
        assert m.metadata == {}


class TestInboxService:
    @pytest.mark.asyncio
    async def test_send_creates_message(self) -> None:
        svc = InboxService(store=InMemoryInboxStore())
        m = await svc.send("user1", "Hello", "World")
        assert m.user_id == "user1"
        assert m.title == "Hello"

    @pytest.mark.asyncio
    async def test_get_inbox_returns_sent(self) -> None:
        svc = InboxService(store=InMemoryInboxStore())
        await svc.send("user1", "A", "Body A")
        await svc.send("user1", "B", "Body B")
        items = await svc.get_inbox("user1")
        assert len(items) == 2

    @pytest.mark.asyncio
    async def test_get_inbox_unread_only(self) -> None:
        svc = InboxService(store=InMemoryInboxStore())
        m1 = await svc.send("user1", "Unread", "body")
        await svc.send("user1", "Also unread", "body")
        await svc.mark_read(m1.id, "user1")
        items = await svc.get_inbox("user1", unread_only=True)
        assert len(items) == 1

    @pytest.mark.asyncio
    async def test_mark_read_updates_flag(self) -> None:
        svc = InboxService(store=InMemoryInboxStore())
        m = await svc.send("user1", "T", "B")
        assert not m.read
        await svc.mark_read(m.id, "user1")
        fetched = await svc.get_message(m.id)
        assert fetched is not None
        assert fetched.read

    @pytest.mark.asyncio
    async def test_mark_all_read(self) -> None:
        svc = InboxService(store=InMemoryInboxStore())
        await svc.send("user1", "A", "b")
        await svc.send("user1", "B", "b")
        await svc.mark_all_read("user1")
        items = await svc.get_inbox("user1", unread_only=True)
        assert len(items) == 0

    @pytest.mark.asyncio
    async def test_delete_removes_message(self) -> None:
        svc = InboxService(store=InMemoryInboxStore())
        m = await svc.send("user1", "T", "B")
        await svc.delete(m.id, "user1")
        items = await svc.get_inbox("user1")
        assert len(items) == 0

    @pytest.mark.asyncio
    async def test_clear_all(self) -> None:
        svc = InboxService(store=InMemoryInboxStore())
        await svc.send("user1", "A", "b")
        await svc.send("user1", "B", "b")
        count = await svc.clear_all("user1")
        assert count == 2
        items = await svc.get_inbox("user1")
        assert len(items) == 0

    @pytest.mark.asyncio
    async def test_count_unread(self) -> None:
        svc = InboxService(store=InMemoryInboxStore())
        await svc.send("user1", "A", "b")
        await svc.send("user1", "B", "b")
        m3 = await svc.send("user1", "C", "b")
        await svc.mark_read(m3.id, "user1")
        assert await svc.count_unread("user1") == 2

    @pytest.mark.asyncio
    async def test_isolates_by_user(self) -> None:
        svc = InboxService(store=InMemoryInboxStore())
        await svc.send("user1", "U1", "body")
        await svc.send("user2", "U2", "body")
        items = await svc.get_inbox("user1")
        assert len(items) == 1
        assert items[0].user_id == "user1"

    @pytest.mark.asyncio
    async def test_level_stored_in_metadata(self) -> None:
        svc = InboxService(store=InMemoryInboxStore())
        m = await svc.send("u1", "Error", "msg", level="error")
        assert m.metadata.get("level") == "error"

    @pytest.mark.asyncio
    async def test_action_url_stored_in_metadata(self) -> None:
        svc = InboxService(store=InMemoryInboxStore())
        m = await svc.send("u1", "T", "B", action_url="/admin/users/1")
        assert m.metadata.get("action_url") == "/admin/users/1"


# ---------------------------------------------------------------------------
# Timezone handling
# ---------------------------------------------------------------------------

from lexigram.admin.i18n import Translator, convert_to_timezone, get_user_timezone


class TestFormatDatetime:
    def test_format_datetime_no_tz(self) -> None:
        t = Translator()
        dt = datetime(2026, 3, 11, 9, 30, tzinfo=UTC)
        result = t.format_datetime(dt)
        assert "2026-03-11" in result
        assert "09:30" in result

    def test_format_datetime_with_timezone(self) -> None:
        t = Translator()
        # UTC 09:00 → US/Eastern is UTC-5 = 04:00 in winter
        dt = datetime(2026, 3, 11, 9, 0, tzinfo=UTC)
        result = t.format_datetime(dt, timezone="America/New_York")
        # Should be 4 or 5 AM depending on DST
        assert "2026-03-11" in result

    def test_format_datetime_invalid_tz_falls_back(self) -> None:
        t = Translator()
        dt = datetime(2026, 3, 11, 9, 0, tzinfo=UTC)
        # Invalid timezone should not raise — just skip conversion
        result = t.format_datetime(dt, timezone="Not/A/Timezone")
        assert "2026-03-11" in result


class TestConvertToTimezone:
    def test_converts_utc_to_paris(self) -> None:
        dt = datetime(2026, 3, 11, 12, 0, tzinfo=UTC)
        converted = convert_to_timezone(dt, "Europe/Paris")
        # Paris is UTC+1 in March (CET)
        assert converted.hour in (13, 14)  # 13 CET / 14 CEST

    def test_invalid_timezone_returns_original(self) -> None:
        dt = datetime(2026, 3, 11, 12, 0, tzinfo=UTC)
        result = convert_to_timezone(dt, "Invalid/Zone")
        assert result == dt

    def test_non_datetime_returns_unchanged(self) -> None:
        assert convert_to_timezone("not a date", "UTC") == "not a date"


class TestGetUserTimezone:
    def test_reads_from_request_state(self) -> None:
        req = MagicMock()
        req.state.timezone = "America/Los_Angeles"
        assert get_user_timezone(req) == "America/Los_Angeles"

    def test_reads_from_cookie(self) -> None:
        req = MagicMock()
        req.state.timezone = None
        req.cookies = {"admin_timezone": "Europe/Berlin"}
        assert get_user_timezone(req) == "Europe/Berlin"

    def test_falls_back_to_utc(self) -> None:
        req = MagicMock()
        req.state.timezone = None
        req.cookies = {}
        assert get_user_timezone(req) == "UTC"

    def test_custom_default(self) -> None:
        req = MagicMock()
        req.state.timezone = None
        req.cookies = {}
        assert get_user_timezone(req, default="Asia/Tokyo") == "Asia/Tokyo"


# ---------------------------------------------------------------------------
# AutoRefreshWidget
# ---------------------------------------------------------------------------

from lexigram.ui import AutoRefreshWidget, LiveDataTable


class TestAutoRefreshWidget:
    def test_renders_without_error(self) -> None:
        w = AutoRefreshWidget(url="/admin/stats", interval_ms=3000)
        result = w.render()
        assert result is not None

    def test_contains_hx_get(self) -> None:
        w = AutoRefreshWidget(url="/admin/stats")
        html = str(w.render())
        assert "hx-get" in html
        assert "/admin/stats" in html

    def test_contains_hx_trigger_every(self) -> None:
        w = AutoRefreshWidget(url="/admin/stats", interval_ms=5000)
        html = str(w.render())
        assert "every 5000ms" in html

    def test_contains_alpine_paused_state(self) -> None:
        w = AutoRefreshWidget(url="/admin/stats")
        html = str(w.render())
        assert "paused" in html

    def test_pause_controls_rendered(self) -> None:
        w = AutoRefreshWidget(url="/admin/stats", show_controls=True)
        html = str(w.render())
        assert "Pause" in html

    def test_no_controls_when_disabled(self) -> None:
        w = AutoRefreshWidget(url="/admin/stats", show_controls=False)
        html = str(w.render())
        assert "Pause" not in html

    def test_custom_target_id(self) -> None:
        w = AutoRefreshWidget(url="/admin/stats", target_id="my-widget")
        html = str(w.render())
        assert "my-widget" in html

    def test_spinner_element_rendered(self) -> None:
        w = AutoRefreshWidget(url="/admin/stats")
        html = str(w.render())
        assert "htmx-indicator" in html


class TestLiveDataTable:
    def test_inherits_auto_refresh(self) -> None:
        table = LiveDataTable(url="/admin/users/table")
        assert isinstance(table, AutoRefreshWidget)

    def test_default_interval_is_30s(self) -> None:
        table = LiveDataTable(url="/admin/users/table")
        assert table.interval_ms == 30_000

    def test_renders(self) -> None:
        table = LiveDataTable(url="/admin/users/table")
        html = str(table.render())
        assert "/admin/users/table" in html


# ---------------------------------------------------------------------------
# DateHierarchyFilter
# ---------------------------------------------------------------------------

from lexigram.ui import DateHierarchyFilter


class TestDateHierarchyFilter:
    def test_renders_year_buttons_at_root(self) -> None:
        f = DateHierarchyFilter(
            field_name="created_at",
            available_years=[2024, 2025, 2026],
        )
        html = str(f.render())
        assert "2024" in html
        assert "2026" in html

    def test_renders_month_buttons_when_year_selected(self) -> None:
        f = DateHierarchyFilter(field_name="created_at", year=2026)
        html = str(f.render())
        assert "Jan" in html
        assert "Dec" in html

    def test_renders_day_buttons_when_month_selected(self) -> None:
        f = DateHierarchyFilter(field_name="created_at", year=2026, month=3)
        html = str(f.render())
        # March has 31 days
        assert "31" in html

    def test_shows_breadcrumb_when_day_selected(self) -> None:
        f = DateHierarchyFilter(field_name="created_at", year=2026, month=3, day=11)
        html = str(f.render())
        assert "11" in html
        assert "×" in html

    def test_clears_link_present(self) -> None:
        f = DateHierarchyFilter(field_name="created_at", year=2026, month=3)
        html = str(f.render())
        assert "×" in html

    def test_htmx_attrs_on_links(self) -> None:
        f = DateHierarchyFilter(
            field_name="created_at",
            available_years=[2026],
            base_url="/admin/users",
        )
        html = str(f.render())
        assert "hx-get" in html
        assert "hx-push-url" in html

    def test_field_name_in_url_params(self) -> None:
        f = DateHierarchyFilter(
            field_name="published_at",
            available_years=[2026],
            base_url="/admin/posts",
        )
        html = str(f.render())
        assert "published_at__year" in html

    def test_february_has_28_days_in_non_leap_year(self) -> None:
        f = DateHierarchyFilter(field_name="created_at", year=2026, month=2)
        html = str(f.render())
        assert "28" in html
        # No 29th in 2026 (not a leap year)
        assert "created_at__day=29" not in html


# ---------------------------------------------------------------------------
# SimplePagination
# ---------------------------------------------------------------------------

from lexigram.ui import SimplePagination


class TestSimplePagination:
    def test_renders(self) -> None:
        p = SimplePagination(page=1, per_page=20, has_next_page=True)
        result = p.render()
        assert result is not None

    def test_shows_page_number(self) -> None:
        p = SimplePagination(page=3, per_page=20, has_next_page=True)
        html = str(p.render())
        assert "Page 3" in html

    def test_next_link_when_has_next(self) -> None:
        p = SimplePagination(page=1, per_page=20, has_next_page=True, base_url="/admin/users")
        html = str(p.render())
        assert "Next" in html
        assert "page=2" in html

    def test_no_next_link_when_no_next(self) -> None:
        p = SimplePagination(page=5, per_page=20, has_next_page=False)
        html = str(p.render())
        # Next should be disabled (rendered as span, not anchor)
        assert "page=6" not in html

    def test_prev_disabled_on_first_page(self) -> None:
        p = SimplePagination(page=1, per_page=20, has_next_page=True)
        html = str(p.render())
        assert "page=0" not in html

    def test_prev_link_on_second_page(self) -> None:
        p = SimplePagination(page=2, per_page=20, has_next_page=True, base_url="/admin/users")
        html = str(p.render())
        assert "page=1" in html

    def test_htmx_attrs_on_links(self) -> None:
        p = SimplePagination(page=1, per_page=20, has_next_page=True, base_url="/admin/users")
        html = str(p.render())
        assert "hx-get" in html
        assert "hx-push-url" in html

    def test_no_total_count_in_html(self) -> None:
        # Simple pagination must NOT mention "of X pages"
        p = SimplePagination(page=1, per_page=20, has_next_page=True)
        html = str(p.render())
        assert "of " not in html
