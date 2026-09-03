"""Read-only effective application configuration for the Settings Center.

The registry-backed settings specs represent values that an operator may
override at runtime. ``AdminConfig`` is different: it is the effective
application configuration assembled from model defaults, YAML, environment,
and runtime code. This adapter exposes that boundary for inspection only.
"""

from __future__ import annotations

from dataclasses import is_dataclass
from enum import Enum
import json  # noqa: TID251 — pretty operator-facing JSON requires indent support
import re
from typing import Any

from lexigram.admin.settings.panel.nodes import ConfigSpec, StringNode
from lexigram.admin.settings.panel.registry import ReadOnlyStore

__all__ = [
    "AdminConfigStore",
    "EffectiveApplicationConfigSpec",
    "redact_config_value",
]

_REDACTED = "[redacted]"


def _is_sensitive_key(key: Any) -> bool:
    """Return whether a mapping/field name identifies secret material.

    Names such as ``csrf_token_lifetime`` and ``token_ttl_hours`` describe a
    duration, not a credential, so a token marker is sensitive only when it is
    the terminal component of the field name.
    """
    text = re.sub(r"(?<!^)(?=[A-Z])", "_", str(key))
    text = text.replace("-", "_").replace(".", "_").lower()
    if text.endswith(
        (
            "_token",
            "_secret",
            "_password",
            "_password_hash",
            "_hashed_password",
            "_password_digest",
            "_passwd",
            "_credential",
            "_dsn",
            "_connection_string",
            "_database_url",
            "_redis_url",
            "_mongo_url",
            "_jdbc_url",
            "_access_key",
            "_secret_key",
            "_key_hash",
            "_encryption_key",
            "_signing_key",
            "_salt",
            "_nonce",
        )
    ):
        return True
    if text in {
        "token",
        "secret",
        "password",
        "password_hash",
        "hashed_password",
        "password_digest",
        "passwd",
        "credential",
        "dsn",
        "jwt",
        "authorization",
        "session_id",
        "secret_id",
        "token_id",
        "salt",
        "nonce",
        "connection_string",
        "database_url",
        "redis_url",
        "mongo_url",
        "jdbc_url",
        "access_key",
        "secret_key",
        "encryption_key",
        "signing_key",
    }:
        return True
    return bool(re.search(r"(?:api|private)_key$", text))


def redact_config_value(value: Any, *, key: str | None = None) -> Any:
    """Recursively redact credentials before a config value reaches a view.

    The shared domain serializer is intentionally general-purpose and can
    serialize arbitrary object attributes; it is not a security boundary.
    This function therefore checks field names *before* descending and also
    handles ``SecretStr`` explicitly. It returns JSON-compatible primitives.
    """
    if key is not None and _is_sensitive_key(key):
        return _REDACTED

    try:
        from lexigram.validation import SecretStr

        if isinstance(value, SecretStr):
            return _REDACTED
    except ImportError:  # pragma: no cover - validation is a core dependency
        pass
    if value.__class__.__name__ in {"SecretBytes", "SecretStr"}:
        return _REDACTED

    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Enum):
        return redact_config_value(value.value)
    if isinstance(value, dict):
        return {
            str(child_key): redact_config_value(child_value, key=str(child_key))
            for child_key, child_value in value.items()
        }
    if isinstance(value, (list, tuple, set, frozenset)):
        return [redact_config_value(item) for item in value]
    if is_dataclass(value):
        return {
            field.name: redact_config_value(getattr(value, field.name), key=field.name)
            for field in value.__dataclass_fields__.values()
            if not field.name.startswith("_")
        }
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        try:
            return redact_config_value(model_dump(mode="python"))
        except (TypeError, ValueError):
            pass
    if hasattr(value, "__dict__"):
        return {
            str(child_key): redact_config_value(child_value, key=str(child_key))
            for child_key, child_value in vars(value).items()
            if not str(child_key).startswith("_")
        }
    return str(value)


