"""Tests for application events."""

import pytest

from lexigram.app.events import (
    ApplicationStarted,
    ApplicationStarting,
    ApplicationStopped,
    ApplicationStopping,
    HealthCheckCompleted,
    ProviderBooted,
    ProviderRegistered,
)


class TestApplicationStarting:
    """Tests for ApplicationStarting event."""

    def test_create_event(self) -> None:
        """Test creating an ApplicationStarting event."""
        event = ApplicationStarting(app_name="test-app")
        assert event.app_name == "test-app"

    def test_event_is_frozen(self) -> None:
        """Test that event is frozen."""
        event = ApplicationStarting(app_name="test-app")
        with pytest.raises(AttributeError):
            event.app_name = "other"

    def test_event_is_dataclass(self) -> None:
        """Test event is a dataclass."""
        event = ApplicationStarting(app_name="test-app")
        assert hasattr(event, "__dataclass_fields__")


class TestApplicationStarted:
    """Tests for ApplicationStarted event."""

    def test_create_event(self) -> None:
        """Test creating an ApplicationStarted event."""
        event = ApplicationStarted(app_name="test-app")
        assert event.app_name == "test-app"

    def test_event_is_frozen(self) -> None:
        """Test that event is frozen."""
        event = ApplicationStarted(app_name="test-app")
        with pytest.raises(AttributeError):
            event.app_name = "other"


class TestApplicationStopping:
    """Tests for ApplicationStopping event."""

    def test_create_event(self) -> None:
        """Test creating an ApplicationStopping event."""
        event = ApplicationStopping(app_name="test-app")
        assert event.app_name == "test-app"


class TestApplicationStopped:
    """Tests for ApplicationStopped event."""

    def test_create_event(self) -> None:
        """Test creating an ApplicationStopped event."""
        event = ApplicationStopped(app_name="test-app", uptime_seconds=60.5)
        assert event.app_name == "test-app"
        assert event.uptime_seconds == 60.5


class TestProviderRegistered:
    """Tests for ProviderRegistered event."""

    def test_create_event(self) -> None:
        """Test creating a ProviderRegistered event."""
        event = ProviderRegistered(provider_name="my-provider")
        assert event.provider_name == "my-provider"


class TestProviderBooted:
    """Tests for ProviderBooted event."""

    def test_create_event(self) -> None:
        """Test creating a ProviderBooted event."""
        event = ProviderBooted(provider_name="my-provider", duration_ms=150.5)
        assert event.provider_name == "my-provider"
        assert event.duration_ms == 150.5


class TestHealthCheckCompleted:
    """Tests for HealthCheckCompleted event."""

    def test_create_event(self) -> None:
        """Test creating a HealthCheckCompleted event."""
        event = HealthCheckCompleted(status="healthy")
        assert event.status == "healthy"

    def test_create_event_with_details(self) -> None:
        """Test creating event with details."""
        details = {"database": "ok", "cache": "ok"}
        event = HealthCheckCompleted(status="healthy", details=details)
        assert event.status == "healthy"
        assert event.details == details

    def test_default_details_is_empty(self) -> None:
        """Test default details is empty dict."""
        event = HealthCheckCompleted(status="healthy")
        assert event.details == {}


class TestEventsExported:
    """Tests that all events are exported."""

    def test_all_exported(self) -> None:
        """Test that all events are in __all__."""
        from lexigram.app.events import __all__ as events_all

        assert "ApplicationStarted" in events_all
        assert "ApplicationStarting" in events_all
        assert "ApplicationStopped" in events_all
        assert "ApplicationStopping" in events_all
        assert "HealthCheckCompleted" in events_all
        assert "ProviderBooted" in events_all
        assert "ProviderRegistered" in events_all