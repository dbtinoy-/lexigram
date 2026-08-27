"""RAG pipeline UI assets and static-serving routes.

Convention followed: **Page controller pattern** — ``RagPageController``
serves static HTML/CSS/JS files.  The API controller handles all dynamic
behavior.

Exports:

- ``RagPageController`` — static file serving routes
"""

from __future__ import annotations

from ragdocs.ui.pages import RagPageController

__all__ = ["RagPageController"]