def _flatten_paths(value: Any, prefix: str = "") -> dict[str, str]:
    """Flatten a redacted value for compact source/provenance presentation."""
    result: dict[str, str] = {}
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            result.update(_flatten_paths(child, path))
        return result
    if isinstance(value, list):
        for index, child in enumerate(value):
            result.update(_flatten_paths(child, f"{prefix}[{index}]"))
        return result
    result[prefix] = "redacted" if value == _REDACTED else "visible"
    return result


class AdminConfigStore(ReadOnlyStore):
    """Read-only ``StoreBase`` adapter for an effective ``AdminConfig``."""

    def __init__(self, config: Any, loader: Any = None) -> None:
        self._config = config
        self._loader = loader

    def _payload(self) -> dict[str, str]:
        """Build the small set of values consumed by the read-only spec."""
        redacted = redact_config_value(self._config)
        effective = json.dumps(redacted, indent=2, sort_keys=True, default=str)

        provenance: dict[str, str] = {}
        get_provenance = getattr(self._loader, "get_provenance", None)
        if callable(get_provenance):
            try:
                provenance = {
                    str(path): str(source) for path, source in get_provenance().items()
                }
            except Exception:  # noqa: BLE001 — provenance is explanatory only
                provenance = {}
        if not provenance:
            # This explicit fallback is intentionally honest: the application
            # config object is effective, but this mount did not receive the
            # loader that could identify the exact YAML/env owner per leaf.
            provenance = dict.fromkeys(
                _flatten_paths(redacted),
                "effective application configuration; exact loader source unavailable",
            )

        yaml_path = getattr(self._loader, "yaml_path", None)
        path_text = str(yaml_path) if yaml_path else "Not provided by this mount"
        return {
            "effective_config": effective,
            "source_provenance": json.dumps(provenance, indent=2, sort_keys=True),
            "source_precedence": (
                "Runtime override → environment → YAML/application config → "
                "declared model default"
            ),
            "config_path": path_text,
        }

    async def get(
        self, key: str, default: Any = None, tenant_id: str | None = None
    ) -> Any:
        """Return one redacted inspection value, never a writable setting."""
        del tenant_id
        name = key.removeprefix("admin.application.")
        return self._payload().get(name, default)

    async def contains(self, key: str, tenant_id: str | None = None) -> bool:
        """All declared inspection fields are present in this adapter."""
        del tenant_id
        return key.removeprefix("admin.application.") in {
            "effective_config",
            "source_provenance",
            "source_precedence",
            "config_path",
        }

    async def set(self, key: str, value: Any, tenant_id: str | None = None) -> None:
        """Reject writes even if a future caller bypasses readonly filtering."""
        del key, value, tenant_id
        raise PermissionError("Effective application configuration is read-only")


class EffectiveApplicationConfigSpec(ConfigSpec):
    """Read-only effective AdminConfig and source explanation."""

    namespace = "admin.application"
    label = "Effective Application Configuration"
    icon = "file-text"
    description = (
        "Inspect the effective AdminConfig assembled by the application. "
        "These values may be owned by YAML, environment, model defaults, or "
        "runtime code and cannot be edited from this screen."
    )
    package_source = "built-in"
    store_name = "application"
    runtime_status = "active"
    required_permissions = frozenset({"admin.settings.edit"})
    effective_config = StringNode(
        label="Effective values",
        default="{}",
        help_text="Secrets and credential-like fields are redacted before rendering.",
        readonly=True,
        multiline=True,
    )
    source_provenance = StringNode(
        label="Source / origin by path",
        default="{}",
        help_text="Exact ownership is shown when the mounted configuration loader supplies provenance.",
        readonly=True,
        multiline=True,
    )
    source_precedence = StringNode(
        label="Precedence",
        default="Runtime override → environment → YAML/application config → declared model default",
        help_text="Higher entries win when the same path is supplied by multiple sources.",
        readonly=True,
    )
    config_path = StringNode(
        label="Configuration file",
        default="Not provided by this mount",
        help_text="The path is informational; this panel never writes YAML.",
        readonly=True,
    )
