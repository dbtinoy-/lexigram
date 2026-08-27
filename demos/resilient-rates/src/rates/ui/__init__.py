"""Rate desk UI assets and static-serving routes.

Convention followed: **Page controller pattern** — ``RatesPageController``
serves static HTML/CSS/JS files.  The API controller handles all dynamic
behavior.

Exports:

- ``RatesPageController`` — static file serving routes
"""

from __future__ import annotations

from rates.ui.pages import RatesPageController

__all__ = ["RatesPageController"]
