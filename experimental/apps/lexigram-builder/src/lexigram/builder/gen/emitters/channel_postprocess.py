"""Post-processing for generated WebSocket (realtime channel) modules.

The framework ``websocket`` generator hardcodes the route decorator as
``@websocket_handler("/ws/<name>")`` and the handler class as ``Pascal(name)``.
When the graph supplies an explicit channel path we must rewrite the decorator
so the mounted route matches.

It also references ``websocket.path_params`` in ``on_connect`` /
``on_message`` / ``on_disconnect`` to bucket connections by room, but the
lexigram-web ``WebSocket`` transport wrapper does not expose ``path_params``
(see WS-3 in docs/LEXIGRAM_FRAMEWORK_BUGS.md), so the default handler raises
``AttributeError`` before it can accept a connection. We replace those reads
with ``getattr(websocket, "path_params", {})`` so the code degrades to a single
default room on the wrapped transport while staying correct on the raw
Starlette socket.
"""

from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True, slots=True)
class ChannelReconcileResult:
    """Outcome of reconciling a generated channel module."""

    text: str
    path: str


def reconcile_channel(text: str, *, path: str) -> ChannelReconcileResult:
    """Rewrite the decorator path and harden ``path_params`` reads.

    Args:
        text: The generated channel module source.
        path: The WebSocket path the channel must be mounted at
            (e.g. ``/ws/chat``).

    Returns:
        A :class:`ChannelReconcileResult` with the (possibly updated) source
        and the resolved path.
    """
    replacement = f'@websocket_handler("{path}")'
    updated, n = re.subn(
        r'@websocket_handler\(\s*"[^"]*"\s*\)',
        replacement,
        text,
        count=1,
    )
    if n:
        text = updated

    # The transport WebSocket wrapper has no ``path_params`` (WS-3); fall back
    # to an empty mapping so room bucketing degrades to the "default" room.
    text = text.replace(
        'websocket.path_params.get("room_id", "default")',
        'getattr(websocket, "path_params", {}).get("room_id", "default")',
    )
    return ChannelReconcileResult(text=text, path=path)
