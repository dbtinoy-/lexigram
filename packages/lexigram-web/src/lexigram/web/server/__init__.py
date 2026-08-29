"""Server Domain - ASGI Server Bridge"""

from __future__ import annotations

from lexigram.web.di.provider import WebProvider  # Moved to root level
from lexigram.web.server.lifecycle import ServerLifecycle
from lexigram.web.server.runner import run_server, run_server_async

__all__ = ["ServerLifecycle", "WebProvider", "run_server", "run_server_async"]
