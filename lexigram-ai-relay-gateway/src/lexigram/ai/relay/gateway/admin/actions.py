"""Admin action handlers for the relay gateway contributor.

Each handler accepts ``(container, **params)`` per the admin action
contract, validates every parameter server-side, and returns a result
dict describing the audited outcome (or the validation/concurrency
failure).  The ``container`` resolves ``RelayControlsService`` lazily.
"""

from __future__ import annotations

from typing import Any

from lexigram.ai.relay.gateway.operations.controls import RelayControlsService
from lexigram.ai.relay.gateway.operations.health import RelayHealthService
from lexigram.contracts.ai.relay import (
    RelayChannel,
    RelayChannelStoreProtocol,
    RelayFormat,
)
from lexigram.logging import get_logger

logger = get_logger(__name__)

_TRUE_TOKENS = {"true", "1", "yes", "on"}
_FALSE_TOKENS = {"false", "0", "no", "off"}


def _coerce_bool(raw: object, default: bool | None = None) -> bool | None:
    """Coerce a bool-like value to a strict boolean.

    Args:
        raw: Value to coerce; bools, strings, and numbers accepted.
        default: Value returned when ``raw`` is ``None``. ``None``
            makes coercion failure return ``None`` as well.

    Returns:
        The coerced boolean, or ``None`` when the value is not a
        recognizable boolean token.
    """
    if isinstance(raw, bool):
        return raw
    if raw is None:
        return default
    if isinstance(raw, int) and raw in (0, 1):
        return bool(raw)
    if isinstance(raw, str):
        token = raw.strip().lower()
        if token in _TRUE_TOKENS:
            return True
        if token in _FALSE_TOKENS:
            return False
    return None


def _coerce_int(raw: object, default: int | None = None) -> int | None:
    """Coerce a value to an integer.

    Args:
        raw: Value to coerce; ints and digit strings accepted.
        default: Value returned when ``raw`` is ``None``.

    Returns:
        The coerced integer, or ``None`` when the value is not a
        recognizable integer.
    """
    if isinstance(raw, bool):
        return None
    if raw is None:
        return default
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str):
        try:
            return int(raw.strip())
        except ValueError:
            return None
    return None


def _coerce_float(raw: object, default: float | None = None) -> float | None:
    """Coerce a value to a float.

    Args:
        raw: Value to coerce; numbers and numeric strings accepted.
        default: Value returned when ``raw`` is ``None``.

    Returns:
        The coerced float, or ``None`` for unrecognizable values.
    """
    if isinstance(raw, bool):
        return None
    if raw is None:
        return default
    if isinstance(raw, (int, float)):
        return float(raw)
    if isinstance(raw, str):
        try:
            return float(raw.strip())
        except ValueError:
            return None
    return None


def _coerce_str_list(raw: object) -> list[str] | None:
    """Coerce a value to a list of trimmed non-empty strings.

    Accepts a list of strings or a comma-separated string.

    Args:
        raw: Value to coerce.

    Returns:
        The item list, or ``None`` for unrecognizable values.
    """
    if isinstance(raw, str):
        items = [part.strip() for part in raw.split(",")]
        return [item for item in items if item]
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, str) and item.strip()]
    return None


def _echo(channel: RelayChannel) -> dict[str, object]:
    """Build a validated echo mapping for one channel."""
    return {
        "name": channel.name,
        "target_format": channel.target_format.value,
        "models": list(channel.models),
        "priority": channel.priority,
        "enabled": channel.enabled,
    }


