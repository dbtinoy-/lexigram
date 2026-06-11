"""Boot-readable file mirror of admin-toggled plugin disabled state.

Bridges "admin clicked disable" to "next process boot excludes it" without
core ever gaining a DB dependency — this module has zero knowledge of
``TenantConfigStore`` or any other admin/DB concept, deliberately, per the
package-boundary rule (extensions never depend on each other).

Persistence contract (systemd-preset style):
  - Every save is atomic: tempfile + fsync + ``os.replace``. A crash leaves
    either the old or the new file, never a torn one.
  - Read-modify-write is serialized with a ``flock`` advisory lock so
    concurrent admin sessions in different processes cannot clobber each
    other's update.
  - A corrupt state file is renamed to ``<name>.corrupt-<ts>`` and reading
    fails open to an empty set — plugin state must never block boot.
"""

from __future__ import annotations

import contextlib
import fcntl
import json
import os
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from lexigram.logging import get_logger
from lexigram.plugins.exceptions import PluginStateError

if TYPE_CHECKING:
    from collections.abc import Iterator

logger = get_logger(__name__)

__all__ = ["load_disabled", "save_disabled", "update_disabled", "_STATE_SCHEMA_VERSION"]

_STATE_SCHEMA_VERSION = 1
_ENV_STATE_PATH = "LEXIGRAM_PLUGINS_STATE_PATH"
_DEFAULT_STATE_PATH = Path(".lexigram/plugins.json")


def _resolve_path(path: str | Path | None) -> Path:
    if path is not None:
        return Path(path)
    env_value = os.environ.get(_ENV_STATE_PATH)
    return Path(env_value) if env_value else _DEFAULT_STATE_PATH


def _lock_file_for(resolved: Path) -> Path:
    return resolved.with_name(resolved.name + ".lock")


def _write_atomic(resolved: Path, data: dict[str, Any]) -> None:
    """Write ``data`` to ``resolved`` atomically via temp + fsync + replace."""
    temp = resolved.with_name(f"{resolved.name}.tmp-{os.getpid()}")
    try:
        with temp.open("w") as fh:
            fh.write(json.dumps(data))
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(temp, resolved)
    except OSError as exc:
        try:
            temp.unlink()
        except OSError:
            pass
        raise PluginStateError(
            "failed to write plugin state",
            path=str(resolved),
        ) from exc


def load_disabled(path: str | Path | None = None) -> set[str]:
    """Return the set of plugin names disabled in the boot-file mirror.

    Missing or corrupt state never prevents application boot — a corrupt
    file is preserved as ``<name>.corrupt-<ts>`` and reading returns an
    empty set. Legacy unversioned files (``{"disabled": [...]}``) load fine.

    Args:
        path: Explicit state-file path. Falls back to the
            ``LEXIGRAM_PLUGINS_STATE_PATH`` env var, then
            ``.lexigram/plugins.json`` relative to the working directory.

    Returns:
        Set of disabled entry-point names (possibly empty).
    """
    resolved = _resolve_path(path)
    if not resolved.exists():
        return set()

    try:
        data = json.loads(resolved.read_text())
    except (json.JSONDecodeError, OSError):
        backup = resolved.with_name(
            f"{resolved.name}.corrupt-{int(time.time())}"
        )
        try:
            os.replace(resolved, backup)
            logger.warning(
                "plugins.state.corrupt_file_backed_up",
                path=str(resolved),
                backup=str(backup),
            )
        except OSError:
            logger.warning(
                "plugins.state.corrupt_file_unreadable",
                path=str(resolved),
                error="backup_failed",
            )
        return set()

    disabled = data.get("disabled", [])
    if not isinstance(disabled, list):
        logger.warning("plugins.state.invalid_shape", path=str(resolved))
        return set()
    return {str(name) for name in disabled}


def save_disabled(names: set[str], path: str | Path | None = None) -> None:
    """Persist ``names`` to the boot-file mirror under an exclusive lock.

    Atomic (temp + fsync + ``os.replace``) and serialized via ``flock``
    so concurrent writers cannot interleave read-modify-write cycles.

    Args:
        names: Set of disabled plugin entry-point names.
        path: Explicit state-file path (env var / default fallback applies
            when omitted).

    Raises:
        PluginStateError: If the state cannot be written (disk full,
            permission denied, etc.).
    """
    resolved = _resolve_path(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)

    with _exclusive_lock(resolved):
        data: dict[str, Any] = {
            "version": _STATE_SCHEMA_VERSION,
            "disabled": sorted(names),
        }
        _write_atomic(resolved, data)


def update_disabled(
    mutator: Any,
    path: str | Path | None = None,
) -> set[str]:
    """Apply ``mutator`` to the disabled set under one exclusive lock.

    Load, mutate, and save happen inside a single ``flock`` critical
    section, so concurrent readers/writers (e.g. two admin sessions in
    different processes) cannot lose updates.

    Args:
        mutator: Callable mapping the current disabled set to the new
            disabled set, e.g. ``lambda current: current | {"rag"}``.
        path: Explicit state-file path (env var / default fallback applies
            when omitted).

    Returns:
        The resulting disabled set after ``mutator`` was applied.

    Raises:
        PluginStateError: If the state cannot be read or written.
    """
    resolved = _resolve_path(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)

    with _exclusive_lock(resolved):
        current = load_disabled(resolved)
        updated = mutator(current)
        data: dict[str, Any] = {
            "version": _STATE_SCHEMA_VERSION,
            "disabled": sorted(updated),
        }
        _write_atomic(resolved, data)
    return set(updated)


def _exclusive_lock(resolved: Path) -> Any:
    """Return a context manager holding an exclusive ``flock`` on the
    sibling ``.lock`` file for ``resolved``."""
    lock_path = _lock_file_for(resolved)

    @contextlib.contextmanager
    def _locked() -> Iterator[None]:
        with lock_path.open("a") as lock_fh:
            fcntl.flock(lock_fh, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_fh, fcntl.LOCK_UN)

    return _locked()