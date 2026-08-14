"""{{ project_name }} application."""
from __future__ import annotations

from lexigram.app import Application
from lexigram.config import LexigramConfig
from lexigram.web import WebProvider


def create_app() -> Application:
    """Create and return the application instance."""
    application = Application(
        name="{{ project_name }}",
        config=LexigramConfig.from_yaml("application.yaml"),
    )
    application.add_provider(WebProvider.auto_discover("{{ package_name }}.controllers"))
    return application


# ASGI entry point
app = create_app()

__all__ = ["app", "create_app"]
