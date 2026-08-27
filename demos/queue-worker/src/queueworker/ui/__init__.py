"""Queue worker UI assets and static-serving routes.

Convention followed: **Page controller pattern** — ``QueuePageController``
serves static HTML/CSS/JS files.  The API controller handles all dynamic
behavior.

Exports:

- ``QueuePageController`` — static file serving routes
"""

from __future__ import annotations

from queueworker.ui.pages import QueuePageController

__all__ = ["QueuePageController"]