def _build_channel(params: dict[str, object]) -> tuple[RelayChannel | None, str | None]:
    """Build a validated channel from action parameters.

    Args:
        params: The action parameter mapping.

    Returns:
        A ``(channel, None)`` pair on success, or a
        ``(None, error_message)`` pair describing the first validated
        problem.
    """
    name = params.get("name")
    if not isinstance(name, str) or not name.strip():
        return None, "name is required"
    upstream_base_url = params.get("upstream_base_url")
    if not isinstance(upstream_base_url, str) or not upstream_base_url.strip():
        return None, "upstream_base_url is required"
    target_format = params.get("target_format")
    if not isinstance(target_format, str) or not target_format.strip():
        return None, "target_format is required"
    try:
        fmt = RelayFormat(target_format)
    except ValueError:
        return None, f"unknown target_format {target_format!r}"
    models = _coerce_str_list(params.get("models"))
    if models is None:
        return None, "models must be a list of strings or a comma-separated string"
    priority = _coerce_int(params.get("priority"), 100)
    if priority is None:
        return None, "priority must be an integer"
    weight = _coerce_int(params.get("weight"), 100)
    if weight is None:
        return None, "weight must be an integer"
    enabled = _coerce_bool(params.get("enabled"), True)
    if enabled is None:
        return None, "enabled must be a boolean"
    timeout_seconds = _coerce_float(params.get("timeout_seconds"), 60.0)
    if timeout_seconds is None:
        return None, "timeout_seconds must be a number"
    capabilities = _coerce_str_list(params.get("capabilities")) or []
    endpoint_kinds = _coerce_str_list(params.get("endpoint_kinds")) or []
    try:
        channel = RelayChannel(
            name=name.strip(),
            upstream_base_url=upstream_base_url.strip(),
            target_format=fmt,
            models=tuple(models),
            capabilities=frozenset(capabilities),
            endpoint_kinds=frozenset(endpoint_kinds),
            priority=priority,
            weight=weight,
            enabled=enabled,
            timeout_seconds=timeout_seconds,
        )
    except ValueError as exc:
        return None, str(exc)
    return channel, None


async def _resolve_store(container: Any) -> RelayChannelStoreProtocol | None:
    """Resolve the durable channel store, or ``None`` when unbound."""
    try:
        return await container.resolve(RelayChannelStoreProtocol)
    except Exception:  # noqa: BLE001
        return None


async def set_channel_state(container: Any, **params: object) -> dict[str, object]:
    """Enable or drain a gateway channel.

    Args:
        container: Container resolver exposing ``RelayControlsService``.
        **params: Action parameters; ``channel`` (str) and ``enabled``
            (bool-like) are required, ``actor_id`` (str) defaults to
            ``"admin"``.

    Returns:
        Mapping describing the outcome: ``ok`` boolean, ``message``,
        ``echo`` (validated params), and ``raised`` for failures.
    """
    channel = params.get("channel")
    if not isinstance(channel, str) or not channel.strip():
        return {"ok": False, "message": "channel is required", "echo": {}}
    enabled = _coerce_bool(params.get("enabled"))
    if enabled is None:
        return {"ok": False, "message": "enabled must be a boolean", "echo": {}}
    actor_id = str(params.get("actor_id") or "admin")
    echo = {"channel": channel, "enabled": enabled, "actor_id": actor_id}
    try:
        controls = await container.resolve(RelayControlsService)
        await controls.set_channel_state(
            channel=channel, enabled=enabled, actor_id=actor_id
        )
    except ValueError as exc:
        logger.warning("relay_admin.set_channel_state.rejected", error=str(exc))
        return {"ok": False, "message": str(exc), "echo": echo}
    except Exception as exc:  # noqa: BLE001
        logger.error("relay_admin.set_channel_state.failed", error=str(exc))
        return {"ok": False, "message": str(exc), "echo": echo}
    return {
        "ok": True,
        "message": f"channel {channel!r} {'enabled' if enabled else 'drained'}",
        "echo": echo,
    }


