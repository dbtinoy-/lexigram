"""Tests for app/factory module."""

import pytest

from lexigram.app.factory import create_app
from lexigram.app.base import Application


class TestCreateApp:
    """Tests for create_app factory function."""

    def test_create_app_default_name(self) -> None:
        """Test create_app with default name."""
        app = create_app()
        assert isinstance(app, Application)
        assert app.name == "lexigram-app"

    def test_create_app_custom_name(self) -> None:
        """Test create_app with custom name."""
        app = create_app(name="my-custom-app")
        assert isinstance(app, Application)
        assert app.name == "my-custom-app"

    def test_create_app_with_none_config(self) -> None:
        """Test create_app with explicit None config."""
        app = create_app(config=None)
        assert isinstance(app, Application)

    def test_create_app_returns_unbooted(self) -> None:
        """Test that create_app returns unbooted application."""
        app = create_app()
        assert app.state.name == "CREATED"
