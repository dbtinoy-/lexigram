"""Engine module for lexigram-admin.

Provides rendering and template engine functionality.
"""

from __future__ import annotations

from lexigram.admin.engine.renderer import AdminRenderer, AdminRendererConfig

__all__ = [
    "AdminRenderer",
    "AdminRendererConfig",
]