async def force_cancel_stream(container: Any, **params: object) -> dict[str, object]:
    """Force-cancel an in-flight upstream stream.

    Args:
        container: Container resolver exposing ``RelayControlsService``.
        **params: Action parameters; ``stream_id`` (str) is required,
            ``actor_id`` (str) defaults to ``"admin"``.

    Returns:
        Mapping describing the outcome: ``ok`` boolean, ``message``,
        and ``echo`` with the validated stream identifier.
    """
    stream_id = params.get("stream_id")
    if not isinstance(stream_id, str) or not stream_id.strip():
        return {"ok": False, "message": "stream_id is required", "echo": {}}
    actor_id = str(params.get("actor_id") or "admin")
    echo = {"stream_id": stream_id, "actor_id": actor_id}
    try:
        controls = await container.resolve(RelayControlsService)
        await controls.force_cancel_stream(
            stream_id=stream_id,
            actor_id=actor_id,
        )
    except ValueError as exc:
        logger.warning("relay_admin.force_cancel_stream.rejected", error=str(exc))
        return {"ok": False, "message": str(exc), "echo": echo}
    except Exception as exc:  # noqa: BLE001
        logger.error("relay_admin.force_cancel_stream.failed", error=str(exc))
        return {"ok": False, "message": str(exc), "echo": echo}
    return {"ok": True, "message": f"stream {stream_id!r} cancelled", "echo": echo}


async def create_channel(container: Any, **params: object) -> dict[str, object]:
    """Create a durable relay channel.

    Args:
        container: Container resolver exposing
            ``RelayChannelStoreProtocol``.
        **params: Action parameters; ``name``, ``upstream_base_url``,
            ``target_format``, and ``models`` are required. Optional
            fields default to the ``RelayChannel`` defaults.

    Returns:
        Mapping describing the outcome: ``ok`` boolean, ``message``,
        ``echo``, ``revision`` and ``code`` (``CONCURRENCY_STALE``) for
        stale writes.
    """
    channel, error = _build_channel(params)
    if channel is None:
        return {"ok": False, "message": error or "invalid channel", "echo": {}}
    echo = _echo(channel)
    store = await _resolve_store(container)
    if store is None:
        return {"ok": False, "message": "channel store is not registered", "echo": {}}
    existing = {snapshot.channel.name for snapshot in await store.list_channels()}
    if channel.name in existing:
        return {
            "ok": False,
            "message": f"channel {channel.name!r} already exists",
            "echo": echo,
        }
    try:
        revision = await store.upsert(channel, expected_revision=None)
    except Exception as exc:  # noqa: BLE001
        logger.error("relay_admin.create_channel.failed", error=str(exc))
        return {"ok": False, "message": str(exc), "echo": echo}
    if revision is None:
        return {
            "ok": False,
            "message": f"channel {channel.name!r} created concurrently; retry",
            "code": "CONCURRENCY_STALE",
            "echo": echo,
        }
    logger.info("relay_admin.create_channel", channel=channel.name, revision=revision)
    return {
        "ok": True,
        "message": f"channel {channel.name!r} created (revision {revision})",
        "echo": echo,
        "revision": revision,
    }


async def update_channel(container: Any, **params: object) -> dict[str, object]:
    """Update a durable relay channel under compare-and-set.

    Args:
        container: Container resolver exposing
            ``RelayChannelStoreProtocol``.
        **params: Action parameters; channel payload fields plus the
            required ``expected_revision`` (int) the caller observed.

    Returns:
        Mapping describing the outcome: ``ok`` boolean, ``message``,
        ``echo``, ``revision`` and ``code`` (``CONCURRENCY_STALE``) for
        stale writes.
    """
    raw_revision = _coerce_int(params.get("expected_revision"))
    if raw_revision is None or raw_revision < 1:
        return {
            "ok": False,
            "message": "expected_revision must be a positive integer",
            "echo": {},
        }
    channel, error = _build_channel(params)
    if channel is None:
        return {"ok": False, "message": error or "invalid channel", "echo": {}}
    echo = _echo(channel)
    store = await _resolve_store(container)
    if store is None:
        return {"ok": False, "message": "channel store is not registered", "echo": {}}
    try:
        revision = await store.upsert(channel, expected_revision=raw_revision)
    except Exception as exc:  # noqa: BLE001
        logger.error("relay_admin.update_channel.failed", error=str(exc))
        return {"ok": False, "message": str(exc), "echo": echo}
    if revision is None:
        return {
            "ok": False,
            "message": (
                f"channel {channel.name!r} changed concurrently; "
                f"expected revision {raw_revision}"
            ),
            "code": "CONCURRENCY_STALE",
            "echo": echo,
        }
    logger.info("relay_admin.update_channel", channel=channel.name, revision=revision)
    return {
        "ok": True,
        "message": f"channel {channel.name!r} updated (revision {revision})",
        "echo": echo,
        "revision": revision,
    }


