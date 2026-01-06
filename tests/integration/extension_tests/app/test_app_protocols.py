"""Tests for app protocols."""

import pytest

from lexigram.app.protocols import AppLifecycleProtocol


class TestAppLifecycleProtocol:
    """Tests for AppLifecycleProtocol."""

    def test_protocol_is_protocol(self) -> None:
        """Test AppLifecycleProtocol is a Protocol."""
        from typing import Protocol as TypingProtocol

        assert issubclass(AppLifecycleProtocol, TypingProtocol)

    def test_protocol_has_start_method(self) -> None:
        """Test protocol defines start method."""
        assert hasattr(AppLifecycleProtocol, "start")
        assert callable(AppLifecycleProtocol.start)

    def test_protocol_has_stop_method(self) -> None:
        """Test protocol defines stop method."""
        assert hasattr(AppLifecycleProtocol, "stop")
        assert callable(AppLifecycleProtocol.stop)

    def test_protocol_exported(self) -> None:
        """Test protocol is exported."""
        from lexigram.app.protocols import __all__ as protocols_all

        assert "AppLifecycleProtocol" in protocols_all

    def test_protocol_defines_async_methods(self) -> None:
        """Test protocol defines async methods."""
        import inspect

        start_method = getattr(AppLifecycleProtocol, "start", None)
        stop_method = getattr(AppLifecycleProtocol, "stop", None)

        assert start_method is not None
        assert stop_method is not None

        assert inspect.iscoroutinefunction(start_method)
        assert inspect.iscoroutinefunction(stop_method)