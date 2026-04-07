"""{{ project_name }} application — Gear 2 bootstrap."""
from __future__ import annotations

from lexigram.app import Application
from lexigram.cache.di.provider import CacheProvider
from lexigram.config import LexigramConfig
from lexigram.sql.di.provider import DatabaseProvider
from lexigram.web import WebProvider


def create_app() -> Application:
    """Create and return the application instance."""
    cache = CacheProvider()
    cache.configure({"backends": [{"name": "memory", "type": "memory", "default": True}]})

    application = Application(
        name="{{ project_name }}",
        config=LexigramConfig.from_yaml("application.yaml"),
    )
    application.add_provider(DatabaseProvider())
    application.add_provider(cache)
    application.add_provider(WebProvider.auto_discover("{{ package_name }}.modules"))
    return application


# ASGI entry point
app = create_app()

__all__ = ["app", "create_app"]