async def delete_channel(container: Any, **params: object) -> dict[str, object]:
    """Delete a durable relay channel under compare-and-set.

    Args:
        container: Container resolver exposing
            ``RelayChannelStoreProtocol``.
        **params: Action parameters; ``name`` (str) and
            ``expected_revision`` (int) are required.

    Returns:
        Mapping describing the outcome: ``ok`` boolean, ``message``,
        ``echo`` and ``code`` (``CONCURRENCY_STALE``) when the row is
        absent or stale.
    """
    name = params.get("name")
    if not isinstance(name, str) or not name.strip():
        return {"ok": False, "message": "name is required", "echo": {}}
    raw_revision = _coerce_int(params.get("expected_revision"))
    if raw_revision is None or raw_revision < 1:
        return {
            "ok": False,
            "message": "expected_revision must be a positive integer",
            "echo": {},
        }
    store = await _resolve_store(container)
    if store is None:
        return {"ok": False, "message": "channel store is not registered", "echo": {}}
    try:
        removed = await store.delete(name.strip(), expected_revision=raw_revision)
    except Exception as exc:  # noqa: BLE001
        logger.error("relay_admin.delete_channel.failed", error=str(exc))
        return {"ok": False, "message": str(exc), "echo": {"name": name}}
    if not removed:
        return {
            "ok": False,
            "message": (
                f"channel {name!r} not found or revision {raw_revision} is stale"
            ),
            "code": "CONCURRENCY_STALE",
            "echo": {"name": name.strip(), "expected_revision": raw_revision},
        }
    logger.info("relay_admin.delete_channel", channel=name.strip())
    return {
        "ok": True,
        "message": f"channel {name!r} deleted",
        "echo": {"name": name.strip()},
    }


async def test_channel(container: Any, **params: object) -> dict[str, object]:
    """Probe one channel through the existing health service.

    Runs the Plan-D health probe for the named channel and reports the
    verdict and observed latency; never touches credentials.

    Args:
        container: Container resolver exposing ``RelayHealthService``.
        **params: Action parameters; ``name`` (str) is required.

    Returns:
        Mapping describing the outcome: ``ok`` boolean, ``message`` and
        ``echo`` with ``verdict`` and ``latency_ms``.
    """
    name = params.get("name")
    if not isinstance(name, str) or not name.strip():
        return {"ok": False, "message": "name is required", "echo": {}}
    try:
        health = await container.resolve(RelayHealthService)
    except Exception:  # noqa: BLE001
        return {
            "ok": False,
            "message": "health service is not registered",
            "echo": {},
        }
    try:
        snapshots = await health.channel_health()
    except Exception as exc:  # noqa: BLE001
        logger.error("relay_admin.test_channel.failed", error=str(exc))
        return {"ok": False, "message": str(exc), "echo": {"channel": name}}
    row = next((snapshot for snapshot in snapshots if snapshot.channel == name), None)
    if row is None:
        return {
            "ok": False,
            "message": f"channel {name!r} not found",
            "echo": {"channel": name},
        }
    echo = {"channel": name, "verdict": row.status, "latency_ms": row.latency_ms_p50}
    return {
        "ok": True,
        "message": f"channel {name!r} probe verdict: {row.status}",
        "echo": echo,
    }


__all__ = [
    "create_channel",
    "delete_channel",
    "force_cancel_stream",
    "set_channel_state",
    "test_channel",
    "update_channel",
]
