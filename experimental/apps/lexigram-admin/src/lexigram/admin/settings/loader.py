"""Configuration loader with layered sources.

Loads configuration from:
1. Pydantic defaults (AdminConfig)
2. YAML file (application.yaml admin: section)
3. Environment variables (LEX_ADMIN_*)
4. Runtime overrides

Supports hot-reload for runtime configuration updates.
All operations are async-only for consistency with the lexigram ecosystem.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import os
from pathlib import Path
from typing import Any, TypeVar

import aiofiles
import yaml

from lexigram import serialization as json
from lexigram.admin.config import AdminConfig
from lexigram.config import ConfigLoader as BaseConfigLoader
from lexigram.domain import DomainModel

T = TypeVar("T")

__all__ = ["AdminConfigLoader"]


@dataclass(init=False)
class ConfigPath(DomainModel):
    """Immutable path reference for nested config access."""

    parts: tuple[str, ...]

    @classmethod
    def from_string(cls, path: str) -> ConfigPath:
        """Create from dot-separated string."""
        return cls(parts=tuple(path.split(".")))

    def __str__(self) -> str:
        return ".".join(self.parts)


class AdminConfigLoader:
    """Layered configuration loader for lexigram-admin.

    Configuration priority (highest to lowest):
    1. Runtime overrides (hot-reloadable)
    2. Environment variables (LEX_ADMIN__*)
    3. YAML file configuration
    4. Pydantic model defaults

    Usage:
        loader = AdminConfigLoader()
        config = await loader.load()

    Hot reload:
        await loader.reload()

    Environment variable mapping:
        admin.auth.session_lifetime -> LEX_ADMIN__AUTH__SESSION_LIFETIME
    """

    ENV_PREFIX = "LEX_ADMIN__"
    YAML_SECTION = "admin"

    def __init__(
        self,
        yaml_path: Path | None = None,
        base_loader: BaseConfigLoader | None = None,
        defaults: dict[str, Any] | None = None,
    ):
        self._yaml_path = yaml_path
        self._base_loader = base_loader
        self._defaults = defaults or {}
        self._config: AdminConfig | None = None
        self._runtime_overrides: dict[str, Any] = {}
        self._reload_callbacks: list[Callable[[AdminConfig], None]] = []
        self._yaml_path_used: Path | None = None
        self._provenance: dict[str, str] = {}

    @property
    def yaml_path(self) -> Path | None:
        """Return the YAML file used by the last load, when one was found."""
        return self._yaml_path_used

    def get_provenance(self) -> dict[str, str]:
        """Return a copy of effective leaf-path source labels."""
        return dict(self._provenance)

    @property
    def config(self) -> AdminConfig:
        """Get current config (raises if not loaded)."""
        if self._config is None:
            raise RuntimeError(
                "Config not loaded. Call load() first or use get_config().",
            )
        return self._config

    async def load(self) -> AdminConfig:
        """Load configuration from all sources.

        Returns:
            Merged AdminConfig instance
        """
        # Layer 1: Start with defaults from the model itself. We fill source
        # labels after validation so fields omitted by every input layer are
        # still represented as declared model defaults.
        config_data: dict[str, Any] = {}
        self._provenance = {}

        # Explicit loader defaults are still defaults: they fill gaps before
        # deployment-owned YAML and environment layers, rather than silently
        # overriding an operator's environment variable.
        self._deep_merge(config_data, self._defaults)
        self._mark_provenance(self._defaults, "loader constructor default")

        # Layer 2: Load from YAML
        yaml_data = await self._load_yaml()
        self._deep_merge(config_data, yaml_data)
        self._mark_provenance(yaml_data, self._yaml_source_label())

        # Layer 3: Apply environment variables
        env_data = self._load_env()
        self._deep_merge(config_data, env_data)
        self._mark_provenance(env_data, "environment override")

        # Layer 4: Apply runtime overrides
        self._deep_merge(config_data, self._runtime_overrides)
        self._mark_provenance(self._runtime_overrides, "runtime override")

        # Construct config model
        self._config = AdminConfig.model_validate(config_data)
        try:
            effective = self._config.model_dump(mode="python")
        except (AttributeError, TypeError, ValueError):
            effective = vars(self._config)
        for path in self._leaf_paths(effective):
            self._provenance.setdefault(path, "declared model default")
        return self._config

    async def reload(self) -> AdminConfig:
        """Hot-reload configuration.

        Re-reads YAML and environment, preserving runtime overrides.
        Notifies all registered reload callbacks.

        Returns:
            Newly loaded AdminConfig instance
        """
        old_config = self._config
        new_config = await self.load()

        # Notify callbacks if config changed
        if old_config != new_config:
            for callback in self._reload_callbacks:
                callback(new_config)

        return new_config

    def on_reload(self, callback: Callable[[AdminConfig], None]) -> None:
        """Register a callback to be notified on config reload."""
        self._reload_callbacks.append(callback)

    def set_runtime(self, path: str, value: Any) -> None:
        """Set a runtime override (survives reload).

        Args:
            path: Dot-separated config path (e.g., "auth.session_lifetime")
            value: Value to set
        """
        self._set_nested(self._runtime_overrides, path.split("."), value)

    def clear_runtime(self, path: str | None = None) -> None:
        """Clear runtime overrides.

        Args:
            path: Specific path to clear, or None for all
        """
        if path is None:
            self._runtime_overrides.clear()
        else:
            self._delete_nested(self._runtime_overrides, path.split("."))

    def get(self, path: str, default: T = None) -> T | Any:  # type: ignore[assignment]
        """Get a config value by dot-path.

        Args:
            path: Dot-separated path (e.g., "auth.session_lifetime")
            default: Default if path not found

        Returns:
            Config value or default
        """
        if self._config is None:
            return default

        obj: Any = self._config
        for part in path.split("."):
            if hasattr(obj, part):
                obj = getattr(obj, part)
            elif isinstance(obj, dict) and part in obj:
                obj = obj[part]
            else:
                return default
        return obj

    @staticmethod
    def _leaf_paths(value: Any, prefix: str = "") -> list[str]:
        """Return dotted paths for scalar leaves in a nested value."""
        if isinstance(value, dict):
            paths: list[str] = []
            for key, child in value.items():
                path = f"{prefix}.{key}" if prefix else str(key)
                paths.extend(AdminConfigLoader._leaf_paths(child, path))
            return paths
        if isinstance(value, (list, tuple)):
            paths = []
            for index, child in enumerate(value):
                paths.extend(AdminConfigLoader._leaf_paths(child, f"{prefix}[{index}]"))
            return paths or ([prefix] if prefix else [])
        return [prefix] if prefix else []

    def _mark_provenance(self, value: Any, source: str, prefix: str = "") -> None:
        """Mark every supplied leaf, allowing later layers to overwrite it."""
        for path in self._leaf_paths(value, prefix):
            self._provenance[path] = source

    def _yaml_source_label(self) -> str:
        """Describe the YAML source without exposing file contents."""
        if self._yaml_path_used is None:
            return "YAML/application config"
        return f"YAML ({self._yaml_path_used})"

    async def _load_yaml(self) -> dict[str, Any]:
        """Load configuration from YAML file.

        Tries paths in order:
        1. Explicit yaml_path if provided
        2. Common paths: application.yaml, application.yml, config/application.yaml

        Returns:
            Dict of admin configuration from YAML, or empty dict
        """
        paths_to_try = []
        self._yaml_path_used = None

        if self._yaml_path:
            paths_to_try.append(self._yaml_path)

        # Common paths
        paths_to_try.extend(
            [
                Path.cwd() / "application.yaml",
                Path.cwd() / "application.yml",
                Path.cwd() / "config" / "application.yaml",
            ],
        )

        for path in paths_to_try:
            if path.exists():
                try:
                    async with aiofiles.open(path) as f:
                        content = await f.read()
                        data = yaml.safe_load(content) or {}
                        if not isinstance(data, dict):
                            continue
                        self._yaml_path_used = path
                        section = data.get(self.YAML_SECTION, {})
                        return section if isinstance(section, dict) else {}
                except (yaml.YAMLError, ValueError, OSError):
                    continue

        return {}

    def _load_env(self) -> dict[str, Any]:
        """Load configuration from environment variables.

        Maps LEX_ADMIN__* environment variables to nested config:
        - LEX_ADMIN__DEBUG=true -> {"debug": True}
        - LEX_ADMIN__AUTH__SESSION_LIFETIME=3600 -> {"auth": {"session_lifetime": 3600}}
        """
        result: dict[str, Any] = {}

        for key, value in os.environ.items():
            if not key.startswith(self.ENV_PREFIX):
                continue

            # Remove prefix and convert to path
            config_key = key[len(self.ENV_PREFIX) :]
            if not config_key.strip("_"):
                continue
            if "__" in config_key:
                # Canonical format: LEX_ADMIN__AUTH__SESSION_LIFETIME
                resolved_path = [
                    segment.lower() for segment in config_key.split("__") if segment
                ]
            else:
                # Backward-compat fallback: LEX_ADMIN_AUTH_SESSION_LIFETIME
                path_parts = config_key.lower().split("_")
                resolved_path = self._resolve_env_path(path_parts)

            # Convert value
            typed_value = self._parse_env_value(value)

            self._set_nested(result, resolved_path, typed_value)

        return result

    def _resolve_env_path(self, parts: list[str]) -> list[str]:
        """Resolve environment variable parts to config path.

        Handles compound names like SESSION_LIFETIME -> session_lifetime
        """
        # Known nested sections
        known_sections = {"auth", "features", "ui", "rate", "resource", "table", "form"}

        result = []
        i = 0
        while i < len(parts):
            part = parts[i]

            if part in known_sections:
                # Check for compound section name
                if part == "rate" and i + 1 < len(parts) and parts[i + 1] == "limit":
                    result.append("rate_limit")
                    i += 2
                elif (
                    part == "resource"
                    and i + 1 < len(parts)
                    and parts[i + 1] == "defaults"
                ):
                    result.append("resource_defaults")
                    i += 2
                elif (
                    part == "table"
                    and i + 1 < len(parts)
                    and parts[i + 1] == "defaults"
                ):
                    result.append("table_defaults")
                    i += 2
                elif (
                    part == "form" and i + 1 < len(parts) and parts[i + 1] == "defaults"
                ):
                    result.append("form_defaults")
                    i += 2
                else:
                    result.append(part)
                    i += 1
            else:
                # Remaining parts as compound key
                result.append("_".join(parts[i:]))
                break

        return result if result else parts

    def _parse_env_value(self, value: str) -> Any:
        """Parse environment variable string to typed value."""
        # Boolean
        if value.lower() in ("true", "1", "yes", "on"):
            return True
        if value.lower() in ("false", "0", "no", "off"):
            return False

        # Integer
        try:
            return int(value)
        except ValueError:
            pass

        # Float
        try:
            return float(value)
        except ValueError:
            pass

        # JSON (for complex values)
        if value.startswith(("{", "[")):
            try:
                from lexigram.serialization import loads

                return loads(value)
            except (json.JSONDecodeError, ValueError, TypeError):
                pass

        # String
        return value

    def _deep_merge(self, base: dict[str, Any], override: dict[str, Any]) -> None:
        """Deep merge override into base (mutates base)."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def _set_nested(self, data: dict[str, Any], path: list[str], value: Any) -> None:
        """Set a nested value by path."""
        for part in path[:-1]:
            data = data.setdefault(part, {})
        data[path[-1]] = value

    def _delete_nested(self, data: dict[str, Any], path: list[str]) -> None:
        """Delete a nested value by path."""
        for part in path[:-1]:
            if part in data and isinstance(data[part], dict):
                data = data[part]
            else:
                return
        data.pop(path[-1], None)


# Global config instance (lazily initialized)
_config_loader: AdminConfigLoader | None = None


async def get_config() -> AdminConfig:
    """Get the global admin configuration.

    Initializes and loads config on first call.

    Returns:
        AdminConfig instance
    """
    global _config_loader
    if _config_loader is None:
        _config_loader = AdminConfigLoader()
        await _config_loader.load()
    return _config_loader.config


def get_loader() -> AdminConfigLoader:
    """Get the global config loader instance.

    Creates a new loader if none exists.

    Returns:
        AdminConfigLoader instance
    """
    global _config_loader
    if _config_loader is None:
        _config_loader = AdminConfigLoader()
    return _config_loader
