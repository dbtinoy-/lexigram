"""Configuration public exports for the app subsystem."""

from __future__ import annotations

from lexigram.app.config.discovery import ModuleDiscoveryConfig
from lexigram.app.config.models import AppConfig

__all__ = [
    "AppConfig",
    "ModuleDiscoveryConfig",
]
