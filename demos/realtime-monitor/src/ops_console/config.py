"""Demo-specific configuration — ``demo:`` section of application.yaml.

The ``RealtimeConfig`` dataclass declares the typed ``demo:`` section with
field-level defaults.  Environment variable overrides use the double-
underscore convention: ``LEX_DEMO__HEARTBEAT_INTERVAL_SECONDS=5`` sets
``heartbeat_interval_seconds = 5``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from lexigram.config import BaseConfig
from lexigram.validation import Field


@dataclass(init=False)
class RealtimeConfig(BaseConfig):
    """Typed ``demo:`` section of the realtime monitor application.yaml."""

    config_section: ClassVar[str] = "demo"

    heartbeat_interval_seconds: float = Field(
        15.0, description="Delay between synthetic heartbeat events"
    )
    history_size: int = Field(100, description="Events retained for SSE replay")
    queue_capacity: int = Field(
        100, description="Per-subscriber buffer before oldest-event drop"
    )


__all__ = ["RealtimeConfig"]
