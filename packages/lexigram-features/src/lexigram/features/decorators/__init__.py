"""Feature-flag–gated decorators package.

Re-exports all four public decorators from their respective submodules.

Usage
-----
Async functions::

    @feature_flag("new_billing", manager=manager)
    async def process_payment(order_id: str) -> None: ...

Sync functions::

    @feature_flag_sync("dark_mode", manager=manager)
    def render_theme() -> str: ...

Strict access guard (raises on disabled)::

    @require_flag("admin_panel", manager=manager)
    async def admin_dashboard() -> Response: ...
"""

from __future__ import annotations

from lexigram.features.decorators.feature_flag import feature_flag, require_flag
from lexigram.features.decorators.sync import feature_flag_sync, require_flag_sync

__all__ = [
    "feature_flag",
    "feature_flag_sync",
    "require_flag",
    "require_flag_sync",
]
