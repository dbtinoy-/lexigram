"""Demo configuration bound from ``application.yaml``.

Blueprint reference example (Wave 0 Task A). Every runtime knob lives in
YAML next to the demo; Python contains zero literal configuration.

Why explicit binding instead of provider ``config_key`` auto-injection:
the framework's ``ConfigProvider`` reads ``application.yaml`` from the
**current working directory**, so auto-injection silently yields defaults
whenever a demo runs from anywhere else (repo root, hub process, tests).
Binding here against an ``__file__``-anchored absolute path keeps one load
point, honors ``LEX_*`` overrides and ``LEX_PROFILE`` overlays, and works in
standalone, embedded-hub, and test contexts alike.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from lexigram.cache.config.top_level import CacheConfig
from lexigram.config.main import LexigramConfig
from lexigram.web.config import WebConfig

APP_YAML = Path(__file__).resolve().parents[2] / "application.yaml"


@dataclass(frozen=True)
class RatesConfig:
    """Typed ``demo:`` section of the resilient-rates application.yaml.

    Attributes:
        upstream_scenario: Initial upstream health scenario
            (``healthy | flaky | down | slow``).
    """

    upstream_scenario: str = "healthy"


def bind_application() -> tuple[WebConfig, CacheConfig, RatesConfig]:
    """Bind the web/cache/demo sections from this demo's application.yaml.

    Returns:
        ``(web_config, cache_config, demo_config)`` ready for module and
        provider wiring. ``LEX_`` environment overrides and ``LEX_PROFILE``
        overlays are applied by the loader. Cache TTL is owned by the cache
        package (``cache.backends[].default_ttl``), not by this demo.
    """
    lex = LexigramConfig.from_yaml(APP_YAML)
    return (
        lex.get_section("web", WebConfig),
        lex.get_section("cache", CacheConfig),
        lex.get_section("demo", RatesConfig),
    )


__all__ = ["APP_YAML", "RatesConfig", "bind_application"]
