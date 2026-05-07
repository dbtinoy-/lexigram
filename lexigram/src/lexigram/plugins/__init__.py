"""Entry-point plugin discovery and boot-time enable/disable state."""

from __future__ import annotations

from lexigram.plugins.discovery import discover_plugins, discover_providers
from lexigram.plugins.engine import PluginEngineProvider
from lexigram.plugins.module import PluginsModule
from lexigram.plugins.state import load_disabled, save_disabled, update_disabled

__all__ = [
    "PluginEngineProvider",
    "PluginsModule",
    "discover_plugins",
    "discover_providers",
    "load_disabled",
    "save_disabled",
    "update_disabled",
]
