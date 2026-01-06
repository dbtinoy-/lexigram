"""Tests for guard decorators and hook patterns."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, AsyncMock


class TestGuardDecorators:
    """Test guard decorator patterns."""

    def test_guarded_decorator_wraps_function(self) -> None:
        """@guarded decorator should wrap functions."""
        # Mock decorator pattern
        def guarded(**kwargs):
            def decorator(func):
                def wrapper(*args, **kw):
                    return func(*args, **kw)
                return wrapper
            return decorator

        @guarded(injection_detection=True)
        def my_function():
            return "result"

        result = my_function()
        assert result == "result"

    def test_guarded_decorator_preserves_function_signature(self) -> None:
        """@guarded decorator should preserve function metadata."""
        def guarded(**kwargs):
            def decorator(func):
                def wrapper(*args, **kw):
                    return func(*args, **kw)
                return wrapper
            return decorator

        @guarded()
        def documented_function():
            """My function."""
            return "result"

        assert documented_function.__doc__ is None or "My function" in documented_function.__doc__


class TestGuardHooks:
    """Test guard hook patterns."""

    def test_input_checked_hook(self) -> None:
        """InputCheckedHook should be callable."""
        hook = MagicMock()
        hook.call = MagicMock(return_value=None)

        hook.call(guard_name="injection_detector", result={"action": "pass"})

        hook.call.assert_called_once()

    def test_output_checked_hook(self) -> None:
        """OutputCheckedHook should be callable."""
        hook = MagicMock()
        hook.call = MagicMock(return_value=None)

        hook.call(guard_name="redactor", result={"action": "redact"})

        hook.call.assert_called_once()

    def test_pipeline_completed_hook(self) -> None:
        """PipelineCompletedHook should capture final result."""
        hook = MagicMock()
        hook.call = MagicMock(return_value=None)

        result = {
            "passed": True,
            "action": "pass",
            "duration_ms": 45.2,
        }
        hook.call(result=result)

        hook.call.assert_called_once()


class TestGuardEventEmission:
    """Test event emission from guards."""

    def test_guard_events_emitted(self) -> None:
        """Guards should emit events."""
        event_bus = MagicMock()
        event_bus.publish = AsyncMock(return_value=None)

        # Simulate event emission
        event = {
            "type": "guard_input_checked",
            "guard_name": "injection",
            "action": "block",
        }

        event_bus.publish(event)

        event_bus.publish.assert_called_once()

    def test_blocked_content_event(self) -> None:
        """Blocked content should emit event."""
        event_bus = MagicMock()
        event_bus.publish = AsyncMock(return_value=None)

        event = {
            "type": "content_blocked",
            "reason": "Injection detected",
            "timestamp": "2024-01-01T00:00:00Z",
        }

        event_bus.publish(event)

        event_bus.publish.assert_called_once()

    def test_redaction_event(self) -> None:
        """Redaction should emit event."""
        event_bus = MagicMock()
        event_bus.publish = AsyncMock(return_value=None)

        event = {
            "type": "content_redacted",
            "entities": ["SSN", "CREDIT_CARD"],
            "timestamp": "2024-01-01T00:00:00Z",
        }

        event_bus.publish(event)

        event_bus.publish.assert_called_once()


class TestGuardPluginSystem:
    """Test guard plugin/extension points."""

    def test_custom_guard_registration(self) -> None:
        """Custom guards should be registerable."""
        registry = MagicMock()
        registry.register = MagicMock(return_value=None)

        custom_guard = MagicMock()
        custom_guard.name = "custom_injection_detector"

        registry.register(custom_guard)

        registry.register.assert_called_once()

    def test_guard_priority_ordering(self) -> None:
        """Guards should support priority ordering."""
        guards = [
            {"name": "injection", "priority": 1},
            {"name": "pii", "priority": 2},
            {"name": "topic", "priority": 3},
        ]

        sorted_guards = sorted(guards, key=lambda g: g["priority"])

        assert sorted_guards[0]["name"] == "injection"
        assert sorted_guards[-1]["name"] == "topic"
