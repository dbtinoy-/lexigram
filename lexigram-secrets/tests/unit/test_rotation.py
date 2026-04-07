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
