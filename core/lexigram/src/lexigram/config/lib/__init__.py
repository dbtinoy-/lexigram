"""Configuration library components for Lexigram Framework.

This module provides the foundational building blocks for configuration:
- Sources: Where config data comes from (files, env, CLI, .env)
- Merge: Dict merging and env-var interpolation helpers
- Registry: Extension registry for dynamic config sections
- Validation: Cross-config validation orchestration
- Watcher: Polling-based config file change detection
"""

from __future__ import annotations

from lexigram.config.lib.merge import (
    deep_merge,
    interpolate_env_vars,
    interpolate_string,
)
from lexigram.config.lib.registry import ConfigRegistry
from lexigram.config.lib.sources import (
    CliConfigSource,
    ConfigLoader,
    ConfigSource,
    DirectoryConfigSource,
    DotEnvSource,
    EnvironmentConfigSource,
    FileConfigSource,
)
from lexigram.config.lib.validation import validate_all_configs
from lexigram.config.lib.watcher import ConfigWatcher

__all__ = [
    # Sources
    "CliConfigSource",
    "ConfigLoader",
    # Registry
    "ConfigRegistry",
    "ConfigSource",
    # Watcher
    "ConfigWatcher",
    "DirectoryConfigSource",
    "DotEnvSource",
    "EnvironmentConfigSource",
    "FileConfigSource",
    # Merge
    "deep_merge",
    "interpolate_env_vars",
    "interpolate_string",
    # Validation
    "validate_all_configs",
]
