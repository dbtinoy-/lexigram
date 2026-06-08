"""Boot-readable file mirror of admin-toggled plugin disabled state.

Bridges "admin clicked disable" to "next process boot excludes it" without
core ever gaining a DB dependency — this module has zero knowledge of
``TenantConfigStore`` or any other admin/DB concept, deliberately, per the
package-boundary rule (extensions never depend on each other).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from lexigram.logging import get_logger

logger = get_logger(__name__)

__all__ = ["load_disabled", "save_disabled"]

_ENV_STATE_PATH = "LEXIGRAM_PLUGINS_STATE_PATH"
_DEFAULT_STATE_PATH = Path(".lexigram/plugins.json")


def _resolve_path(path: str | Path | None) -> Path:
    if path is not None:
        return Path(path)
    env_value = os.environ.get(_ENV_STATE_PATH)
    return Path(env_value) if env_value else _DEFAULT_STATE_PATH


def load_disabled(path: str | Path | None = None) -> set[str]:
    """Return the set of plugin names disabled in the boot-file mirror.

    Returns an empty set if the file doesn't exist or fails to parse —
    a missing/corrupt state file must never prevent the application from
    booting.
    """
    resolved = _resolve_path(path)
    if not resolved.exists():
        return set()
    try:
        data = json.loads(resolved.read_text())
    except (json.JSONDecodeError, OSError):
        logger.warning("plugins.state.load_failed", path=str(resolved))
        return set()
    disabled = data.get("disabled", [])
    if not isinstance(disabled, list):
        return set()
    return {str(name) for name in disabled}


def save_disabled(names: set[str], path: str | Path | None = None) -> None:
    """Persist the set of disabled plugin names to the boot-file mirror."""
    resolved = _resolve_path(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(json.dumps({"disabled": sorted(names)}, indent=2))