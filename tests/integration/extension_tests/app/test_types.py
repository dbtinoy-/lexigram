"""Tests for app/types module."""

import pytest

from lexigram.app.types import AppState


class TestAppState:
    """Tests for AppState enum."""

    def test_app_state_created(self) -> None:
        """Test AppState has CREATED."""
        assert AppState.CREATED is not None

    def test_app_state_starting(self) -> None:
        """Test AppState has STARTING."""
        assert AppState.STARTING is not None

    def test_app_state_stopping(self) -> None:
        """Test AppState has STOPPING."""
        assert AppState.STOPPING is not None

    def test_app_state_stopped(self) -> None:
        """Test AppState has STOPPED."""
        assert AppState.STOPPED is not None

    def test_app_state_is_strenum(self) -> None:
        """Test AppState is a string enum."""
        assert isinstance(AppState.CREATED, str)
