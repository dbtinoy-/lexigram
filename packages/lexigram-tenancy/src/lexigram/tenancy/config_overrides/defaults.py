"""Default config schema values for per-tenant configuration."""

from __future__ import annotations

from typing import Any

# Applications extend this dict with their own default keys.
DEFAULT_CONFIG: dict[str, Any] = {}

__all__ = ["DEFAULT_CONFIG"]
