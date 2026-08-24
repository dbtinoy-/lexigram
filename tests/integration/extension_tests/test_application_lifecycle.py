"""Tests for Application lifecycle events and container-awareness (Phase 4)."""

from __future__ import annotations

import pytest

from lexigram.app.base import Application, AppState
from lexigram.app.events import (
    ApplicationStarted,
    ApplicationStarting,
    ApplicationStopped,
    ApplicationStopping,
    HealthCheckCompleted,
    ProviderBooted,
    ProviderRegistered,
)
from lexigram.app.invoker import Invoker
from lexigram.app.di.provider import CoreProvider
from lexigram.contracts.core import MiddlewarePipelineProtocol

# ---------------------------------------------------------------------------
# Lifecycle event dataclasses
# ---------------------------------------------------------------------------


class TestLifecycleEvents:
    """Tests for lifecycle event dataclasses."""

    def test_application_starting(self) -> None:
        event = ApplicationStarting(app_name="test")
        assert event.app_name == "test"

    def test_application_started(self) -> None:
        event = ApplicationStarted(app_name="test")
        assert event.app_name == "test"

    def test_application_stopping(self) -> None:
        event = ApplicationStopping(app_name="test")
        assert event.app_name == "test"

    def test_application_stopped(self) -> None:
        event = ApplicationStopped(app_name="test", uptime_seconds=1.5)
        assert event.uptime_seconds == 1.5

    def test_provider_registered(self) -> None:
        event = ProviderRegistered(provider_name="core")
        assert event.provider_name == "core"

    def test_provider_booted(self) -> None:
        event = ProviderBooted(provider_name="core", duration_ms=42.0)
        assert event.duration_ms == 42.0

    def test_health_check_completed(self) -> None:
        event = HealthCheckCompleted(status="healthy", details={"db": "ok"})
        assert event.status == "healthy"
        assert event.details["db"] == "ok"

    def test_events_are_frozen(self) -> None:
        event = ApplicationStarting(app_name="test")
        with pytest.raises(AttributeError):
            event.app_name = "other"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Container-aware Application
# ---------------------------------------------------------------------------


class TestContainerAwareApplication:
    """Tests for Application's container-awareness features."""

    def test_middleware_pipeline_registered_as_singleton(self) -> None:
        app = Application(name="test")
        # MiddlewarePipeline should be resolvable from the container via protocol key
        assert app.container.has(MiddlewarePipelineProtocol)

    def test_invoker_registered_as_singleton(self) -> None:
        app = Application(name="test")
        assert app.container.has(Invoker)

    def test_initial_state(self) -> None:
        app = Application(name="test")
        assert app.state == AppState.CREATED
        # Boot timing moved into the ApplicationLifecycle collaborator.
        assert app._lifecycle._start_time is None

    @pytest.mark.asyncio
    async def test_container_resolve_after_boot(self) -> None:
        app = Application(name="test")
        # Register manually to avoid full provider boot
        from lexigram.contracts.events import EventBusProtocol
        from lexigram.testing.memory.event_bus import InMemoryEventBus

        bus = InMemoryEventBus()
        app.container.singleton(EventBusProtocol, bus)

        mw = await app.container.resolve(MiddlewarePipelineProtocol)
        assert isinstance(mw, MiddlewarePipelineProtocol)

    @pytest.mark.asyncio
    async def test_container_resolve_optional_missing(self) -> None:
        app = Application(name="test")

        class NotRegistered:
            pass

        # Container raises on missing registration
        with pytest.raises(Exception):  # noqa: PT011, B017 - broad exception expected
            await app.container.resolve(NotRegistered)
