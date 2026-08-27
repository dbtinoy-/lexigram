"""Console assets + static-serving routes.

Convention: the UI layer serves HTML views and static assets.  Business
logic lives in controllers (``controllers/api.py``); the page controller
(``ui/pages.py``) is stateless.
"""

from __future__ import annotations

from feedback_loop.ui.pages import LoopPageController

__all__ = ["LoopPageController"]
