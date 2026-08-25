"""Demo configuration bound from ``application.yaml``.

Blueprint reference wiring: knobs live in YAML next to the demo; Python binds
them explicitly via ``LexigramConfig.get_section`` because provider
auto-injection reads configuration from the current working directory and is
therefore unreliable for demos run from a repository root.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from lexigram.config.main import LexigramConfig
from lexigram.web.config import WebConfig

APP_YAML = Path(__file__).resolve().parents[2] / "application.yaml"


@dataclass(frozen=True)
class RealtimeConfig:
    """Typed ``demo:`` section of the realtime monitor application.yaml.

    Attributes:
        heartbeat_interval_seconds: Delay between synthetic heartbeat events.
        history_size: Events retained for SSE replay.
        queue_capacity: Per-subscriber buffer before oldest-event drop.
    """

    heartbeat_interval_seconds: float = 15.0
    history_size: int = 100
    queue_capacity: int = 100


def load_lex_config() -> LexigramConfig:
    """Load the demo's full ``LexigramConfig`` from application.yaml."""
    return LexigramConfig.from_yaml(APP_YAML)


def bind_application() -> tuple[WebConfig, RealtimeConfig]:
    """Bind the web and demo sections from this demo's application.yaml.

    Returns:
        ``(web_config, demo_config)`` ready for module/provider wiring.
        ``LEX_`` environment overrides and ``LEX_PROFILE`` overlays are
        applied by the loader.
    """
    lex = LexigramConfig.from_yaml(APP_YAML)
    return (
        lex.get_section("web", WebConfig),
        lex.get_section("demo", RealtimeConfig),
    )


def bind_web() -> WebConfig:
    """Bind the ``web`` section for server wiring."""
    return LexigramConfig.from_yaml(APP_YAML).get_section("web", WebConfig)


__all__ = ["APP_YAML", "RealtimeConfig", "bind_application", "bind_web"]
