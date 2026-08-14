import pytest

from lexigram.admin.dashboard.naming_policy import NamingPolicy, NameCollisionError


def test_namespace_is_applied() -> None:
    p = NamingPolicy()
    assert p.namespaced("cache", "hit_miss_ratio") == "cache.hit_miss_ratio"


def test_already_namespaced_passes_through() -> None:
    p = NamingPolicy()
    assert p.namespaced("cache", "cache.hit_miss_ratio") == "cache.hit_miss_ratio"


def test_collision_warn_mode_does_not_raise(caplog: pytest.LogCaptureFixture) -> None:
    p = NamingPolicy()
    p.register("widget", "cache.hit_miss_ratio")
    p.register("widget", "cache.hit_miss_ratio")
    assert any("collision" in r.message.lower() for r in caplog.records)


def test_collision_error_mode_raises() -> None:
    p = NamingPolicy(mode="error")
    p.register("widget", "cache.hit_miss_ratio")
    with pytest.raises(NameCollisionError):
        p.register("widget", "cache.hit_miss_ratio")
