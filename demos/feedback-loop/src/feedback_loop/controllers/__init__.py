"""JSON API controllers (logic lives here; pages serve assets).

Convention: re-exports make imports ergonomic.  Controllers are
registered in the ``WebModule.configure()`` call in ``app.py``.
"""

from __future__ import annotations

from feedback_loop.controllers.api import LoopApiController

__all__ = ["LoopApiController"]
