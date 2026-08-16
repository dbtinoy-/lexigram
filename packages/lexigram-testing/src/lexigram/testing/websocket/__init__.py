"""WebSocket testing utilities.

Provides in-memory WebSocket test clients for testing WebSocket
handlers without requiring a real server connection.
"""

from __future__ import annotations

from lexigram.testing.websocket.client import WebSocketTestClient

__all__ = ["WebSocketTestClient"]
