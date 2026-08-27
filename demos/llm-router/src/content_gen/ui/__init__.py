"""Content generator UI assets and static-serving routes.

Convention followed: **Page controller pattern** — ``ContentPageController``
serves static HTML/CSS/JS files.  The API controller handles all dynamic
behavior.

Exports:

- ``ContentPageController`` — static file serving routes
"""

from __future__ import annotations

from content_gen.ui.pages import ContentPageController

__all__ = ["ContentPageController"]
