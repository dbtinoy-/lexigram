from __future__ import annotations

import pytest

from lexigram.secrets.rotation import RotationDecorator, RotationSchedule
from lexigram.testing.fakes import FakeRotatableSecretStore


class TestRotationSchedule:
    def test_creation(self) -> None:
        sched = RotationSchedule(max_age_seconds=100.0)
        assert sched.max_age_seconds == 100.0
        assert sched.warning_before_seconds == 86400.0

    def test_custom_warning(self) -> None:
        sched = RotationSchedule(max_age_seconds=100.0, warning_before_seconds=10.0)
        assert sched.warning_before_seconds == 10.0


class TestRotationDecorator:
    @pytest.fixture
    def store(self) -> FakeRotatableSecretStore:
        return FakeRotatableSecretStore()

    @pytest.fixture
    def short_schedule(self) -> RotationSchedule:
        return RotationSchedule(max_age_seconds=0.0, warning_before_seconds=0.0)

    @pytest.fixture
    def long_schedule(self) -> RotationSchedule:
        return RotationSchedule(max_age_seconds=999999.0, warning_before_seconds=100.0)

    async def test_get_rotated_returns_value(
        self,
        store: FakeRotatableSecretStore,
        long_schedule: RotationSchedule,
    ) -> None:
        await store.set("key", "hello")
        decorator = RotationDecorator(store, long_schedule)
        value, rotated = await decorator.get_rotated("key")
        assert value == "hello"
        assert not rotated

    async def test_get_rotated_triggers_when_expired(
        self,
        store: FakeRotatableSecretStore,
        short_schedule: RotationSchedule,
    ) -> None:
        await store.set("key", "hello")
        decorator = RotationDecorator(store, short_schedule)
        value, rotated = await decorator.get_rotated("key")
        assert value != "hello"
        assert rotated

    async def test_check_warnings_returns_none_when_fresh(
        self,
        store: FakeRotatableSecretStore,
        long_schedule: RotationSchedule,
    ) -> None:
        await store.set("key", "fresh")
        decorator = RotationDecorator(store, long_schedule)
        warning = await decorator.check_warnings("key")
        assert warning is None

    async def test_check_warnings_returns_message_when_due(
        self,
        store: FakeRotatableSecretStore,
        short_schedule: RotationSchedule,
    ) -> None:
        await store.set("key", "stale")
        decorator = RotationDecorator(store, short_schedule)
        warning = await decorator.check_warnings("key")
        assert warning is not None
        assert "approaching rotation deadline" in warning


class TestRotationGraceBufferEviction:
    @pytest.fixture
    def store(self) -> FakeRotatableSecretStore:
        return FakeRotatableSecretStore()

    async def test_expired_rotation_is_evicted_on_get_rotated(self, store) -> None:
        from datetime import UTC, datetime, timedelta

        from lexigram.secrets.types import VersionedSecret

        await store.set("key", "hello")
        decorator = RotationDecorator(
            store, RotationSchedule(max_age_seconds=999999.0, grace_period_seconds=0.0)
        )
        old_secret = await store.get_current_version("key")
        decorator._rotated_at["key"] = datetime.now(UTC) - timedelta(seconds=1)
        decorator._rotated_old["key"] = VersionedSecret(
            key="key",
            version=1,
            value=old_secret.value,
            created_at=old_secret.created_at,
        )
        await decorator.get_rotated("key")
        assert "key" not in decorator._rotated_old
        assert "key" not in decorator._rotated_at

    async def test_buffer_is_bounded(self, store) -> None:
        decorator = RotationDecorator(store, RotationSchedule(max_age_seconds=0.0))
        for i in range(80):
            await store.set(f"key-{i}", f"value-{i}")
        for i in range(80):
            await decorator.get_rotated(f"key-{i}")
        assert len(decorator._rotated_old) <= 64

    async def test_grace_period_still_serves_old_value(self, store) -> None:
        await store.set("key", "hello")
        decorator = RotationDecorator(
            store, RotationSchedule(max_age_seconds=0.0, grace_period_seconds=3600.0)
        )
        await decorator.get_rotated("key")
        served = await decorator.get_current_version("key")
        assert str(served.value) == "hello"
