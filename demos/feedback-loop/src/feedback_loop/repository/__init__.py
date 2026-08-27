"""Canned data stores and registries.

Convention: the repository layer owns domain data.  Re-exports make
imports ergonomic (``from feedback_loop.repository import BOT``).
"""

from __future__ import annotations

from feedback_loop.repository.bot import BOT, POOR_KEYS, TRACE_IDS

__all__ = ["BOT", "POOR_KEYS", "TRACE_IDS"]
