"""Admin dashboard widgets and contributor for lexigram-auth."""

from __future__ import annotations

from lexigram.auth.admin.contributor import AuthAdminContributor
from lexigram.auth.admin.handlers import (
    ActiveSessionsWidgetHandler,
    FailedLoginsWidgetHandler,
    TokenRefreshRateWidgetHandler,
)

__all__ = [
    "ActiveSessionsWidgetHandler",
    "AuthAdminContributor",
    "FailedLoginsWidgetHandler",
    "TokenRefreshRateWidgetHandler",
]
