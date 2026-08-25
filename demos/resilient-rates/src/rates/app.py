"""Application composition root for the resilient-rates demo.

``create_app`` is the only place that knows how the modules fit together
(starter pattern). Configuration comes from this demo's ``application.yaml``
unless an explicit ``LexigramConfig`` is provided.
"""

from __future__ import annotations

from lexigram.app.base import Application
from lexigram.cache.config.top_level import CacheConfig
from lexigram.cache.module import CacheModule
from lexigram.config.main import LexigramConfig
from lexigram.resilience.module import ResilienceModule
from lexigram.web.config import WebConfig
from lexigram.web.module import WebModule
from rates.config import APP_YAML, RatesConfig
from rates.controllers.api import RatesApiController
from rates.di.provider import RatesProvider
from rates.ui.pages import RatesPageController


def create_app(config: LexigramConfig | None = None) -> Application:
    """Create the configured (not yet started) rates application."""
    config = config or LexigramConfig.from_yaml(APP_YAML)
    web_config = WebConfig.from_yaml(APP_YAML)
    cache_config = CacheConfig.from_yaml(APP_YAML)
    demo_config = RatesConfig.from_yaml(APP_YAML)

    app = Application(name="resilient-rates", config=config)
    app.add_modules(
        [
            ResilienceModule.configure(),
            CacheModule.configure(cache_config),
            WebModule.configure(
                web_config=web_config,
                controllers=[RatesApiController, RatesPageController],
            ),
        ]
    )
    app.add_provider(RatesProvider(config=demo_config, cache_config=cache_config))
    return app


__all__ = ["create_app"]
