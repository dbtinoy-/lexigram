"""Webhook relay UI assets and static-serving routes.

Convention followed: **Page controller pattern** — ``WebhookPageController``
serves static HTML/CSS/JS files.  The API controller handles all dynamic
behavior.

Exports:

- ``WebhookPageController`` — static file serving routes
"""

from __future__ import annotations

from webhookrelay.ui.pages import WebhookPageController

__all__ = ["WebhookPageController"]
