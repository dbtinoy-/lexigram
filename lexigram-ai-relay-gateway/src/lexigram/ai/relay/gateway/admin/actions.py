"""Admin action handlers for the relay gateway contributor.

Each handler accepts ``(container, **params)`` per the admin action
contract, validates every parameter server-side, and returns a result
dict describing the audited outcome (or the validation/concurrency
failure).  The ``container`` resolves ``RelayControlsService`` lazily.
"""

from __future__ import annotations

from typing import Any

from lexigram.ai.relay.gateway.operations.controls import RelayControlsService
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


__all__ = ["force_cancel_stream", "set_channel_state"]
