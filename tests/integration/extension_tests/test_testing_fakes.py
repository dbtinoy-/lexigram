"""Tests for lexigram-testing fakes — FakeEventBus, FakeLogger, FakeClock, TestProvider."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from lexigram.contracts.domain.events import DomainEvent
from lexigram.testing.fakes import (
    Clock,
    FakeClock,
    FakeEventBus,
    FakeLogger,
    LogEntry,
    SystemClock,
)
from lexigram.testing.mocks.test_provider import LifecycleTracker

# ---------------------------------------------------------------------------
# Test events
# ---------------------------------------------------------------------------


class UserCreated(DomainEvent):
    user_id: str = ""


class UserDeleted(DomainEvent):
    user_id: str = ""


# ===========================================================================
# Clock Protocol + SystemClock + FakeClock
# ===========================================================================


class TestClockProtocol:
    """Verify Clock protocol implementation."""

    def test_system_clock_satisfies_protocol(self) -> None:
        assert isinstance(SystemClock(), Clock)

    def test_fake_clock_satisfies_protocol(self) -> None:
        assert isinstance(FakeClock(), Clock)


class TestSystemClock:
    """Tests for SystemClock — real time access."""

    def test_now_returns_utc(self) -> None:
        clock = SystemClock()
        dt = clock.now()
        assert dt.tzinfo is not None

    def test_monotonic_returns_float(self) -> None:
        assert isinstance(SystemClock().monotonic(), float)

    def test_time_returns_float(self) -> None:
        assert isinstance(SystemClock().time(), float)


class TestFakeClock:
    """Tests for FakeClock — deterministic time control."""

    def test_default_now(self) -> None:
        clock = FakeClock()
        assert clock.now().tzinfo is not None

    def test_custom_start_time(self) -> None:
        start = datetime(2026, 6, 15, 12, 0, 0, tzinfo=UTC)
        clock = FakeClock(now=start)
        assert clock.now() == start

    def test_advance_moves_time_forward(self) -> None:
        start = datetime(2026, 1, 1, tzinfo=UTC)
        clock = FakeClock(now=start)
        clock.advance(3600)
        assert clock.now() == start + timedelta(hours=1)

    def test_advance_accumulates(self) -> None:
        start = datetime(2026, 1, 1, tzinfo=UTC)
        clock = FakeClock(now=start)
        clock.advance(60)
        clock.advance(60)
        assert clock.now() == start + timedelta(minutes=2)

    def test_tick_advances_one_second(self) -> None:
        start = datetime(2026, 1, 1, tzinfo=UTC)
        clock = FakeClock(now=start)
        clock.tick()
        assert clock.now() == start + timedelta(seconds=1)

    def test_freeze_resets_to_new_time(self) -> None:
        clock = FakeClock()
        target = datetime(2030, 12, 31, tzinfo=UTC)
        clock.freeze(target)
        assert clock.now() == target

    def test_freeze_resets_offset(self) -> None:
        clock = FakeClock()
        clock.advance(999)
        target = datetime(2030, 1, 1, tzinfo=UTC)
        clock.freeze(target)
        assert clock.now() == target

    def test_monotonic_starts_at_zero(self) -> None:
        clock = FakeClock()
        assert clock.monotonic() == 0.0

    def test_monotonic_advances_with_clock(self) -> None:
        clock = FakeClock()
        clock.advance(5.0)
        assert clock.monotonic() == 5.0

    def test_time_returns_unix_timestamp(self) -> None:
        start = datetime(2026, 1, 1, tzinfo=UTC)
        clock = FakeClock(now=start)
        assert clock.time() == start.timestamp()


# ===========================================================================
# FakeEventBus
# ===========================================================================


class TestFakeEventBus:
    """Tests for FakeEventBus — event recording and assertions."""

    @pytest.mark.asyncio
    async def test_publish_records_event(self) -> None:
        bus = FakeEventBus()
        event = UserCreated(user_id="1")
        await bus.publish(event)
        assert len(bus.published) == 1
        assert bus.published[0] is event

    @pytest.mark.asyncio
    async def test_published_returns_copy(self) -> None:
        bus = FakeEventBus()
        await bus.publish(UserCreated(user_id="1"))
        assert bus.published is not bus._published

    @pytest.mark.asyncio
    async def test_published_of_type(self) -> None:
        bus = FakeEventBus()
        await bus.publish(UserCreated(user_id="1"))
        await bus.publish(UserDeleted(user_id="2"))
        await bus.publish(UserCreated(user_id="3"))
        created = bus.published_of_type(UserCreated)
        assert len(created) == 2

    @pytest.mark.asyncio
    async def test_subscribe_and_dispatch(self) -> None:
        bus = FakeEventBus()
        received: list[DomainEvent] = []

        async def handler(event: UserCreated) -> None:
            received.append(event)

        bus.subscribe(UserCreated, handler)
        await bus.publish(UserCreated(user_id="abc"))
        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_unsubscribe_removes_handler(self) -> None:
        bus = FakeEventBus()
        received: list[DomainEvent] = []

        async def handler(event: UserCreated) -> None:
            received.append(event)

        bus.subscribe(UserCreated, handler)
        bus.unsubscribe(UserCreated, handler)
        await bus.publish(UserCreated(user_id="gone"))
        assert len(received) == 0

    @pytest.mark.asyncio
    async def test_priority_ordering(self) -> None:
        bus = FakeEventBus()
        order: list[str] = []

        async def first(e: DomainEvent) -> None:
            order.append("first")

        async def second(e: DomainEvent) -> None:
            order.append("second")

        bus.subscribe(UserCreated, second, priority=10)
        bus.subscribe(UserCreated, first, priority=1)
        await bus.publish(UserCreated(user_id="x"))
        assert order == ["first", "second"]

    def test_clear_resets_published(self) -> None:
        bus = FakeEventBus()
        bus._published.append(UserCreated(user_id="1"))
        bus.clear()
        assert bus.published == []


class TestFakeEventBusAssertions:
    """Tests for FakeEventBus assertion helpers."""

    @pytest.mark.asyncio
    async def test_assert_published_passes(self) -> None:
        bus = FakeEventBus()
        await bus.publish(UserCreated(user_id="1"))
        bus.assert_published(UserCreated)

    @pytest.mark.asyncio
    async def test_assert_published_fails(self) -> None:
        bus = FakeEventBus()
        with pytest.raises(AssertionError, match="Expected UserCreated"):
            bus.assert_published(UserCreated)

    @pytest.mark.asyncio
    async def test_assert_published_count(self) -> None:
        bus = FakeEventBus()
        await bus.publish(UserCreated(user_id="1"))
        await bus.publish(UserCreated(user_id="2"))
        bus.assert_published(UserCreated, count=2)

    @pytest.mark.asyncio
    async def test_assert_published_count_mismatch(self) -> None:
        bus = FakeEventBus()
        await bus.publish(UserCreated(user_id="1"))
        with pytest.raises(AssertionError, match="Expected 3"):
            bus.assert_published(UserCreated, count=3)

    @pytest.mark.asyncio
    async def test_assert_published_with_attrs(self) -> None:
        bus = FakeEventBus()
        await bus.publish(UserCreated(user_id="abc"))
        bus.assert_published(UserCreated, user_id="abc")

    @pytest.mark.asyncio
    async def test_assert_published_attrs_no_match(self) -> None:
        bus = FakeEventBus()
        await bus.publish(UserCreated(user_id="abc"))
        with pytest.raises(AssertionError, match="No UserCreated event matched"):
            bus.assert_published(UserCreated, user_id="xyz")

    @pytest.mark.asyncio
    async def test_assert_not_published_passes(self) -> None:
        bus = FakeEventBus()
        bus.assert_not_published(UserCreated)

    @pytest.mark.asyncio
    async def test_assert_not_published_fails(self) -> None:
        bus = FakeEventBus()
        await bus.publish(UserCreated(user_id="1"))
        with pytest.raises(AssertionError, match="NOT be published"):
            bus.assert_not_published(UserCreated)

    @pytest.mark.asyncio
    async def test_assert_published_once(self) -> None:
        bus = FakeEventBus()
        await bus.publish(UserCreated(user_id="only"))
        bus.assert_published_once(UserCreated, user_id="only")


# ===========================================================================
# FakeLogger
# ===========================================================================


class TestFakeLogger:
    """Tests for FakeLogger — log capture and assertions."""

    def test_log_levels_captured(self) -> None:
        logger = FakeLogger()
        logger.debug("d")
        logger.info("i")
        logger.warning("w")
        logger.error("e")
        logger.critical("c")
        logger.exception("x")
        assert len(logger.entries) == 6
        assert [e.level for e in logger.entries] == [
            "debug", "info", "warning", "error", "critical", "exception",
        ]

    def test_entries_are_log_entry(self) -> None:
        logger = FakeLogger()
        logger.info("hello")
        entry = logger.entries[0]
        assert isinstance(entry, LogEntry)
        assert entry.message == "hello"
        assert entry.level == "info"

    def test_kwargs_captured_as_context(self) -> None:
        logger = FakeLogger()
        logger.info("action", user_id="abc", count=5)
        entry = logger.entries[0]
        assert entry.context["user_id"] == "abc"
        assert entry.context["count"] == 5

    def test_bind_creates_child_with_context(self) -> None:
        logger = FakeLogger()
        child = logger.bind(request_id="r123")
        child.info("child_msg")
        entry = logger.entries[0]  # shared entries list
        assert entry.context["request_id"] == "r123"

    def test_bind_shares_entries(self) -> None:
        logger = FakeLogger()
        child = logger.bind(key="value")
        child.info("from_child")
        # Both parent and child see the same entries
        assert len(logger.entries) == 1
        assert len(child.entries) == 1

    def test_unbind_removes_keys(self) -> None:
        logger = FakeLogger(bound_context={"a": 1, "b": 2})
        child = logger.unbind("a")
        child.info("msg")
        entry = child.entries[0]
        assert "a" not in entry.context
        assert entry.context.get("b") == 2

    def test_clear_resets(self) -> None:
        logger = FakeLogger()
        logger.info("msg")
        logger.clear()
        assert logger.entries == []

    def test_entries_returns_copy(self) -> None:
        logger = FakeLogger()
        logger.info("msg")
        assert logger.entries is not logger._entries


class TestFakeLoggerAssertions:
    """Tests for FakeLogger assertion helpers."""

    def test_assert_logged_passes(self) -> None:
        logger = FakeLogger()
        logger.info("user_created")
        logger.assert_logged("info", "user_created")

    def test_assert_logged_partial_match(self) -> None:
        logger = FakeLogger()
        logger.error("something went wrong with user 123")
        logger.assert_logged("error", "went wrong")

    def test_assert_logged_fails(self) -> None:
        logger = FakeLogger()
        logger.debug("other")
        with pytest.raises(AssertionError, match="Expected log entry"):
            logger.assert_logged("info", "missing")

    def test_assert_not_logged_passes(self) -> None:
        logger = FakeLogger()
        logger.info("safe")
        logger.assert_not_logged("error")

    def test_assert_not_logged_with_message_passes(self) -> None:
        logger = FakeLogger()
        logger.info("safe")
        logger.assert_not_logged("info", "dangerous")

    def test_assert_not_logged_fails(self) -> None:
        logger = FakeLogger()
        logger.error("boom")
        with pytest.raises(AssertionError, match="Expected no log entry"):
            logger.assert_not_logged("error")

    def test_assert_not_logged_with_message_fails(self) -> None:
        logger = FakeLogger()
        logger.error("boom happened")
        with pytest.raises(AssertionError, match="Expected no log entry"):
            logger.assert_not_logged("error", "boom")


# ===========================================================================
# TestProvider
# ===========================================================================


class TestTestProvider:
    """Tests for TestProvider lifecycle tracking."""

    def test_initial_state(self) -> None:
        p = LifecycleTracker(name="test")
        assert p.register_called is False
        assert p.boot_called is False
        assert p.shutdown_called is False

    @pytest.mark.asyncio
    async def test_register_sets_flag(self) -> None:
        p = LifecycleTracker()
        await p.register(container=None)
        assert p.register_called is True

    @pytest.mark.asyncio
    async def test_boot_sets_flag(self) -> None:
        p = LifecycleTracker()
        await p.boot(container=None)
        assert p.boot_called is True

    @pytest.mark.asyncio
    async def test_shutdown_sets_flag(self) -> None:
        p = LifecycleTracker()
        await p.shutdown()
        assert p.shutdown_called is True

    @pytest.mark.asyncio
    async def test_reset_clears_flags(self) -> None:
        p = LifecycleTracker()
        await p.register(container=None)
        await p.boot(container=None)
        await p.shutdown()
        p.reset()
        assert p.register_called is False
        assert p.boot_called is False
        assert p.shutdown_called is False

    def test_default_name(self) -> None:
        assert LifecycleTracker().name == "test"

    def test_custom_name(self) -> None:
        assert LifecycleTracker(name="custom").name == "custom"
