"""Unit tests for SessionUserCache (R16).

Covers TTL expiry, size-bounded eviction, single/user-wide invalidation,
guest exclusion, and the TTL-0 disable switch. Full plan:
docs/09-01-2026/12-session-user-cache.md.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from lexigram.admin.auth.services.session_user_cache import SessionUserCache


class FakeClock:
    """Deterministic monotonic time source."""

    def __init__(self) -> None:
        self.t = 1000.0

    def __call__(self) -> float:
        return self.t

    def advance(self, seconds: float) -> None:
        self.t += seconds


def _user(user_id: str = "u-1") -> MagicMock:
    user = MagicMock()
    user.user_id = user_id
    return user


def test_hit_within_ttl() -> None:
    clock = FakeClock()
    cache = SessionUserCache(ttl_seconds=5, time_source=clock)
    user = _user()
    cache.put("sid-1", user)
    clock.advance(4.9)
    assert cache.get("sid-1") is user


def test_miss_after_ttl_expiry_and_entry_reaped() -> None:
    clock = FakeClock()
    cache = SessionUserCache(ttl_seconds=5, time_source=clock)
    cache.put("sid-1", _user())
    clock.advance(5.0)
    assert cache.get("sid-1") is None
    assert len(cache) == 0  # lazily reaped


def test_unknown_session_misses() -> None:
    cache = SessionUserCache(ttl_seconds=5)
    assert cache.get("nope") is None


def test_ttl_zero_disables_cache() -> None:
    cache = SessionUserCache(ttl_seconds=0)
    assert cache.enabled is False
    cache.put("sid-1", _user())
    assert cache.get("sid-1") is None
    assert len(cache) == 0


def test_guest_and_empty_ids_never_cached() -> None:
    cache = SessionUserCache(ttl_seconds=5)
    guest = _user("guest")
    cache.put("sid-1", guest)
    empty = _user("")
    cache.put("sid-2", empty)
    cache.put("", _user("u-9"))
    assert len(cache) == 0


def test_invalidate_single_session() -> None:
    cache = SessionUserCache(ttl_seconds=5)
    cache.put("sid-1", _user("u-1"))
    cache.put("sid-2", _user("u-2"))
    cache.invalidate("sid-1")
    assert cache.get("sid-1") is None
    assert cache.get("sid-2") is not None


def test_invalidate_user_drops_all_their_sessions_only() -> None:
    cache = SessionUserCache(ttl_seconds=5)
    cache.put("sid-a1", _user("u-a"))
    cache.put("sid-a2", _user("u-a"))
    cache.put("sid-b1", _user("u-b"))
    cache.invalidate_user("u-a")
    assert cache.get("sid-a1") is None
    assert cache.get("sid-a2") is None
    assert cache.get("sid-b1") is not None


def test_invalidate_user_empty_id_is_noop() -> None:
    cache = SessionUserCache(ttl_seconds=5)
    cache.put("sid-1", _user("u-1"))
    cache.invalidate_user("")
    assert cache.get("sid-1") is not None


def test_max_entries_evicts_oldest() -> None:
    cache = SessionUserCache(ttl_seconds=60, max_entries=3)
    for i in range(3):
        cache.put(f"sid-{i}", _user(f"u-{i}"))
    cache.put("sid-3", _user("u-3"))  # overflows → sid-0 evicted
    assert cache.get("sid-0") is None
    assert cache.get("sid-1") is not None
    assert cache.get("sid-3") is not None
    assert len(cache) == 3


def test_reput_refreshes_ttl_without_eviction() -> None:
    clock = FakeClock()
    cache = SessionUserCache(ttl_seconds=5, max_entries=3, time_source=clock)
    cache.put("sid-1", _user("u-1"))
    clock.advance(4.0)
    cache.put("sid-1", _user("u-1"))  # refresh, still 1 entry
    clock.advance(4.0)  # 8s after first put, 4s after refresh
    assert cache.get("sid-1") is not None
    assert len(cache) == 1


def test_clear_drops_everything() -> None:
    cache = SessionUserCache(ttl_seconds=5)
    cache.put("sid-1", _user("u-1"))
    cache.put("sid-2", _user("u-2"))
    cache.clear()
    assert len(cache) == 0
    assert cache.get("sid-1") is None
